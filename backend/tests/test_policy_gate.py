from app.agents import policy_gate
from app.ledger.models import Clarification
from app.memory import qdrant_client as qdrant


async def test_high_score_match_acts_and_increments_times_applied(db, fake_qdrant, fake_embed, fake_lyzr):
    text = "archive the saas times newsletter"
    await qdrant.upsert_preference(
        "pref-1", text, {"scope": "email", "confidence": 1.0, "provenance": "explicit", "times_applied": 0}
    )
    fake_lyzr.responses["policy"] = {"applies": True}

    result = await policy_gate.evaluate(db, text, "trace-1")

    assert result.verdict == "ACT"
    assert result.matched_policy_id == "pref-1"
    assert fake_qdrant.collections["preferences"]["pref-1"].payload["times_applied"] == 1


async def test_below_threshold_asks_exactly_one_question(db, fake_qdrant, fake_embed, fake_lyzr):
    await qdrant.upsert_preference(
        "pref-1", "newsletters are archived automatically",
        {"scope": "email", "confidence": 1.0, "provenance": "explicit", "times_applied": 0},
    )
    fake_lyzr.responses["policy"] = {"clarifying_question": "What time should external meetings start?"}

    result = await policy_gate.evaluate(db, "set up time with Rahul next week", "trace-2")

    assert result.verdict == "CLARIFY"
    assert result.clarifying_question == "What time should external meetings start?"

    rows = db.query(Clarification).all()
    assert len(rows) == 1
    assert rows[0].answer_text is None


async def test_answered_clarification_is_not_asked_twice(db, fake_qdrant, fake_embed, fake_lyzr):
    instruction = "set up time with Rahul next week"
    row = Clarification(
        instruction_text=instruction,
        question_text="When do external meetings work best?",
        answer_text="afternoons after 2pm",
        resulting_policy_id="pref-new",
    )
    db.add(row)
    db.commit()

    result = await policy_gate.evaluate(db, instruction, "trace-3")

    assert result.verdict == "ACT"
    assert result.matched_policy_id == "pref-new"
    assert fake_lyzr.calls == []  # never had to ask the model anything -- pure precedent match


async def test_learn_upserts_explicit_full_confidence(db, fake_qdrant, fake_embed, fake_lyzr):
    row = Clarification(
        instruction_text="set up time with Rahul next week",
        question_text="When do external meetings work best?",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    fake_lyzr.responses["policy"] = {"proposed_policy_text": "External meetings are scheduled after 2pm."}

    policy_id = await policy_gate.learn(db, row, "afternoons after 2pm", True, "trace-4")

    assert policy_id is not None
    stored = fake_qdrant.collections["preferences"][policy_id]
    assert stored.payload["provenance"] == "explicit"
    assert stored.payload["confidence"] == 1.0
    assert stored.payload["scope"] == "calendar"
    assert row.answer_text == "afternoons after 2pm"
    assert row.resulting_policy_id == policy_id


async def test_learn_without_save_flag_records_answer_but_no_policy(db, fake_qdrant, fake_embed, fake_lyzr):
    row = Clarification(instruction_text="archive this", question_text="are you sure?")
    db.add(row)
    db.commit()
    db.refresh(row)

    policy_id = await policy_gate.learn(db, row, "yes", False, "trace-5")

    assert policy_id is None
    assert row.answer_text == "yes"
    assert "preferences" not in fake_qdrant.collections or not fake_qdrant.collections["preferences"]
    assert fake_lyzr.calls == []
