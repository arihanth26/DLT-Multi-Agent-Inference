"""SCD generator and workflow checks with a fake model (no GPU, no network).

Run with python -m pytest tests/test_supply_chain.py.
"""

import asyncio
import copy
import time

from data.supply_chain.generate import (HORIZON, MARGIN, load_scenarios, make_scenario, plan_cost)
from models.client import CallResult
from pilot.supply_chain import base_prompt, run_task


class FakeClient:
    """Answers \\boxed{B} after a fixed delay; records every request."""

    def __init__(self, delay=0.02):
        self.delay, self.requests = delay, []

    async def agenerate(self, messages, **kw):
        self.requests.append((copy.deepcopy(messages), dict(kw)))
        start = time.perf_counter()
        await asyncio.sleep(self.delay)
        text = "SPECIALIST: Logistics Analyst\nQUESTION: Is Air worth it?" if kw.get("round") == 2 \
            else "Plan B is cheapest. \\boxed{B}"
        return CallResult(texts=[text], submit_time=start, completion_time=time.perf_counter(),
                          prompt_tokens=100, cached_tokens=0, output_tokens=10, model="fake")


def test_generator_is_deterministic_and_unambiguous():
    for i in range(30):
        sc = make_scenario(0, i)
        assert sc == make_scenario(0, i)
        totals = sorted(plan_cost(sc, p)["total"] for p in sc["plans"])
        assert totals[1] - totals[0] >= MARGIN * totals[1]
        gold = "ABCD"[min(range(4), key=lambda k: plan_cost(sc, sc["plans"][k])["total"])]
        assert gold == sc["gold"] and len(sc["demand"]) == HORIZON


def test_workflow_call_structure_and_speedup():
    p = load_scenarios(1, 0)[0]
    base = base_prompt(p)

    async def go(mode):
        c = FakeClient()
        rec = await run_task(c, mode, p, 0)
        return c, rec

    out = {m: asyncio.run(go(m)) for m in ("seq", "par", "l3a", "l3", "single")}
    for m, (c, rec) in out.items():
        first_user = [r[0][0]["content"] for r in c.requests]
        assert all(s.startswith(base) for s in first_user), m      # dossier is the shared prefix
        assert rec["final"] == "B" and rec["chosen"] in (None, "Logistics Analyst")
    n_calls = {m: len(c.requests) for m, (c, _) in out.items()}
    assert n_calls == {"seq": 9, "par": 9, "l3a": 10, "l3": 11, "single": 1}
    # seq, par and l3a send identical debate requests (only dispatch and the warm-up differ).
    strip = lambda c: sorted(str(r) for r in c.requests if r[1].get("max_tokens") != 1)
    assert strip(out["seq"][0]) == strip(out["par"][0]) == strip(out["l3a"][0])
    # Parallel stages 1-2 cut 9 serial calls to 2 + 3 serial = 5 on the critical path.
    assert out["par"][1]["T"] < 0.75 * out["seq"][1]["T"]
