import re
import uuid
from pathlib import Path

from app.governance import pii_guard
from app.ledger import service
from app.ledger.models import Approval
from app.schemas import ActionDescriptor, Authorization


async def test_gmail_send_without_approval_routes_to_approvals_not_adapter(db, monkeypatch):
    async def fake_model_scan(text):
        return []

    monkeypatch.setattr(pii_guard, "model_scan", fake_model_scan)

    def fail_if_called(params):
        raise AssertionError("adapter should not run before approval")

    monkeypatch.setitem(service.DISPATCH, ("gmail", "send"), fail_if_called)

    descriptor = ActionDescriptor(
        tool="gmail", operation="send",
        params={"to": "a@b.com", "subject": "hi", "body": "hello"}, agent_name="comms",
    )
    authorization = Authorization(type="instruction", ref="reply to this")

    result = await service.execute_action(db, descriptor, authorization, uuid.uuid4())

    assert result["status"] == "needs_approval"
    approval = db.get(Approval, result["approval_id"])
    assert approval is not None
    assert approval.status == "pending"


BYPASS_PATTERNS = [
    re.compile(r"\bgmail\.send\("),
    re.compile(r"\bgcal\.delete_event\("),
    re.compile(r"\bdelete_event\("),
]

ALLOWED_FILES = {"app/ledger/service.py", "app/workers/outbox_worker.py"}
ADAPTER_FILES = {"gmail.py", "gcal.py", "gtasks.py"}


def test_no_direct_adapter_calls_outside_the_ledger_choke_point():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    violations = []

    for path in app_dir.rglob("*.py"):
        rel = path.relative_to(app_dir.parent).as_posix()
        if rel in ALLOWED_FILES or path.name in ADAPTER_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in BYPASS_PATTERNS:
            if pattern.search(text):
                violations.append(f"{rel}: {pattern.pattern}")

    assert not violations, f"found adapter calls bypassing the ledger gate: {violations}"
