import time

from app import state
from app.agents import lyzr_client
from app.governance.traces import new_trace_id
from app.memory import qdrant_client as qdrant


async def get_triage_verdict(message: dict) -> dict:
    cached = state.get_triage_cached(message["id"])
    if cached is not None:
        return {**cached, "cached": True, "latency_ms": 0}

    start = time.monotonic()

    query_text = f"{message.get('subject', '')} {message.get('snippet', '')}"
    context_hits = await qdrant.search_context_hybrid(query_text)
    pref_hits = await qdrant.search_preferences(query_text, k=3)
    policy_candidates = [{"id": p["id"], "text": p["text"]} for p in pref_hits if p["score"] >= 0.5]

    payload = {
        "message": {
            "id": message["id"],
            "from": message.get("from"),
            "subject": message.get("subject"),
            "snippet": message.get("snippet"),
            "date": message.get("date"),
        },
        "context_hits": [
            {
                "subject": h.get("subject"),
                "snippet": h.get("snippet"),
                "from": h.get("from"),
                "source": h.get("source"),
            }
            for h in context_hits
        ],
        "policy_candidates": policy_candidates,
    }

    reply = await lyzr_client.invoke("triage", payload, new_trace_id())

    cited_text = None
    cited_id = reply.get("cited_policy_id")
    if cited_id:
        cited_text = next((p["text"] for p in policy_candidates if p["id"] == cited_id), None)

    verdict = {
        "priority": reply.get("priority"),
        "suggested_action": reply.get("suggested_action"),
        "reasoning": reply.get("reasoning"),
        "cited_policy_id": cited_id,
        "cited_policy_text": cited_text,
    }
    state.set_triage_cached(message["id"], verdict)

    latency_ms = int((time.monotonic() - start) * 1000)
    return {**verdict, "cached": False, "latency_ms": latency_ms}
