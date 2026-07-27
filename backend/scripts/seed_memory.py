"""seeds qdrant memory: preferences, episodes, and the hybrid context collection.
run after scripts/seed.py so the context embeddings pick up real message/task ids."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.adapters import gmail, gtasks  # noqa: E402
from app.adapters.mappers import map_message  # noqa: E402
from app.memory import qdrant_client as qdrant  # noqa: E402
from app.memory.collections import context_id, episode_id, pref_id  # noqa: E402

PREFERENCES = [
    dict(
        text="Newsletters and promotional emails are archived automatically.",
        scope="email", confidence=1.0, provenance="explicit",
    ),
    dict(text="Meetings default to 30 minutes.", scope="calendar", confidence=1.0, provenance="explicit"),
    dict(
        text="Mornings before 11am are protected for deep work; avoid scheduling over them.",
        scope="calendar", confidence=1.0, provenance="explicit",
    ),
    dict(text="Emails from priya@ are high priority.", scope="email", confidence=1.0, provenance="explicit"),
    dict(
        text="Weekly status emails get converted into tasks.",
        scope="tasks", confidence=0.6, provenance="learned",
    ),
]

EPISODES = [
    dict(
        situation="Tuesday internal sync overlapped the morning deep-work block",
        decision="moved the internal sync to the afternoon",
        outcome="no complaints; deep work preserved", tool="calendar",
    ),
    dict(
        situation="the weekly internal sync landed on top of a protected morning again",
        decision="moved it to the afternoon, same as before",
        outcome="deep work stayed intact", tool="calendar",
    ),
    dict(
        situation="a recurring internal sync kept colliding with the morning focus block",
        decision="shifted the sync later in the day",
        outcome="no pushback, pattern repeated smoothly", tool="calendar",
    ),
    dict(
        situation="client requested a report while the week was full",
        decision="delegated to Arjun with a tracking task and a Friday deadline",
        outcome="delivered on time", tool="gmail",
    ),
    dict(
        situation="newsletter backlog built up over a travel week",
        decision="batch-archived all newsletters",
        outcome="inbox back to zero in one pass", tool="gmail",
    ),
    dict(
        situation="meeting request landed on a protected morning",
        decision="offered afternoon slots instead",
        outcome="meeting booked at 3pm, morning intact", tool="calendar",
    ),
]


async def seed_preferences() -> int:
    for i, p in enumerate(PREFERENCES, start=1):
        await qdrant.upsert_preference(
            pref_id(i),
            p["text"],
            {
                "scope": p["scope"],
                "confidence": p["confidence"],
                "provenance": p["provenance"],
                "times_applied": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return len(PREFERENCES)


async def seed_episodes() -> int:
    for i, e in enumerate(EPISODES, start=1):
        text = f"{e['situation']} -- {e['decision']} -- {e['outcome']}"
        await qdrant.upsert_episode(
            episode_id(i),
            text,
            {
                "situation": e["situation"],
                "decision": e["decision"],
                "outcome": e["outcome"],
                "tool": e["tool"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return len(EPISODES)


async def seed_context() -> int:
    raw_messages = gmail.list_inbox(20)
    raw_tasks = gtasks.list_tasks()

    count = 0
    for raw in raw_messages:
        m = map_message(raw)
        text = f"{m['subject']} {m['snippet']}"
        await qdrant.upsert_context(
            context_id("email", m["id"]),
            text,
            {
                "source": "email", "source_id": m["id"], "subject": m["subject"],
                "snippet": m["snippet"], "from": m["from"], "date": m["date"],
            },
        )
        count += 1

    for t in raw_tasks:
        text = f"{t.get('title', '')} {t.get('notes', '')}"
        await qdrant.upsert_context(
            context_id("task", t["id"]),
            text,
            {
                "source": "task", "source_id": t["id"], "subject": t.get("title", ""),
                "snippet": t.get("notes", "") or "", "from": None, "date": t.get("due"),
            },
        )
        count += 1

    return count


async def run_seed_memory() -> dict:
    return {
        "preferences": await seed_preferences(),
        "episodes": await seed_episodes(),
        "context": await seed_context(),
    }


if __name__ == "__main__":
    result = asyncio.run(run_seed_memory())
    print(f"seeded {result['preferences']} preferences, {result['episodes']} episodes, {result['context']} context points")
