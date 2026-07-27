from datetime import datetime, timezone

from app.config import INTERNAL_DOMAINS


def header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def map_message(msg: dict) -> dict:
    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "from": header(headers, "From"),
        "subject": header(headers, "Subject"),
        "snippet": msg.get("snippet", ""),
        "date": header(headers, "Date"),
        "unread": "UNREAD" in msg.get("labelIds", []),
    }


def is_external_attendee(attendee: dict) -> bool:
    if attendee.get("self"):
        return False
    domain = attendee.get("email", "").split("@")[-1].lower()
    return domain not in INTERNAL_DOMAINS


def map_event(ev: dict) -> dict:
    attendees = ev.get("attendees", [])
    return {
        "id": ev["id"],
        "title": ev.get("summary", "(no title)"),
        "start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
        "end": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date"),
        "attendees": [a.get("email") for a in attendees],
        "external": any(is_external_attendee(a) for a in attendees),
        "conflict_group": None,
    }


def map_task(t: dict) -> dict:
    due = t.get("due")
    overdue = False
    if due and t.get("status") != "completed":
        try:
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
            overdue = due_dt < datetime.now(timezone.utc)
        except ValueError:
            pass
    return {
        "id": t["id"],
        "title": t.get("title", ""),
        "notes": t.get("notes"),
        "due": due,
        "status": t.get("status", "needsAction"),
        "overdue": overdue,
    }
