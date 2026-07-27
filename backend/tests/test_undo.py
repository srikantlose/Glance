import uuid

import pytest

from app.ledger import service
from app.ledger.models import Action
from app.ledger.undo import IrreversibleActionError, undo_action
from app.schemas import ActionDescriptor, Authorization


_DEFAULT_EVENT = {
    "id": "evt-unused",
    "start": {"dateTime": "2026-07-21T04:00:00+00:00"},
    "end": {"dateTime": "2026-07-21T05:00:00+00:00"},
}


async def _execute(db, monkeypatch, tool, operation, params, fake_fn, original_event=None, auth_type="instruction"):
    monkeypatch.setitem(service.DISPATCH, (tool, operation), fake_fn)

    # execute_action always fetches the current event body before an event.move/delete
    # (its own inverse needs it), whether that's the action under test or a later undo
    # of it -- so calendar tests need this mocked regardless of which op they're checking.
    from app.adapters import gcal

    monkeypatch.setattr(gcal, "get_event", lambda event_id: original_event or _DEFAULT_EVENT)

    descriptor = ActionDescriptor(tool=tool, operation=operation, params=params, agent_name="test")
    authorization = Authorization(type=auth_type, ref="test")
    result = await service.execute_action(db, descriptor, authorization, uuid.uuid4())
    return db.get(Action, result["action_id"])


async def test_archive_undo_readds_inbox(db, monkeypatch):
    def fake_archive(params):
        return {"id": params["message_id"], "labelIds": []}

    action = await _execute(db, monkeypatch, "gmail", "archive", {"message_id": "m1"}, fake_archive)
    assert action.inverse_operation == "unarchive"
    assert action.inverse_params_json == {"message_id": "m1"}

    calls = []

    def fake_unarchive(params):
        calls.append(params)
        return {"id": params["message_id"], "labelIds": ["INBOX"]}

    monkeypatch.setitem(service.DISPATCH, ("gmail", "unarchive"), fake_unarchive)

    result = await undo_action(db, action)
    assert result["status"] == "executed"
    assert calls == [{"message_id": "m1"}]
    assert action.status == "undone"
    assert action.undone_by == "user"


async def test_event_create_undo_deletes_by_created_id(db, monkeypatch):
    def fake_create(params):
        return {"id": "evt-123"}

    action = await _execute(db, monkeypatch, "calendar", "event.create", {"body": {"summary": "x"}}, fake_create)
    assert action.inverse_operation == "event.delete"
    assert action.inverse_params_json == {"event_id": "evt-123"}

    deleted = []

    def fake_delete(params):
        deleted.append(params["event_id"])
        return {"event_id": params["event_id"]}

    monkeypatch.setitem(service.DISPATCH, ("calendar", "event.delete"), fake_delete)

    result = await undo_action(db, action)
    assert deleted == ["evt-123"]
    assert result["status"] == "executed"


async def test_event_move_undo_restores_original_times(db, monkeypatch):
    original_event = {
        "id": "evt-1",
        "start": {"dateTime": "2026-07-21T04:00:00+00:00"},
        "end": {"dateTime": "2026-07-21T05:30:00+00:00"},
    }

    def fake_move(params):
        return {"id": params["event_id"], "start": {"dateTime": params["new_start"]}}

    action = await _execute(
        db, monkeypatch, "calendar", "event.move",
        {"event_id": "evt-1", "new_start": "2026-07-21T09:00:00+00:00", "new_end": "2026-07-21T10:30:00+00:00"},
        fake_move, original_event=original_event,
    )
    assert action.inverse_operation == "event.move"
    assert action.inverse_params_json == {
        "event_id": "evt-1",
        "new_start": "2026-07-21T04:00:00+00:00",
        "new_end": "2026-07-21T05:30:00+00:00",
    }

    moved_back = []

    def fake_move_back(params):
        moved_back.append(params)
        return {"id": params["event_id"]}

    monkeypatch.setitem(service.DISPATCH, ("calendar", "event.move"), fake_move_back)

    await undo_action(db, action)
    assert moved_back == [{
        "event_id": "evt-1",
        "new_start": "2026-07-21T04:00:00+00:00",
        "new_end": "2026-07-21T05:30:00+00:00",
    }]


async def test_task_complete_undo_sets_needs_action(db, monkeypatch):
    def fake_complete(params):
        return {"id": params["task_id"], "status": "completed"}

    action = await _execute(db, monkeypatch, "tasks", "task.complete", {"task_id": "t1"}, fake_complete)
    assert action.inverse_operation == "task.uncomplete"

    calls = []

    def fake_uncomplete(params):
        calls.append(params)
        return {"id": params["task_id"], "status": "needsAction"}

    monkeypatch.setitem(service.DISPATCH, ("tasks", "task.uncomplete"), fake_uncomplete)

    await undo_action(db, action)
    assert calls == [{"task_id": "t1"}]


async def test_send_is_irreversible(db, monkeypatch):
    def fake_send(params):
        return {"id": "msg-sent"}

    action = await _execute(
        db, monkeypatch, "gmail", "send",
        {"to": "a@b.com", "subject": "hi", "body": "hello"}, fake_send,
        auth_type="approval",
    )
    assert action.irreversible is True

    with pytest.raises(IrreversibleActionError):
        await undo_action(db, action)
