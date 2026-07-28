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


def _enrich_instruction(text: str, context: dict) -> str:
    """the policy gate embeds the raw instruction to match preferences, so "archive this"
    on its own matches nothing -- fold the pointed-at entity into the text so the gate
    sees what the user can see. also feeds infer_scope, which is keyword-based."""
    label = (context.get("label") or "").strip()
    if not label:
        return text
    kind = context.get("kind")
    noun = {"message": "email", "event": "calendar event", "task": "task"}.get(kind, "item")
    return f'{text} (the {noun}: "{label}")'


def _explicit_op(text: str, context: dict) -> ActionDescriptor | None:
    """when someone points at a row and gives a direct order, do that -- don't hand it to
    triage and let the agent's own verdict overrule them ("archive this" on a client
    escalation triages as reply_today, and the archive would just quietly never happen).
    anything less clear-cut than these falls through to the normal decomposition."""
    lowered = text.lower()
    kind, entity_id = context.get("kind"), context.get("id")
    if not entity_id:
        return None

    def has(*words: str) -> bool:
        return any(w in lowered for w in words)

    if kind == "message":
        if has("archive", "file it", "file this"):
            return ActionDescriptor(
                tool="gmail", operation="archive", params={"message_id": entity_id}, agent_name="pointer"
            )
        if has("to task", "into a task", "make a task", "add a task", "turn this into a task"):
            label = context.get("label") or "Follow up"
            return ActionDescriptor(
                tool="tasks", operation="task.create", params={"title": label, "notes": ""}, agent_name="pointer"
            )

    if kind == "task":
        if has("complete", "done", "finished", "tick", "check off"):
            return ActionDescriptor(
                tool="tasks", operation="task.complete", params={"task_id": entity_id}, agent_name="pointer"
            )
        if has("delete", "remove", "drop"):
            return ActionDescriptor(
                tool="tasks", operation="task.delete", params={"task_id": entity_id}, agent_name="pointer"
            )

    if kind == "event" and has("delete", "cancel", "drop", "call it off"):
        return ActionDescriptor(
            tool="calendar", operation="event.delete", params={"event_id": entity_id}, agent_name="pointer"
        )

    return None


def _inject_entity(sub_input: dict, context: dict) -> dict:
    """the manager agent can't know the id of whatever the pointer was on -- it only ever
    sees the label. fill it in here rather than trusting the model to echo one back,
    same reasoning as _resolve_contact below."""
    kind, entity_id = context.get("kind"), context.get("id")
    if not entity_id:
        return sub_input

    if kind == "message" and not sub_input.get("message_id"):
        sub_input["message_id"] = entity_id
    elif kind == "event" and not sub_input.get("event_ids"):
        # a conflicted event carries its whole group, so resolve_conflict gets both sides
        # rather than one event with nothing to weigh it against
        sub_input["event_ids"] = context.get("event_ids") or [entity_id]
    return sub_input


def _is_conflict_ask(text: str, context: dict) -> bool:
    """pointing at a clashing event and saying "sort this out" is the same request the
    Resolve conflict button makes, so send it down the same path -- that one skips the
    policy gate on purpose, because the scheduler cites its own episodes and prefs."""
    if context.get("kind") != "event" or len(context.get("event_ids") or []) < 2:
        return False
    lowered = text.lower()
    return any(
        w in lowered for w in ("clash", "conflict", "overlap", "double", "resolve", "fix", "sort out", "sort this")
    )


async def handle_command(db: Session, text: str, context: dict | None, trace_id: str) -> dict:
    if context and context.get("type") == "entity" and _is_conflict_ask(text, context):
        context = {"type": "conflict", "event_ids": context["event_ids"]}

    if context and context.get("type") == "conflict":
        reply = await scheduler.resolve_conflict(context.get("event_ids", []), trace_id)
        return {
            "type": "options",
            "conflict_summary": reply.get("conflict_summary"),
            "options": reply.get("options", []),
        }

    if context and context.get("type") == "comms":
        return await _run_hover_comms(db, context, trace_id)

    entity = context if context and context.get("type") == "entity" else None
    instruction = _enrich_instruction(text, entity) if entity else text

    gate = await policy_gate.evaluate(db, instruction, trace_id)
    if gate.verdict == "CLARIFY":
        return {
            "type": "clarification",
            "clarification_id": gate.clarification_id,
            "question": gate.clarifying_question,
        }

    authorization = (
        Authorization(type="policy", ref=gate.matched_policy_id)
        if gate.matched_policy_id
        else Authorization(type="instruction", ref=instruction)
    )

    if entity:
        direct = _explicit_op(text, entity)
        if direct is not None:
            result = await execute_action(
                db, direct, authorization, idempotency_key=uuid.uuid4(), trace_id=trace_id
            )
            if result.get("status") == "needs_approval":
                return {
                    "type": "approval_pending",
                    "approval_id": result.get("approval_id"),
                    "preview": None,
                }
            return {
                "type": "executed",
                "summary": f"{direct.operation.replace('.', ' ')}: {entity.get('label') or 'done'}",
                "actions": [
                    {
                        "action_id": result.get("action_id"),
                        "tool": direct.tool,
                        "operation": direct.operation,
                        "status": result.get("status"),
                    }
                ],
            }

    decomposition = await lyzr_client.invoke("manager", {"instruction": instruction, "context": context}, trace_id)
    subtasks = decomposition.get("subtasks", [])

    actions = []
    for subtask in subtasks:
        agent = subtask.get("agent")
        sub_input = subtask.get("input", {})
        if entity:
            sub_input = _inject_entity(sub_input, entity)

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
