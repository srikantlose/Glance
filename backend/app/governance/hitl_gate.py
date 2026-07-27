from sqlalchemy.orm import Session

from app.adapters import gcal
from app.config import INTERNAL_DOMAINS
from app.governance.pii_guard import REDACTION_TOKENS, Finding
from app.ledger.models import Approval
from app.schemas import ActionDescriptor


def requires_approval(descriptor: ActionDescriptor) -> bool:
    if descriptor.tool == "gmail" and descriptor.operation == "send":
        return True
    if descriptor.tool == "calendar" and descriptor.operation == "event.delete":
        return True
    if descriptor.tool == "calendar" and descriptor.operation == "event.move":
        event = gcal.get_event(descriptor.params["event_id"])
        return _has_external_attendee(event)
    return False


def _has_external_attendee(event: dict) -> bool:
    for attendee in event.get("attendees", []):
        if attendee.get("self"):
            continue
        domain = attendee.get("email", "").split("@")[-1].lower()
        if domain not in INTERNAL_DOMAINS:
            return True
    return False


def create_approval(
    db: Session,
    descriptors: list[ActionDescriptor],
    rendered: str,
    pii_findings: list[Finding],
) -> Approval:
    approval = Approval(
        action_preview_json={
            "actions": [d.model_dump() for d in descriptors],
            "rendered": rendered,
        },
        pii_findings_json=[
            {
                "type": f.type,
                "original": f.text,
                "redacted": REDACTION_TOKENS.get(f.type, "[redacted]"),
                "flagged_by": f.flagged_by,
            }
            for f in pii_findings
        ],
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval
