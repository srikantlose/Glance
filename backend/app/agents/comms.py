from sqlalchemy.orm import Session

from app.agents import lyzr_client
from app.governance import hitl_gate, pii_guard
from app.memory import qdrant_client as qdrant
from app.schemas import ActionDescriptor


async def _draft(thread: dict, recipient: str, goal: str, instructions: str | None, trace_id: str) -> dict:
    query_text = f"{thread.get('subject', '')} {thread.get('snippet', '')}"
    related = await qdrant.search_context_hybrid(query_text)
    payload = {
        "goal": goal,
        "thread": {"from": thread.get("from"), "subject": thread.get("subject"), "snippet": thread.get("snippet")},
        "recipient": recipient,
        "instructions": instructions,
        "related_context": related,
    }
    return await lyzr_client.invoke("comms", payload, trace_id)


async def draft_reply(db: Session, thread: dict, instructions: str | None, trace_id: str) -> dict:
    recipient = thread.get("from")
    draft = await _draft(thread, recipient, "reply", instructions, trace_id)

    findings = await pii_guard.full_scan(draft["body"])
    redacted_body = pii_guard.redact(draft["body"], findings)

    descriptor = ActionDescriptor(
        tool="gmail",
        operation="send",
        params={"to": recipient, "subject": draft["subject"], "body": redacted_body, "thread_id": thread.get("thread_id")},
        agent_name="comms",
    )
    rendered = f"To: {recipient}\nSubject: {draft['subject']}\n\n{redacted_body}"
    approval = hitl_gate.create_approval(db, [descriptor], rendered, findings)
    return {"approval_id": str(approval.id)}


async def draft_delegation(
    db: Session,
    thread: dict,
    recipient: str,
    task_title: str,
    task_due: str | None,
    instructions: str | None,
    trace_id: str,
) -> dict:
    draft = await _draft(thread, recipient, "delegate", instructions, trace_id)

    findings = await pii_guard.full_scan(draft["body"])
    redacted_body = pii_guard.redact(draft["body"], findings)

    send_descriptor = ActionDescriptor(
        tool="gmail",
        operation="send",
        params={"to": recipient, "subject": draft["subject"], "body": redacted_body, "thread_id": thread.get("thread_id")},
        agent_name="comms",
    )
    task_descriptor = ActionDescriptor(
        tool="tasks",
        operation="task.create",
        params={"title": task_title, "notes": f"Delegated: {thread.get('subject', '')}", "due": task_due},
        agent_name="comms",
    )

    rendered = f"To: {recipient}\nSubject: {draft['subject']}\n\n{redacted_body}\n\n+ tracking task: {task_title}"
    approval = hitl_gate.create_approval(db, [send_descriptor, task_descriptor], rendered, findings)
    return {"approval_id": str(approval.id)}
