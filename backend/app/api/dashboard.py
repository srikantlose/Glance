import asyncio

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app import state
from app.adapters import gcal, gmail, gtasks
from app.adapters.mappers import map_event, map_message, map_task
from app.agents.triage import get_triage_verdict
from app.config import PREWARM_CONCURRENCY

router = APIRouter()


def _compute_conflicts(events: list[dict]) -> list[dict]:
    timed = [e for e in events if e["start"] and "T" in e["start"]]
    n = len(timed)
    adjacency = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = timed[i], timed[j]
            if a["start"] < b["end"] and b["start"] < a["end"]:
                adjacency[i].add(j)
                adjacency[j].add(i)

    seen: set[int] = set()
    conflicts = []
    group_num = 0
    for i in range(n):
        if i in seen or not adjacency[i]:
            continue
        stack = [i]
        group: set[int] = set()
        while stack:
            cur = stack.pop()
            if cur in group:
                continue
            group.add(cur)
            stack.extend(adjacency[cur] - group)
        seen |= group
        group_num += 1
        group_id = f"conflict-{group_num}"
        for k in group:
            timed[k]["conflict_group"] = group_id
        conflicts.append(
            {"group_id": group_id, "event_ids": [timed[k]["id"] for k in group], "summary": f"{len(group)} overlapping events"}
        )
    return conflicts


async def _prewarm_triage(inbox: list[dict]) -> None:
    sem = asyncio.Semaphore(PREWARM_CONCURRENCY)

    async def one(msg: dict) -> None:
        async with sem:
            try:
                await get_triage_verdict(msg)
            except Exception:
                pass  # pre-warm is best-effort -- a slow/broken agent shouldn't block the dashboard

    await asyncio.gather(*(one(m) for m in inbox))


@router.get("/api/dashboard")
async def get_dashboard():
    cached = state.get_dashboard_cached()
    if cached is not None:
        return cached

    raw_messages = await run_in_threadpool(gmail.list_inbox, 20)
    raw_events = await run_in_threadpool(gcal.list_events, 7)
    raw_tasks = await run_in_threadpool(gtasks.list_tasks)

    inbox = [map_message(m) for m in raw_messages]
    events = [map_event(e) for e in raw_events]
    tasks = [map_task(t) for t in raw_tasks]
    conflicts = _compute_conflicts(events)

    snapshot = {"inbox": inbox, "events": events, "tasks": tasks, "conflicts": conflicts}
    state.set_dashboard_cached(snapshot)

    asyncio.create_task(_prewarm_triage(inbox))

    return snapshot
