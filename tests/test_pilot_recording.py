"""Check that optional pilot recording preserves requests and snapshots message history.

Run with python -m pytest tests/test_pilot_recording.py.
"""

import asyncio
import copy
import hashlib
import json
import time

from models.client import CallResult
from pilot.debate import run_debate


class ReplayClient:
    """A deterministic fake that retains exactly what the harness submits."""

    def __init__(self):
        """Start with no captured requests."""
        self.requests = []

    async def agenerate(self, messages, **kwargs):
        """Return a seeded answer after yielding to other concurrent calls."""
        self.requests.append((copy.deepcopy(messages), dict(kwargs)))
        start = time.perf_counter()
        await asyncio.sleep(0)
        return CallResult(
            texts=[f"Answer: \\boxed{{{kwargs['seed'] % 7}}}"],
            submit_time=start, completion_time=time.perf_counter(),
            prompt_tokens=100, cached_tokens=0, output_tokens=8, model="fake",
        )


def test_recording_preserves_requests_and_history():
    """Recording must neither change submitted payloads nor mutate earlier snapshots."""
    problem = {"id": "fixture", "question": "What is two plus two?", "gold": "4"}

    async def check():
        for mode in ("seq", "par", "l3a", "l3", "single"):
            plain, recorded = ReplayClient(), ReplayClient()
            a = await run_debate(plain, "gsm8k", mode, problem, 0)
            b = await run_debate(recorded, "gsm8k", mode, problem, 0, record_inputs=True)
            assert plain.requests == recorded.requests
            assert a["final"] == b["final"] and a["preds"] == b["preds"]
            assert all("messages" not in c for c in a["calls"])
            for call in b["calls"]:
                expected = hashlib.sha256(json.dumps(
                    call["messages"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                assert call["messages_sha256"] == expected
                assert "\\boxed" in call["response"]
                if call["rnd"] == 0:
                    assert len(call["messages"]) == 1

    asyncio.run(check())
