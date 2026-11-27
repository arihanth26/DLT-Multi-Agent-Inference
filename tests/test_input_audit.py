"""Check pilot.input_audit on synthetic recorded runs (no GPU, no network).

The fake model returns different text for every call, so seq/par/l3a would not match each other
by accident; the audit must still find that L3a sends the released round-2 requests once the
round-1 answers are fixed, and must catch a tampered request.
"""

import asyncio
import copy
import time

from models.client import CallResult
from pilot.debate import run_debate
from pilot.input_audit import audit


class SeededModel:
    """Answers depend on the sampling seed and the mode tag, like real sampling noise would."""

    def __init__(self, tag):
        self.tag = tag

    async def agenerate(self, messages, seed=None, **kwargs):
        await asyncio.sleep(0)
        t = time.perf_counter()
        return CallResult(texts=[f"{self.tag}-{seed} \\boxed{{{seed % 5}}}"], submit_time=t,
                          completion_time=t, prompt_tokens=100, cached_tokens=50,
                          output_tokens=8, model="fake")


PROBLEMS = {f"g{i}": {"id": f"g{i}", "question": f"What is {i} plus 2?", "gold": str(i + 2)}
            for i in range(3)}


def make_runs():
    runs = {}
    for mode in ("seq", "par", "l3a", "l3"):
        recs = {}
        for pid, p in PROBLEMS.items():
            recs[pid] = asyncio.run(run_debate(SeededModel(mode), "gsm8k", mode, p, 0, record_inputs=True))
        runs[("gsm8k", 0, mode)] = recs
    return runs


def test_audit_confirms_l3a_inputs():
    text = "\n".join(audit(make_runs(), {"gsm8k": PROBLEMS}))
    assert "round-1 requests identical to BASE across seq, par, l3a, l3: **36/36**" in text
    assert "warm-up equals the debaters' request: **6/6**" in text
    for m in ("seq", "par", "l3a"):
        assert f"  - {m}: round-2 requests identical to BASE's recorded ones in **3/3** problems" in text
    assert "question and all three answers present in **9/9**" in text
    assert "seq 3/3, par 3/3, l3a 3/3, l3 3/3" in text


def test_audit_catches_a_changed_request():
    runs = make_runs()
    bad = copy.deepcopy(runs)
    call = next(c for c in bad[("gsm8k", 0, "l3a")]["g0"]["calls"] if c["rnd"] == 1 and c["kind"] == "debate")
    call["messages"][-1]["content"] += " (tampered)"
    text = "\n".join(audit(bad, {"gsm8k": PROBLEMS}))
    assert "l3a 2/3" in text


class DictTokenizer:
    """Like newer transformers: apply_chat_template(tokenize=True) returns a dict, one token per char."""

    def apply_chat_template(self, msgs, add_generation_prompt=True, tokenize=True):
        text = "".join(f"<{m['role']}>{m['content']}<eot>" for m in msgs) + "<asst>"
        return {"input_ids": [ord(ch) for ch in text], "attention_mask": [1] * len(text)}


def test_token_check_unwraps_dicts_and_measures_reuse():
    from pilot.input_audit import check_tokens
    lines = check_tokens(make_runs(), "gsm8k", 0, DictTokenizer())
    l3a = next(x for x in lines if "l3a round 1" in x)
    assert "in **9/9** calls" in l3a                     # round-1 warm-up == debater prompt
    share = float(l3a.split("median **")[1].split("%")[0])
    assert share > 50                                     # not the 0% a dict-length bug gives
