import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.adapters import gmail
from app.adapters.mappers import map_message
from app.agents import comms, lyzr_client, policy_gate, scheduler, triage
from app.config import (
    DEFAULT_DELEGATE_DUE_DAYS,
    DEFAULT_DELEGATE_EMAIL,
    DEFAULT_MEETING_DURATION_MIN,
    KNOWN_CONTACTS,
)
from app.ledger.service import execute_action
from app.schemas import ActionDescriptor, Authorization


def _resolve_contact(name_or_email: str | None) -> str | None:
    if not name_or_email:
        return None
    if "@" in name_or_email:
        return name_or_email
    return KNOWN_CONTACTS.get(name_or_email.strip().lower(), name_or_email)


def _descriptor_from_suggested_action(action: str, message: dict) -> ActionDescriptor | None:
    if action == "archive":
        return ActionDescriptor(
            tool="gmail", operation="archive", params={"message_id": message["id"]}, agent_name="triage"
        )
    if action == "convert_to_task":
        return ActionDescriptor(
            tool="tasks",
            operation="task.create",
            params={"title": message["subject"], "notes": message["snippet"]},
            agent_name="triage",
        )
    # reply_today / delegate / none all need a drafted email first -- that's the comms
    # agent's job, not something triage can execute directly
    return None


async def _run_triage_subtask(db: Session, sub_input: dict, authorization: Authorization, trace_id: str) -> dict | None:
    message_id = sub_input.get("message_id")
    if not message_id:
        return None
    raw = await run_in_threadpool(gmail.get_message, message_id)
    message = map_message(raw)

    verdict = await triage.get_triage_verdict(message)
    descriptor = _descriptor_from_suggested_action(verdict["suggested_action"], message)
    if descriptor is None:
        return None

    result = await execute_action(db, descriptor, authorization, idempotency_key=uuid.uuid4(), trace_id=trace_id)
    return {
        "action_id": result.get("action_id"),
        "tool": descriptor.tool,
        "operation": descriptor.operation,
        "status": result.get("status"),
    }


async def _run_comms_subtask(db: Session, sub_input: dict, trace_id: str) -> dict | None:
    message_id = sub_input.get("message_id")
    if not message_id:
        return None
    raw = await run_in_threadpool(gmail.get_message, message_id)
    message = map_message(raw)
    thread = {
        "from": message["from"],
        "subject": message["subject"],
        "snippet": message["snippet"],
        "thread_id": message["thread_id"],
    }

    if sub_input.get("goal") == "delegate":
        recipient = _resolve_contact(sub_input.get("recipient")) or DEFAULT_DELEGATE_EMAIL
        task_title = sub_input.get("task_title") or f"Follow up: {message['subject']}"
        return await comms.draft_delegation(
            db, thread, recipient, task_title, sub_input.get("task_due"), sub_input.get("instructions"), trace_id
        )

    return await comms.draft_reply(db, thread, sub_input.get("instructions"), trace_id)


async def _run_hover_comms(db: Session, context: dict, trace_id: str) -> dict:
    """the HoverLens Reply/Delegate buttons -- deterministic, no LLM decomposition
    needed since the frontend already knows exactly which message and which goal."""
    raw = await run_in_threadpool(gmail.get_message, context["message_id"])
    message = map_message(raw)
    thread = {
        "from": message["from"],
        "subject": message["subject"],
        "snippet": message["snippet"],
        "thread_id": message["thread_id"],
    }
    instructions = context.get("instructions") or None

    if context.get("goal") == "delegate":
        recipient = _resolve_contact(context.get("recipient")) or DEFAULT_DELEGATE_EMAIL
        task_title = context.get("task_title") or f"Follow up: {message['subject']}"
        due = (datetime.now(timezone.utc) + timedelta(days=DEFAULT_DELEGATE_DUE_DAYS)).date().isoformat()
        result = await comms.draft_delegation(db, thread, recipient, task_title, due, instructions, trace_id)
    else:
        result = await comms.draft_reply(db, thread, instructions, trace_id)

    return {"type": "approval_pending", "approval_id": result["approval_id"], "preview": None}


async def handle_command(db: Session, text: str, context: dict | None, trace_id: str) -> dict:
    if context and context.get("type") == "conflict":
        reply = await scheduler.resolve_conflict(context.get("event_ids", []), trace_id)
        return {
            "type": "options",
            "conflict_summary": reply.get("conflict_summary"),
            "options": reply.get("options", []),
        }

    if context and context.get("type") == "comms":
        return await _run_hover_comms(db, context, trace_id)

    gate = await policy_gate.evaluate(db, text, trace_id)
    if gate.verdict == "CLARIFY":
        return {
            "type": "clarification",
            "clarification_id": gate.clarification_id,
            "question": gate.clarifying_question,
        }

    authorization = (
        Authorization(type="policy", ref=gate.matched_policy_id)
        if gate.matched_policy_id
        else Authorization(type="instruction", ref=text)
    )

    decomposition = await lyzr_client.invoke("manager", {"instruction": text, "context": context}, trace_id)
    subtasks = decomposition.get("subtasks", [])

    actions = []
    for subtask in subtasks:
        agent = subtask.get("agent")
        sub_input = subtask.get("input", {})

        if agent == "triage":
            result = await _run_triage_subtask(db, sub_input, authorization, trace_id)
            if result:
                actions.append(result)

        elif agent == "comms":
            result = await _run_comms_subtask(db, sub_input, trace_id)
            if result:
                return {"type": "approval_pending", "approval_id": result["approval_id"], "preview": None}

        elif agent == "scheduler":
            event_ids = sub_input.get("event_ids", [])
            attendee = _resolve_contact(sub_input.get("attendee"))
            if event_ids:
                reply = await scheduler.resolve_conflict(event_ids, trace_id)
                return {
                    "type": "options",
                    "conflict_summary": reply.get("conflict_summary"),
                    "options": reply.get("options", []),
                }
            if attendee:
                duration = sub_input.get("duration_minutes") or DEFAULT_MEETING_DURATION_MIN
                title = sub_input.get("title") or f"Meeting with {attendee.split('@')[0].title()}"
                reply = await scheduler.propose_new_meeting(attendee, duration, title, trace_id)
                return {
                    "type": "options",
                    "conflict_summary": reply.get("conflict_summary"),
                    "options": reply.get("options", []),
                }
        # a "policy" subtask needs nothing further -- the gate above already covered it

    return {"type": "executed", "summary": decomposition.get("intent", text), "actions": actions}
