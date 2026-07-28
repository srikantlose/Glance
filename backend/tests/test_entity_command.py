import pytest

from app.agents import manager
from app.ledger.models import Action
from app.memory import qdrant_client as qdrant

MESSAGE = {"kind": "message", "id": "msg-1", "label": "digest@saastimes.com - SaaS Times Daily Digest #412"}
EVENT = {"kind": "event", "id": "ev-1", "label": "Vendor Sync (internal)"}
TASK = {"kind": "task", "id": "task-1", "label": "Update the ops runbook"}


def _entity(base: dict, **extra) -> dict:
    return {"type": "entity", **base, **extra}


def test_enrichment_names_the_pointed_at_thing():
    enriched = manager._enrich_instruction("archive this", MESSAGE)

    # the gate embeds this string to match preferences, so the newsletter has to be in it
    assert "archive this" in enriched
    assert "SaaS Times Daily Digest #412" in enriched
    assert "email" in enriched


def test_enrichment_uses_the_right_noun_per_kind():
    assert "calendar event" in manager._enrich_instruction("move this", EVENT)
    assert "task" in manager._enrich_instruction("push this out", TASK)


def test_enrichment_is_a_noop_without_a_label():
    assert manager._enrich_instruction("archive this", {"kind": "message", "id": "msg-1"}) == "archive this"


def test_inject_fills_the_id_the_model_could_not_know():
    assert manager._inject_entity({"message_id": None}, MESSAGE)["message_id"] == "msg-1"


def test_inject_leaves_an_explicit_id_alone():
    sub_input = manager._inject_entity({"message_id": "msg-other"}, MESSAGE)

    assert sub_input["message_id"] == "msg-other"


def test_inject_prefers_the_whole_conflict_group():
    sub_input = manager._inject_entity({"event_ids": []}, {**EVENT, "event_ids": ["ev-1", "ev-2"]})

    assert sub_input["event_ids"] == ["ev-1", "ev-2"]


def test_inject_falls_back_to_the_single_event():
    assert manager._inject_entity({"event_ids": []}, EVENT)["event_ids"] == ["ev-1"]


@pytest.mark.parametrize(
    "text,entity,tool,operation",
    [
        ("archive this", MESSAGE, "gmail", "archive"),
        ("turn this into a task", MESSAGE, "tasks", "task.create"),
        ("mark this done", TASK, "tasks", "task.complete"),
        ("delete this", TASK, "tasks", "task.delete"),
        ("cancel this", EVENT, "calendar", "event.delete"),
    ],
)
def test_direct_orders_resolve_without_the_model(text, entity, tool, operation):
    descriptor = manager._explicit_op(text, entity)

    assert descriptor is not None
    assert (descriptor.tool, descriptor.operation) == (tool, operation)


def test_clash_ask_on_a_conflicted_event_takes_the_resolve_path():
    conflicted = {**EVENT, "event_ids": ["ev-1", "ev-2"]}

    assert manager._is_conflict_ask("sort out this clash", conflicted)
    assert manager._is_conflict_ask("fix this", conflicted)
    # a lone event has nothing to resolve against
    assert not manager._is_conflict_ask("sort out this clash", EVENT)
    # and an unrelated ask on a conflicted event still goes through the gate
    assert not manager._is_conflict_ask("who else is coming to this?", conflicted)


async def test_conflict_ask_skips_the_gate_entirely(db, fake_qdrant, fake_embed, fake_lyzr, monkeypatch):
    seen = {}

    async def fake_resolve(event_ids, trace_id):
        seen["event_ids"] = event_ids
        return {"conflict_summary": "Deep Work vs Vendor Sync", "options": []}

    monkeypatch.setattr(manager.scheduler, "resolve_conflict", fake_resolve)

    result = await manager.handle_command(
        db, "sort out this clash", _entity(EVENT, event_ids=["ev-1", "ev-2"]), "trace-3"
    )

    assert result["type"] == "options"
    assert seen["event_ids"] == ["ev-1", "ev-2"]
    # the gate never ran, so it never asked the policy agent anything
    assert fake_lyzr.calls == []


def test_open_ended_asks_fall_through_to_decomposition():
    assert manager._explicit_op("what should I do about this?", MESSAGE) is None
    assert manager._explicit_op("find a better slot for this", EVENT) is None


async def test_explicit_archive_executes_and_cites_the_policy(db, fake_qdrant, fake_embed, fake_lyzr, monkeypatch):
    text = "archive this"
    await qdrant.upsert_preference(
        "pref-1",
        manager._enrich_instruction(text, MESSAGE),
        {"scope": "email", "confidence": 1.0, "provenance": "explicit", "times_applied": 0},
    )
    fake_lyzr.responses["policy"] = {"applies": True}

    from app.adapters import gmail

    monkeypatch.setattr(gmail, "archive", lambda message_id: {"id": message_id})

    result = await manager.handle_command(db, text, _entity(MESSAGE), "trace-1")

    assert result["type"] == "executed"
    assert result["actions"][0]["operation"] == "archive"

    row = db.query(Action).one()
    assert row.params_json["message_id"] == "msg-1"
    assert row.authorization_type == "policy"
    assert row.authorization_ref == "pref-1"
    # a direct order never needed the manager agent at all
    assert [c[0] for c in fake_lyzr.calls] == ["policy"]


async def test_unknown_preference_still_clarifies_at_the_pointer(db, fake_qdrant, fake_embed, fake_lyzr):
    fake_lyzr.responses["policy"] = {"clarifying_question": "When do external meetings work best?"}

    result = await manager.handle_command(
        db, "set up time with him", _entity({"kind": "message", "id": "msg-9", "label": "rahul@northwind.co"}), "t"
    )

    assert result["type"] == "clarification"
    assert result["question"] == "When do external meetings work best?"


async def test_open_ended_event_ask_routes_to_the_scheduler(db, fake_qdrant, fake_embed, fake_lyzr, monkeypatch):
    fake_lyzr.responses["policy"] = {"clarifying_question": "unused"}
    await qdrant.upsert_preference(
        "pref-cal",
        manager._enrich_instruction("sort out this clash", EVENT),
        {"scope": "calendar", "confidence": 1.0, "provenance": "explicit", "times_applied": 0},
    )
    fake_lyzr.responses["policy"] = {"applies": True}
    fake_lyzr.responses["manager"] = {
        "intent": "resolve_conflict",
        "subtasks": [{"agent": "scheduler", "input": {"event_ids": []}}],
        "requires_gate": True,
    }

    seen = {}

    async def fake_resolve(event_ids, trace_id):
        seen["event_ids"] = event_ids
        return {"conflict_summary": "Deep Work vs Vendor Sync", "options": []}

    monkeypatch.setattr(manager.scheduler, "resolve_conflict", fake_resolve)

    result = await manager.handle_command(
        db, "sort out this clash", _entity(EVENT, event_ids=["ev-1", "ev-2"]), "trace-2"
    )

    assert result["type"] == "options"
    assert seen["event_ids"] == ["ev-1", "ev-2"]
