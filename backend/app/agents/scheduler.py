from datetime import datetime, timedelta, timezone

from starlette.concurrency import run_in_threadpool

from app.adapters import gcal
from app.agents import lyzr_client
from app.config import EPISODE_TOP_K
from app.memory import qdrant_client as qdrant

NEW_MEETING_SEARCH_DAYS = 7
IST = timezone(timedelta(hours=5, minutes=30))
BUSINESS_START_IST = 9
BUSINESS_END_IST = 18
SLOT_STEP_MINUTES = 30
MAX_CANDIDATE_SLOTS = 10


def _event_brief(ev: dict) -> dict:
    return {
        "id": ev["id"],
        "title": ev.get("summary", "(no title)"),
        "start": ev.get("start", {}).get("dateTime"),
        "end": ev.get("end", {}).get("dateTime"),
        "attendees": [a.get("email") for a in ev.get("attendees", [])],
    }


def _attach_descriptor(option: dict) -> None:
    changes = option.get("event_changes")
    action = option.get("action")
    if action == "event.move" and changes:
        option["descriptor"] = {
            "tool": "calendar",
            "operation": "event.move",
            "params": {
                "event_id": changes["event_id"],
                "new_start": changes["new_start"],
                "new_end": changes["new_end"],
            },
            "agent_name": "scheduler",
        }
    elif action == "event.delete" and changes:
        option["descriptor"] = {
            "tool": "calendar",
            "operation": "event.delete",
            "params": {"event_id": changes["event_id"]},
            "agent_name": "scheduler",
        }
    elif action == "event.create" and changes:
        option["descriptor"] = {
            "tool": "calendar",
            "operation": "event.create",
            "params": {
                "body": {
                    "summary": changes.get("title") or "Meeting",
                    "start": {"dateTime": changes["new_start"]},
                    "end": {"dateTime": changes["new_end"]},
                    "attendees": [{"email": a} for a in changes.get("attendees") or []],
                }
            },
            "agent_name": "scheduler",
        }
    else:
        option["descriptor"] = None


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _candidate_slots(busy: list[dict], duration_minutes: int, days: int = NEW_MEETING_SEARCH_DAYS) -> list[dict]:
    """business-hours-in-IST slots, converted to UTC in code -- the scheduler agent kept getting the
    IST/UTC arithmetic wrong when asked to do it itself (tried three prompt variants), so it only
    picks from and justifies a pre-computed list now instead of inventing a time."""
    now_utc = datetime.now(timezone.utc)
    busy_windows = [
        (datetime.fromisoformat(b["start"].replace("Z", "+00:00")), datetime.fromisoformat(b["end"].replace("Z", "+00:00")))
        for b in busy
    ]

    candidates = []
    start_date = now_utc.astimezone(IST).date()
    for day_offset in range(days + 1):
        day = start_date + timedelta(days=day_offset)
        slot_start_ist = datetime(day.year, day.month, day.day, BUSINESS_START_IST, 0, tzinfo=IST)
        day_end_ist = datetime(day.year, day.month, day.day, BUSINESS_END_IST, 0, tzinfo=IST)
        while slot_start_ist + timedelta(minutes=duration_minutes) <= day_end_ist:
            slot_end_ist = slot_start_ist + timedelta(minutes=duration_minutes)
            slot_start_utc = slot_start_ist.astimezone(timezone.utc)
            slot_end_utc = slot_end_ist.astimezone(timezone.utc)
            free = slot_start_utc > now_utc and not any(
                _overlaps(slot_start_utc, slot_end_utc, b0, b1) for b0, b1 in busy_windows
            )
            if free:
                candidates.append({
                    "start_utc": slot_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end_utc": slot_end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "label_ist": slot_start_ist.strftime("%a %d %b, %H:%M IST"),
                })
                if len(candidates) >= MAX_CANDIDATE_SLOTS:
                    return candidates
            slot_start_ist += timedelta(minutes=SLOT_STEP_MINUTES)
    return candidates


async def resolve_conflict(event_ids: list[str], trace_id: str) -> dict:
    events = [await run_in_threadpool(gcal.get_event, eid) for eid in event_ids]
    briefs = [_event_brief(e) for e in events]

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=NEW_MEETING_SEARCH_DAYS)
    freebusy_raw = await run_in_threadpool(gcal.freebusy, now.isoformat(), window_end.isoformat())
    busy = freebusy_raw.get("calendars", {}).get(gcal.CALENDAR_ID, {}).get("busy", [])

    candidate_slots_by_event = {}
    for b in briefs:
        if b["start"] and b["end"]:
            start_dt = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
            duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
            candidate_slots_by_event[b["id"]] = _candidate_slots(busy, duration_minutes)

    summary_text = " vs ".join(b["title"] for b in briefs)
    episode_hits = await qdrant.search_episodes(summary_text, k=EPISODE_TOP_K)
    pref_hits = await qdrant.search_preferences(summary_text, k=5)
    preferences = [{"id": p["id"], "text": p["text"]} for p in pref_hits if p["score"] >= 0.5]
    episodes = [
        {"situation": e.get("situation"), "decision": e.get("decision"), "outcome": e.get("outcome")}
        for e in episode_hits
    ]

    payload = {
        "mode": "resolve_conflict",
        "conflict": {"summary": summary_text, "events": briefs},
        "candidate_slots_by_event": candidate_slots_by_event,
        "episodes": episodes,
        "preferences": preferences,
    }

    reply = await lyzr_client.invoke("scheduler", payload, trace_id)
    for option in reply.get("options", []):
        _attach_descriptor(option)
    return reply


async def propose_new_meeting(attendee_email: str, duration_minutes: int, title: str, trace_id: str) -> dict:
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=NEW_MEETING_SEARCH_DAYS)
    freebusy_raw = await run_in_threadpool(gcal.freebusy, now.isoformat(), window_end.isoformat())
    busy = freebusy_raw.get("calendars", {}).get(gcal.CALENDAR_ID, {}).get("busy", [])
    candidates = _candidate_slots(busy, duration_minutes)

    situation = f"scheduling a meeting with {attendee_email}"
    episode_hits = await qdrant.search_episodes(situation, k=EPISODE_TOP_K)
    pref_hits = await qdrant.search_preferences(situation, k=5)
    preferences = [{"id": p["id"], "text": p["text"]} for p in pref_hits if p["score"] >= 0.5]
    episodes = [
        {"situation": e.get("situation"), "decision": e.get("decision"), "outcome": e.get("outcome")}
        for e in episode_hits
    ]

    payload = {
        "mode": "propose_new_meeting",
        "new_meeting": {"attendee": attendee_email, "duration_minutes": duration_minutes, "title": title},
        "candidate_slots": candidates,
        "episodes": episodes,
        "preferences": preferences,
    }

    reply = await lyzr_client.invoke("scheduler", payload, trace_id)
    for option in reply.get("options", []):
        _attach_descriptor(option)
    return reply
