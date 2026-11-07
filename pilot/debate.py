"""Initial-results pilot for the approved proposal: multi-agent debate on GSM8K and QuALITY.

Runs ONE configuration against an already-running vLLM server and appends one JSON row per
debate (with a per-call trace) to --out. slurm/pilot.sbatch runs the whole grid.

Debate follows Du et al. (3 agents, 2 rounds, majority vote). The prompts approximate the
released code; the preregistered baseline must eventually wrap the released code itself.

Configurations (the prefix-caching lever L2 is a SERVER flag; --apc only labels the row and
must match how the server was started):

  mode    | dispatch                 | prompts                 | name in the report
  --------+--------------------------+-------------------------+-------------------------------
  seq     | sequential, framework order | as released           | BASE when apc=on; neither lever when apc=off
  par     | L1: concurrent per round | as released             | L1 (+L2 if apc=on)
  l3a     | L1 + prefill-only warm-up | as released (unchanged) | L3a: must match par answers
  l3      | l3a + shared round-2 transcript | CHANGED (round 2)  | L3: accuracy is the guardrail
  single  | one agent, one call      | round 1 only            | multi-agent overhead reference

Problems are fixed by --problem-seed (default 0) so every configuration sees the same problems.
Per-call sampling seeds depend only on (--seed, problem, agent, round), so seq, par and l3a send
byte-identical requests and their answers should agree.

Usage (from the repository root, server running on port 8000):
    python -m pilot.debate --task quality --mode par --apc on --n 20
    python -m pilot.debate --task gsm8k --mode seq --apc on --n 30 --conc 4
"""

import argparse
import asyncio
import hashlib
import json
import random
import re
import time
import urllib.request
from collections import Counter
from typing import Any, Dict, List, Optional

from data.gsm8k.preprocess import normalize_number, parse_gold_answer
from models.client import CallResult, LLMClient
from models.model_config import SamplingConfig

# Approved proposal: temperature 0.7, top-p 0.9, at most 512 output tokens.
SAMPLING = SamplingConfig(temperature=0.7, top_p=0.9, max_tokens=512)
AGENTS, ROUNDS = 3, 2
LETTERS = "ABCD"
MODES = ["seq", "par", "l3a", "l3", "single"]

FORMAT = {
    "gsm8k": "Your final answer should be a single numerical number, in the form \\boxed{answer}, "
             "at the end of your response.",
    "quality": "Your final answer should be a single letter (A, B, C, or D), in the form "
               "\\boxed{answer}, at the end of your response.",
}


# ----------------------------------------------------------------------------- problems

def load_problems(task: str, n: int, problem_seed: int = 0) -> List[Dict[str, Any]]:
    """Return n problems fixed by problem_seed. QuALITY takes one question per article so that
    no two problems share a story (which would give free cross-problem cache hits)."""
    from datasets import load_dataset

    rng = random.Random(problem_seed)
    if task == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split="test")
        return [
            {"id": f"gsm8k-test-{i}", "question": ds[i]["question"].strip(),
             "gold": parse_gold_answer(ds[i]["answer"])}
            for i in rng.sample(range(len(ds)), n)
        ]
    ds = load_dataset("emozilla/quality", split="validation")
    order = list(range(len(ds)))
    rng.shuffle(order)
    seen, out = set(), []
    for i in order:
        row = ds[i]
        key = hashlib.md5(row["article"].encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": f"quality-val-{i}", "article": row["article"], "question": row["question"],
                    "options": list(row["options"]), "gold": LETTERS[int(row["answer"])]})
        if len(out) == n:
            break
    return out


# ----------------------------------------------------------------------------- prompts

def round1_prompt(task: str, p: Dict[str, Any]) -> str:
    """Round-1 prompt, identical for every debater. For QuALITY the story comes first."""
    if task == "gsm8k":
        return f"Can you solve the following math problem? {p['question']} Explain your reasoning. {FORMAT[task]}"
    opts = "\n".join(f"({LETTERS[k]}) {o}" for k, o in enumerate(p["options"]))
    return (f"{p['article']}\n\nQuestion: {p['question']}\n{opts}\n\n"
            f"Answer the question about the story above. Explain your reasoning. {FORMAT[task]}")


def round2_released(task: str, others: List[str]) -> str:
    """Round-2 user turn as in the released debate code: the OTHER agents' answers only."""
    s = "These are the solutions to the problem from other agents: "
    s += "".join(f"\n\n One agent solution: ```{o}```" for o in others)
    return (s + "\n\n Using the solutions from other agents as additional information, can you "
            f"provide your answer to the problem? {FORMAT[task]}")


def round2_shared_prefix(task: str, r1: str, answers: List[str]) -> str:
    """L3: one transcript of EVERY answer in fixed order, identical for all debaters."""
    s = r1 + "\n\nThese are the solutions to the problem from all agents in this debate:"
    s += "".join(f"\n\nAgent {k + 1} solution: ```{a}```" for k, a in enumerate(answers))
    return s + "\n\n"


def round2_agent_line(task: str, i: int) -> str:
    """L3: the short agent-specific line appended after the shared transcript."""
    return (f"You are Agent {i + 1}; the solution labelled Agent {i + 1} is your own. Using the "
            "solutions from the other agents as additional information, can you provide your "
            f"answer to the problem? {FORMAT[task]}")


# ----------------------------------------------------------------------------- scoring

def parse_answer(task: str, text: str) -> Optional[str]:
    """Answer inside the last \\boxed{...}; falls back to the whole text."""
    boxed = re.findall(r"\\boxed\{([^}]*)\}", text)
    s = boxed[-1] if boxed else text
    if task == "quality":
        letters = re.findall(r"\b([ABCD])\b", s)
        return letters[-1] if letters else None
    nums = re.findall(r"-?\d[\d,]*\.?\d*", s)
    return normalize_number(nums[-1]) if nums else None


def majority(preds: List[Optional[str]]) -> Optional[str]:
    """Most common non-empty answer; ties go to the earliest agent, as in the released code."""
    votes = Counter(p for p in preds if p is not None).most_common(1)
    return votes[0][0] if votes else None


# ----------------------------------------------------------------------------- one debate

def call_seed(run_seed: int, pid: str, agent: int, rnd: int) -> int:
    """Per-request sampling seed, identical across configurations for the same call."""
    return int(hashlib.md5(f"{run_seed}-{pid}-{agent}-{rnd}".encode()).hexdigest()[:8], 16)


def trace_row(r: CallResult, kind: str, agent: int, rnd: int, t0: float) -> Dict[str, Any]:
    """Flatten a CallResult into the per-call trace (times relative to the debate start)."""
    return {"kind": kind, "agent": agent, "rnd": rnd,
            "submit": r.submit_time - t0, "done": r.completion_time - t0, "lat": r.latency,
            "ttft": (r.first_token_time - r.submit_time) if r.first_token_time else None,
            "prompt": r.prompt_tokens, "cached": r.cached_tokens, "out": r.output_tokens}


async def run_debate(client: LLMClient, task: str, mode: str, p: Dict[str, Any], run_seed: int,
                     record_inputs: bool = False) -> Dict[str, Any]:
    """Run one debate (or single call) and return its record."""
    n_agents, n_rounds = (1, 1) if mode == "single" else (AGENTS, ROUNDS)
    r1 = round1_prompt(task, p)
    trace: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    async def call(msgs, agent, rnd, kind="debate", max_tokens=None):
        seed = call_seed(run_seed, p["id"], agent, rnd)
        snapshot = [dict(m) for m in msgs] if record_inputs else None
        res = await client.agenerate(msgs, seed=seed,
                                     max_tokens=max_tokens, role=f"agent{agent}", round=rnd)
        row = trace_row(res, kind, agent, rnd, t0)
        if record_inputs:
            row.update(messages=snapshot, response=res.text, request_seed=seed,
                       messages_sha256=hashlib.sha256(json.dumps(
                           snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                       sampling={"temperature": SAMPLING.temperature, "top_p": SAMPLING.top_p,
                                 "max_tokens": max_tokens or SAMPLING.max_tokens})
        trace.append(row)
        return res.text

    async def warm(msgs, rnd):
        # Prefill-only request: caches the shared prefix once before the fan-out (1 output token).
        await call(msgs, -1, rnd, kind="warm", max_tokens=1)

    ctx = [[{"role": "user", "content": r1}] for _ in range(n_agents)]
    answers: List[str] = []
    for rnd in range(n_rounds):
        if rnd == 0:
            msgs = ctx
            if mode in ("l3a", "l3"):
                await warm([{"role": "user", "content": r1}], rnd)
        elif mode == "l3":
            shared = round2_shared_prefix(task, r1, answers)
            await warm([{"role": "user", "content": shared}], rnd)
            msgs = [[{"role": "user", "content": shared + round2_agent_line(task, i)}] for i in range(n_agents)]
        else:
            for i in range(n_agents):
                ctx[i].append({"role": "assistant", "content": answers[i]})
                ctx[i].append({"role": "user", "content": round2_released(
                    task, [answers[j] for j in range(n_agents) if j != i])})
            msgs = ctx
        if mode == "seq" or mode == "single":
            answers = [await call(msgs[i], i, rnd) for i in range(n_agents)]
        else:
            answers = list(await asyncio.gather(*(call(msgs[i], i, rnd) for i in range(n_agents))))
    T = time.perf_counter() - t0

    preds = [parse_answer(task, a) for a in answers]
    final = majority(preds)
    # Critical path: per round, the slowest debater (plus the warm-up if any).
    cp = 0.0
    for rnd in range(n_rounds):
        cp += max(c["lat"] for c in trace if c["rnd"] == rnd and c["kind"] == "debate")
        cp += sum(c["lat"] for c in trace if c["rnd"] == rnd and c["kind"] == "warm")
    return {"task": task, "mode": mode, "id": p["id"], "T": T, "cp": cp, "final": final,
            "gold": p["gold"], "correct": final == p["gold"], "preds": preds,
            "answer_tokens": [c["out"] for c in trace if c["kind"] == "debate"], "calls": trace}


# ----------------------------------------------------------------------------- main

def post(base_url: str, path: str) -> bool:
    """POST to a vLLM admin endpoint (needs VLLM_SERVER_DEV_MODE=1 on the server)."""
    root = base_url.rsplit("/v1", 1)[0]
    try:
        urllib.request.urlopen(urllib.request.Request(root + path, method="POST"), timeout=60)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"WARN {path}: {e}")
        return False


async def amain(a: argparse.Namespace) -> None:
    client = LLMClient(a.model, base_url=a.base_url, sampling=SAMPLING)
    problems = load_problems(a.task, a.n, a.problem_seed)
    for _ in range(3):  # warm CUDA graphs and the tokenizer; not measured
        await client.agenerate([{"role": "user", "content": "Say hi."}], max_tokens=8)
    # Start every configuration from an empty prefix cache, so it cannot reuse the previous
    # configuration's identical round-1 prompts.
    if not post(client.base_url, "/reset_prefix_cache") and a.apc == "on":
        raise SystemExit("Could not reset the prefix cache: start vLLM with VLLM_SERVER_DEV_MODE=1")

    sem = asyncio.Semaphore(a.conc)  # closed loop: C debates in flight
    meta = {"apc": a.apc, "conc": a.conc, "seed": a.seed, "problem_seed": a.problem_seed, "model": a.model}
    start = time.perf_counter()
    with open(a.out, "a") as f:
        async def one(p):
            async with sem:
                rec = await run_debate(client, a.task, a.mode, p, a.seed, a.record_inputs)
            rec.update(meta)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            return rec

        recs = await asyncio.gather(*(one(p) for p in problems))
    wall = time.perf_counter() - start
    Ts = sorted(r["T"] for r in recs)
    acc = sum(r["correct"] for r in recs) / len(recs)
    print(f"{a.task:8} {a.mode:6} apc={a.apc} C={a.conc} n={len(recs)}: median T {Ts[len(Ts) // 2]:.2f}s "
          f"acc {acc:.2f} tasks/min {60 * len(recs) / wall:.1f}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one pilot configuration of the debate.")
    ap.add_argument("--task", required=True, choices=["gsm8k", "quality"])
    ap.add_argument("--mode", required=True, choices=MODES)
    ap.add_argument("--apc", required=True, choices=["on", "off"], help="Label; must match the server flag.")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--conc", type=int, default=1, help="Concurrent debates C (closed loop).")
    ap.add_argument("--seed", type=int, default=0, help="Sampling seed (preregistered: 0, 1, 2).")
    ap.add_argument("--problem-seed", type=int, default=0)
    ap.add_argument("--model", default="llama-3.1-8b")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--out", default="results/pilot/pilot.jsonl")
    ap.add_argument("--record-inputs", action="store_true",
                    help="Retain request messages, seeds, sampling settings and full responses for auditing.")
    a = ap.parse_args()
    if a.mode in ("l3a", "l3") and a.apc == "off":
        ap.error("L3 sits on top of L1 and L2: run it with --apc on")
    asyncio.run(amain(a))


if __name__ == "__main__":
    main()
