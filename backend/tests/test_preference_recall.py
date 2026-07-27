"""the one test in this suite that isn't fully offline (P20's stated exception) --
retrieval quality can't be judged with a fake embedding, so this hits the real
Qdrant + Gemini and expects scripts/seed_memory.py to have already run against
that project. skips itself when no live credentials are configured."""

import json
from pathlib import Path

import pytest

from app.config import settings
from app.memory.collections import pref_id

SCENARIOS = json.loads((Path(__file__).parent / "scenarios" / "preferences.json").read_text())

pytestmark = pytest.mark.skipif(
    not settings.GEMINI_API_KEY or not settings.QDRANT_URL,
    reason="needs live GEMINI_API_KEY and QDRANT_URL plus a seed_memory.py run",
)


async def test_preference_recall_scenarios(db, fake_lyzr):
    from app.agents import policy_gate

    def canned_policy_response(payload):
        if payload.get("mode") == "applies_check":
            return {"applies": True}
        return {"clarifying_question": "placeholder -- retrieval test doesn't exercise this answer"}

    fake_lyzr.responses["policy"] = canned_policy_response

    failures = []
    correct = 0

    for case in SCENARIOS:
        result = await policy_gate.evaluate(db, case["instruction"], "recall-test")
        expected_id = pref_id(case["expect"]) if case["expect"] is not None else None
        got_id = result.matched_policy_id if result.verdict == "ACT" else None

        if got_id == expected_id:
            correct += 1
        else:
            failures.append({"instruction": case["instruction"], "expected": expected_id, "got": got_id})

    if failures:
        print(f"\n{len(failures)} recall failures:")
        for f in failures:
            print(f"  {f['instruction']!r}: expected {f['expected']}, got {f['got']}")

    assert correct >= 18, f"only {correct}/20 scenarios matched the expected policy"
