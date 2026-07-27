import uuid

import pytest

from app.adapters.errors import AdapterError, GoogleAuthError401
from app.adapters.retry import with_retry
from app.ledger import service
from app.schemas import ActionDescriptor, Authorization


def test_retry_gives_up_after_max_attempts():
    calls = {"n": 0}

    @with_retry
    def flaky():
        calls["n"] += 1
        raise AdapterError("boom", retryable=True)

    with pytest.raises(AdapterError):
        flaky()

    assert calls["n"] == 3


def test_failure_mode_raises_before_any_request(monkeypatch):
    from app import state
    from app.adapters import gmail

    monkeypatch.setitem(state.runtime_flags, "failure_mode", "gmail_401")

    def fake_service():
        raise AssertionError("should never reach the google client during the failure drill")

    monkeypatch.setattr(gmail, "gmail_service", fake_service)

    with pytest.raises(GoogleAuthError401):
        gmail.archive("msg-1")


async def test_idempotent_execute_runs_adapter_once(db, monkeypatch):
    calls = {"n": 0}

    def fake_archive(params):
        calls["n"] += 1
        return {"id": params["message_id"], "labelIds": []}

    monkeypatch.setitem(service.DISPATCH, ("gmail", "archive"), fake_archive)

    descriptor = ActionDescriptor(tool="gmail", operation="archive", params={"message_id": "msg-1"}, agent_name="triage")
    authorization = Authorization(type="policy", ref="pref-1")
    key = uuid.uuid4()

    first = await service.execute_action(db, descriptor, authorization, key)
    second = await service.execute_action(db, descriptor, authorization, key)

    assert calls["n"] == 1
    assert first["status"] == "executed"
    assert second["status"] == "executed"
    assert second["result"] == first["result"]
