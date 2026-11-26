"""Audit what each configuration sends to the model: does L3a leave the agents' effective inputs
unchanged, and what exactly does full L3 change? (TA milestone item: validate that the
shared-prefix prefill does not alter the agents' effective inputs.)

CPU only. Reads C=1 campaign files written with --record-inputs:
results/final_<GPU>/<task>_<mode>_apcon_C1_s<seed>.jsonl

Checks, per task and seed:
  A. Round-1 identity: every debater's round-1 request (message hash and sampling seed) is the
     same in BASE (seq), L1+L2 (par), L3a and L3, and each warm-up request equals the debaters'
     round-1 request.
  B. Fixed-upstream replay: BASE's recorded round-1 answers are fed back through the harness's
     own run_debate (a replay client returns them), and the round-2 requests each mode builds are
     captured. seq, par and l3a must reproduce BASE's recorded round-2 requests exactly. For l3
     we check that the same information is present (question, every agent's answer) and measure
     the length change.
  C. Self-consistency: every recorded round-2 request in every file equals what that mode builds
     from the same record's own round-1 answers (so the replay in B describes the real runs).
  D. Token prefix (needs --tokenizer): after the chat template, each warm-up's token IDs are a
     prefix of the debaters' token IDs; reports the share of each debater prompt that is
     reusable in whole 16-token KV blocks, next to the cached tokens vLLM reported.

Usage (repository root):
    python -m pilot.input_audit results/final_<GPU> > results/input_audit.md
    python -m pilot.input_audit results/final_<GPU> --tokenizer meta-llama/Llama-3.1-8B-Instruct
"""

import argparse
import asyncio
import glob
import json
import os
import statistics as st
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from models.client import CallResult
from pilot.debate import AGENTS, question_text, run_debate

MODES = ("seq", "par", "l3a", "l3")
BLOCK = 16  # vLLM KV-cache block size (default)


# ----------------------------------------------------------------------------- loading

def load_runs(d: str, conc: int = 1) -> Dict[Tuple[str, int, str], Dict[str, Dict[str, Any]]]:
    """(task, seed, mode) -> {problem id: record}, from files recorded with --record-inputs."""
    runs: Dict[Tuple[str, int, str], Dict[str, Dict[str, Any]]] = {}
    for path in sorted(glob.glob(os.path.join(d, f"*_apcon_C{conc}_s*.jsonl"))):
        name = os.path.basename(path)[:-len(".jsonl")]
        task, mode = name.split("_")[:2]
        if mode not in MODES or not name.endswith(tuple(f"_s{s}" for s in range(10))):
            continue  # skips *_repeat and other tagged files
        seed = int(name.rsplit("_s", 1)[1])
        recs = {}
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if any("messages" not in c for c in r["calls"]):
                    raise SystemExit(f"{path}: not recorded with --record-inputs")
                recs[r["id"]] = r
        runs[(task, seed, mode)] = recs
    return runs


def calls(r: Dict[str, Any], rnd: int, kind: str = "debate") -> List[Dict[str, Any]]:
    """The record's calls of one kind in one round, ordered by agent."""
    return sorted((c for c in r["calls"] if c["rnd"] == rnd and c["kind"] == kind), key=lambda c: c["agent"])


# ----------------------------------------------------------------------------- replay through the harness

class ReplayClient:
    """Fake model: round 1 returns fixed upstream answers; records every request it receives."""

    def __init__(self, round1_answers: List[str]):
        self.answers = round1_answers
        self.sent: Dict[Tuple[int, int, str], List[Dict[str, str]]] = {}

    async def agenerate(self, messages, seed=None, max_tokens=None, role="", round=-1, **_):
        agent = int(role[len("agent"):])
        kind = "warm" if agent < 0 else "debate"
        self.sent[(round, agent, kind)] = [dict(m) for m in messages]
        await asyncio.sleep(0)
        text = self.answers[agent] if round == 0 and agent >= 0 else "replay \\boxed{0}"
        t = time.perf_counter()
        return CallResult(texts=[text], submit_time=t, completion_time=t, prompt_tokens=0,
                          cached_tokens=0, output_tokens=0, model="replay")


def replay(task: str, mode: str, problem: Dict[str, Any], round1_answers: List[str]):
    """Run the real harness for one debate with fixed round-1 answers; return what it sent."""
    client = ReplayClient(round1_answers)
    asyncio.run(run_debate(client, task, mode, problem, 0))
    return client.sent


# ----------------------------------------------------------------------------- checks

def check_round1(runs, task, seed) -> List[str]:
    """A: round-1 request identity across modes, and warm-up == debater request."""
    modes = [m for m in MODES if (task, seed, m) in runs]
    base = runs.get((task, seed, "seq"))
    if base is None:
        return [f"- A: no BASE file for {task} seed {seed}"]
    same = total = warm_ok = warm_n = 0
    for pid, r in base.items():
        ref = [(c["messages_sha256"], c["request_seed"]) for c in calls(r, 0)]
        for m in modes:
            other = runs[(task, seed, m)].get(pid)
            if other is None:
                continue
            got = [(c["messages_sha256"], c["request_seed"]) for c in calls(other, 0)]
            total += len(ref)
            same += sum(a == b for a, b in zip(ref, got))
            for w in calls(other, 0, "warm"):
                warm_n += 1
                warm_ok += all(w["messages"] == c["messages"] for c in calls(other, 0))
    line = f"- A, round-1 requests identical to BASE across {', '.join(modes)}: **{same}/{total}**"
    if warm_n:
        line += f"; round-1 warm-up equals the debaters' request: **{warm_ok}/{warm_n}**"
    return [line]


def check_replay(runs, task, seed, problems) -> List[str]:
    """B: feed BASE's round-1 answers through each mode's real code path."""
    base = runs.get((task, seed, "seq"))
    if base is None:
        return []
    exact = defaultdict(int)
    n = 0
    l3_info = l3_len = 0
    ratios = []
    for pid, r in base.items():
        p = problems.get(pid)
        if p is None:
            continue
        n += 1
        answers = [c["response"] for c in calls(r, 0)]
        recorded = [c["messages"] for c in calls(r, 1)]
        for m in ("seq", "par", "l3a"):
            sent = replay(task, m, p, answers)
            exact[m] += all(sent[(1, i, "debate")] == recorded[i] for i in range(AGENTS))
        sent = replay(task, "l3", p, answers)
        q = question_text(task, p)
        for i in range(AGENTS):
            text = "".join(x["content"] for x in sent[(1, i, "debate")])
            l3_info += q in text and all(a in text for a in answers)
            l3_len += 1
            released = sum(len(x["content"]) for x in recorded[i])
            ratios.append(len(text) / released)
    out = [f"- B, fixed-upstream replay on {n} problems (BASE's recorded round-1 answers through the harness):"]
    for m in ("seq", "par", "l3a"):
        out.append(f"  - {m}: round-2 requests identical to BASE's recorded ones in **{exact[m]}/{n}** problems")
    if ratios:
        out.append(f"  - l3: question and all three answers present in **{l3_info}/{l3_len}** debater "
                   f"prompts; prompt length vs released, median {st.median(ratios):.2f}x "
                   f"(range {min(ratios):.2f}-{max(ratios):.2f}); by design the wording and layout differ")
    return out


def check_self(runs, task, seed, problems) -> List[str]:
    """C: each recorded round-2 request equals its mode's construction from its own round-1 answers."""
    out = []
    for m in MODES:
        recs = runs.get((task, seed, m))
        if not recs:
            continue
        ok = n = 0
        for pid, r in recs.items():
            p = problems.get(pid)
            if p is None:
                continue
            n += 1
            sent = replay(task, m, p, [c["response"] for c in calls(r, 0)])
            good = all(sent[(1, c["agent"], "debate")] == c["messages"] for c in calls(r, 1))
            good &= all(sent[(1, -1, "warm")] == w["messages"] for w in calls(r, 1, "warm"))
            ok += good
        out.append(f"{m} {ok}/{n}")
    return [f"- C, recorded round-2 requests match their mode's construction: " + ", ".join(out)]


def check_tokens(runs, task, seed, tok) -> List[str]:
    """D: warm-up token IDs are a prefix of debater token IDs; reusable share in whole KV blocks."""
    def ids(msgs):
        return tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)

    out = []
    for m in ("l3a", "l3"):
        recs = runs.get((task, seed, m))
        if not recs:
            continue
        for rnd in (0, 1):
            prefix_ok = n = 0
            share, cached = [], []
            for r in recs.values():
                warm = calls(r, rnd, "warm")
                if not warm:
                    continue
                w = ids(warm[0]["messages"])
                # The warm-up ends with end-of-turn + assistant header, which debaters with more
                # text in the same turn do not share; the reusable part is the common prefix.
                for c in calls(r, rnd):
                    d = ids(c["messages"])
                    lcp = 0
                    while lcp < min(len(w), len(d)) and w[lcp] == d[lcp]:
                        lcp += 1
                    n += 1
                    prefix_ok += lcp >= len(w) - 5 or lcp == len(d)
                    share.append((lcp // BLOCK) * BLOCK / len(d))
                    cached.append(c["cached"] / max(c["prompt"], 1))
            if n:
                out.append(f"- D, {m} round {rnd + 1}: warm-up is a token prefix of the debater prompt "
                           f"(up to its closing turn tokens) in **{prefix_ok}/{n}** calls; reusable share of "
                           f"debater prompt (whole 16-token blocks) median **{st.median(share):.1%}**; "
                           f"cached share vLLM reported median **{st.median(cached):.1%}**")
    return out


# ----------------------------------------------------------------------------- main

def audit(runs, problems_by_task, tok=None) -> List[str]:
    lines = ["# Input audit: what each configuration sends to the model", "",
             "Generated by `python -m pilot.input_audit`. BASE = seq with prefix caching on; "
             "all files C=1 with recorded inputs.", ""]
    for task, seed in sorted({(t, s) for t, s, _ in runs}):
        problems = problems_by_task[task]
        lines.append(f"## {task}, sampling seed {seed}")
        lines += check_round1(runs, task, seed)
        lines += check_replay(runs, task, seed, problems)
        lines += check_self(runs, task, seed, problems)
        if tok is not None:
            lines += check_tokens(runs, task, seed, tok)
        lines.append("")
    lines += ["Reading: if A and B (seq, par, l3a) are complete, L1 and L3a change only *when* requests "
              "are sent, never *what* is sent; any answer differences between them come from sampling "
              "or batching, not from their inputs. Full L3 changes the round-2 wording by design, which "
              "is why its accuracy is held to the guardrail."]
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dir", help="results/final_<GPU>")
    ap.add_argument("--tokenizer", default=None, help="HF id for check D, e.g. meta-llama/Llama-3.1-8B-Instruct")
    a = ap.parse_args()
    runs = load_runs(a.dir)
    if not runs:
        raise SystemExit(f"no recorded C=1 files in {a.dir}")
    from pilot.debate import load_problems
    problems_by_task = {}
    for task in {t for t, _, _ in runs}:
        n = max(len(v) for (t, _, _), v in runs.items() if t == task)
        problems_by_task[task] = {p["id"]: p for p in load_problems(task, n)}
    tok = None
    if a.tokenizer:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(a.tokenizer)
    print("\n".join(audit(runs, problems_by_task, tok)))


if __name__ == "__main__":
    main()
