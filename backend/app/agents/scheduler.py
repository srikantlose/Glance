from starlette.concurrency import run_in_threadpool

from app.adapters import gcal
from app.agents import lyzr_client
from app.config import EPISODE_TOP_K
from app.memory import qdrant_client as qdrant


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
    if option.get("action") == "event.move" and changes:
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
    elif option.get("action") == "event.delete" and changes:
        option["descriptor"] = {
            "tool": "calendar",
            "operation": "event.delete",
            "params": {"event_id": changes["event_id"]},
            "agent_name": "scheduler",
        }
    else:
        option["descriptor"] = None


async def resolve_conflict(event_ids: list[str], trace_id: str) -> dict:
    events = [await run_in_threadpool(gcal.get_event, eid) for eid in event_ids]
    briefs = [_event_brief(e) for e in events]

    starts = [b["start"] for b in briefs if b["start"]]
    ends = [b["end"] for b in briefs if b["end"]]
    freebusy = {}
    if starts and ends:
        freebusy = await run_in_threadpool(gcal.freebusy, min(starts), max(ends))

    summary_text = " vs ".join(b["title"] for b in briefs)
    episode_hits = await qdrant.search_episodes(summary_text, k=EPISODE_TOP_K)
    pref_hits = await qdrant.search_preferences(summary_text, k=5)
    preferences = [{"id": p["id"], "text": p["text"]} for p in pref_hits if p["score"] >= 0.5]
    episodes = [
        {"situation": e.get("situation"), "decision": e.get("decision"), "outcome": e.get("outcome")}
        for e in episode_hits
    ]

    payload = {
        "conflict": {"summary": summary_text, "events": briefs},
        "freebusy": freebusy,
        "episodes": episodes,
        "preferences": preferences,
    }

    reply = await lyzr_client.invoke("scheduler", payload, trace_id)
    for option in reply.get("options", []):
        _attach_descriptor(option)
    return reply
