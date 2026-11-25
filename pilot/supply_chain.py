"""Supply-Chain Disruption Response (SCD): a three-stage multi-agent workflow (exploratory extension).

Combines the two published architectures the proposal cites:
  Stage 1  (rnd 0) Du et al. fan-out: Demand Planner, Procurement Analyst, Logistics Analyst each
                   read the shared dossier and propose a plan.
  Stage 2  (rnd 1) Du et al. debate round: each specialist reads the other two answers and revises.
  Stage 3  (rnd 2-4) AutoGen SelectorGroupChat-style manager, strictly serial:
                   rnd 2 Coordinator picks ONE specialist and writes a follow-up question,
                   rnd 3 that specialist answers it,
                   rnd 4 Coordinator commits the final plan as \\boxed{letter}.
9 model calls per task. The dossier is the first thing in EVERY prompt, so it is the shared prefix.

Modes (same names and meaning as pilot/debate.py; L2 caching is the server flag, --apc labels it):
  seq     all 9 calls one at a time                         -> BASE (apc on) / neither lever (apc off)
  par     stages 1 and 2 dispatched concurrently (L1)       -> L1 (+L2)
  l3a     par + 1-token warm-up of the shared dossier prefix before stage 1; prompts unchanged
  l3      l3a + one shared stage-2 transcript of all three answers + a short role line
  single  one Coordinator call on the dossier               -> single-agent reference

Scoring: the Coordinator's final letter vs the solver's gold (data/supply_chain/generate.py).
The stage-2 majority vote is also recorded, so stage 3's effect on accuracy can be read off.

Usage (server running on port 8000, from the repository root):
    python -m pilot.supply_chain --mode par --apc on --n 100 --conc 1 --out results/scd/scd.jsonl
"""

import argparse
import asyncio
import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional

from data.supply_chain.generate import load_scenarios
from models.client import LLMClient
from pilot.debate import SAMPLING, call_seed, majority, parse_answer, post, trace_row

MODES = ["seq", "par", "l3a", "l3", "single"]
ROLES = [
    ("Demand Planner", "Focus on the demand forecast, the stock position and when the shelf runs empty."),
    ("Procurement Analyst", "Focus on supplier unit costs, lead times, weekly capacity and minimum orders."),
    ("Logistics Analyst", "Focus on freight lanes: transit times, per-unit and fixed shipment costs."),
]
FORMAT = ("Your final answer should be a single letter (A, B, C, or D), in the form \\boxed{answer}, "
          "at the end of your response.")
SELECT_MAX_TOKENS = 128  # the Coordinator's selection turn is short by design


def base_prompt(p: Dict[str, Any]) -> str:
    """Dossier + question + options: identical leading text in every call (the shared prefix)."""
    opts = "\n".join(f"({L}) {o}" for L, o in zip("ABCD", p["options"]))
    return f"{p['dossier']}\n\n# Decision\n{p['question']}\n{opts}\n\n"


def role_line(i: int) -> str:
    name, focus = ROLES[i]
    return (f"You are the {name} on the disruption response team. {focus} Cost each plan "
            f"under the policy, explain briefly, and recommend one. {FORMAT}")


def stage2_released(others: List[str]) -> str:
    """Du et al. style: the OTHER agents' answers only, appended to the agent's own history."""
    s = "These are the recommendations from the other specialists: "
    s += "".join(f"\n\n One specialist's answer: ```{o}```" for o in others)
    return (s + "\n\n Using their analysis as additional information, re-check the costs and give "
            f"your recommendation. {FORMAT}")


def transcript(answers: List[str]) -> str:
    """All specialists' latest answers in fixed role order (used by stage 3, and by L3 in stage 2)."""
    return "".join(f"\n\n## {ROLES[k][0]}\n```{a}```" for k, a in enumerate(answers))


def stage2_shared(answers: List[str]) -> str:
    return "# Stage-1 recommendations from all specialists" + transcript(answers) + "\n\n"


def stage2_role_line(i: int) -> str:
    return (f"You are the {ROLES[i][0]}; the section with your title is your own answer. Using the "
            f"others' analysis as additional information, re-check the costs and give your recommendation. {FORMAT}")


def select_prompt(answers: List[str]) -> str:
    names = ", ".join(r[0] for r in ROLES)
    return ("# Specialist recommendations after debate" + transcript(answers) + "\n\n"
            "You are the Coordinator. Before deciding, you may ask ONE specialist ONE follow-up "
            f"question. Choose from: {names}. Reply in exactly two lines:\n"
            "SPECIALIST: <name>\nQUESTION: <one question>")


def parse_selection(text: str) -> (int, str):
    """Chosen specialist index (default: Procurement Analyst) and the follow-up question."""
    m = re.search(r"SPECIALIST:\s*(.+)", text, re.I)
    who = (m.group(1) if m else text).lower()
    idx = next((k for k, (n, _) in enumerate(ROLES) if n.split()[0].lower() in who), 1)
    q = re.search(r"QUESTION:\s*(.+)", text, re.I | re.S)
    question = (q.group(1).strip() if q else "Which plan has the lowest total cost, and why?")[:600]
    return idx, question


def followup_prompt(i: int, question: str) -> str:
    return (f"You are the {ROLES[i][0]}. {ROLES[i][1]} The Coordinator asks you: {question}\n"
            "Answer concisely with the numbers that matter.")


def final_prompt(answers: List[str], i: int, question: str, reply: str) -> str:
    return ("# Specialist recommendations after debate" + transcript(answers)
            + f"\n\n# Follow-up\nCoordinator to {ROLES[i][0]}: {question}\n{ROLES[i][0]}: {reply}\n\n"
            f"You are the Coordinator. Commit the team to one recovery plan. {FORMAT}")


def single_prompt() -> str:
    return f"You are the Coordinator. Cost each plan under the policy and choose one. {FORMAT}"


async def run_task(client: LLMClient, mode: str, p: Dict[str, Any], run_seed: int,
                   record_inputs: bool = False) -> Dict[str, Any]:
    """Run one SCD workflow and return its record (same trace format as pilot/debate.py)."""
    base = base_prompt(p)
    trace: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    async def call(content_or_msgs, agent, rnd, kind="debate", max_tokens=None):
        msgs = ([{"role": "user", "content": content_or_msgs}] if isinstance(content_or_msgs, str)
                else content_or_msgs)
        seed = call_seed(run_seed, p["id"], agent, rnd)
        snapshot = [dict(m) for m in msgs] if record_inputs else None
        res = await client.agenerate(msgs, seed=seed, max_tokens=max_tokens,
                                     role=f"agent{agent}", round=rnd)
        row = trace_row(res, kind, agent, rnd, t0)
        if record_inputs:
            row.update(messages=snapshot, response=res.text, request_seed=seed,
                       messages_sha256=hashlib.sha256(json.dumps(
                           snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
        trace.append(row)
        return res.text

    async def stage(prompts, rnd):
        if mode == "seq":
            return [await call(m, i, rnd) for i, m in enumerate(prompts)]
        return list(await asyncio.gather(*(call(m, i, rnd) for i, m in enumerate(prompts))))

    if mode == "single":
        final_text = await call(base + single_prompt(), 3, 4, kind="coord")
        final = parse_answer("quality", final_text)
        return _record(p, mode, t0, trace, final, None, [final], None)

    # Stage 1: fan-out.
    if mode in ("l3a", "l3"):
        await call(base, -1, 0, kind="warm", max_tokens=1)
    ctx = [[{"role": "user", "content": base + role_line(i)}] for i in range(3)]
    s1 = await stage(ctx, 0)

    # Stage 2: debate round.
    if mode == "l3":
        shared = base + stage2_shared(s1)
        await call(shared, -1, 1, kind="warm", max_tokens=1)
        s2 = await stage([shared + stage2_role_line(i) for i in range(3)], 1)
    else:
        for i in range(3):
            ctx[i] += [{"role": "assistant", "content": s1[i]},
                       {"role": "user", "content": stage2_released([s1[j] for j in range(3) if j != i])}]
        s2 = await stage(ctx, 1)
    preds = [parse_answer("quality", a) for a in s2]

    # Stage 3: manager-serialized (always sequential: each call depends on the previous one).
    sel = await call(base + select_prompt(s2), 3, 2, kind="coord", max_tokens=SELECT_MAX_TOKENS)
    who, question = parse_selection(sel)
    reply = await call(base + followup_prompt(who, question), who, 3, kind="followup")
    final_text = await call(base + final_prompt(s2, who, question, reply), 3, 4, kind="coord")
    final = parse_answer("quality", final_text)
    return _record(p, mode, t0, trace, final, majority(preds), preds, ROLES[who][0])


def _record(p, mode, t0, trace, final, vote, preds, chosen) -> Dict[str, Any]:
    T = time.perf_counter() - t0
    par_rounds = {c["rnd"] for c in trace if c["kind"] == "debate"}
    cp = sum(max(c["lat"] for c in trace if c["rnd"] == r and c["kind"] == "debate") for r in par_rounds)
    cp += sum(c["lat"] for c in trace if c["kind"] in ("warm", "coord", "followup"))
    serial = sum(c["lat"] for c in trace if c["kind"] in ("coord", "followup"))
    return {"task": "scd", "mode": mode, "id": p["id"], "T": T, "cp": cp, "stage3_s": serial,
            "final": final, "vote": vote, "gold": p["gold"], "correct": final == p["gold"],
            "vote_correct": vote == p["gold"] if vote else None, "preds": preds, "chosen": chosen,
            "answer_tokens": [c["out"] for c in trace if c["kind"] != "warm"], "calls": trace}


async def amain(a: argparse.Namespace) -> None:
    client = LLMClient(a.model, base_url=a.base_url, sampling=SAMPLING)
    problems = load_scenarios(a.n, a.problem_seed)
    for _ in range(3):
        await client.agenerate([{"role": "user", "content": "Say hi."}], max_tokens=8)
    if not post(client.base_url, "/reset_prefix_cache") and a.apc == "on":
        raise SystemExit("Could not reset the prefix cache: start vLLM with VLLM_SERVER_DEV_MODE=1")
    sem = asyncio.Semaphore(a.conc)
    meta = {"apc": a.apc, "conc": a.conc, "seed": a.seed, "problem_seed": a.problem_seed, "model": a.model}
    start = time.perf_counter()
    with open(a.out, "a") as f:
        async def one(p):
            async with sem:
                rec = await run_task(client, a.mode, p, a.seed, a.record_inputs)
            rec.update(meta)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            return rec
        recs = await asyncio.gather(*(one(p) for p in problems))
    wall = time.perf_counter() - start
    Ts = sorted(r["T"] for r in recs)
    acc = sum(r["correct"] for r in recs) / len(recs)
    print(f"scd      {a.mode:6} apc={a.apc} C={a.conc} n={len(recs)}: median T {Ts[len(Ts) // 2]:.2f}s "
          f"acc {acc:.2f} tasks/min {60 * len(recs) / wall:.1f}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one configuration of the SCD workflow.")
    ap.add_argument("--mode", required=True, choices=MODES)
    ap.add_argument("--apc", required=True, choices=["on", "off"], help="Label; must match the server flag.")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--conc", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--problem-seed", type=int, default=0)
    ap.add_argument("--model", default="llama-3.1-8b")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--out", default="results/scd/scd.jsonl")
    ap.add_argument("--record-inputs", action="store_true")
    a = ap.parse_args()
    if a.mode in ("l3a", "l3") and a.apc == "off":
        ap.error("L3 sits on top of L1 and L2: run it with --apc on")
    asyncio.run(amain(a))


if __name__ == "__main__":
    main()
