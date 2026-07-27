import json

import httpx

from app.agents.parsing import parse_json_strict
from app.config import settings, LYZR_CHAT_PATH, LYZR_USER_ID


def _agent_id(agent: str) -> str:
    if agent == "manager":
        return settings.LYZR_MANAGER_AGENT_ID
    return settings.lyzr_agent_ids[agent]


async def invoke(agent: str, payload: dict, session_id: str) -> dict:
    """single choke point for every lyzr call -- if their api shape turns out to differ
    from what's assumed here (see DECISIONS.md), this is the only place that needs to change."""
    agent_id = _agent_id(agent)
    headers = {"x-api-key": settings.LYZR_API_KEY}
    body = {
        "user_id": LYZR_USER_ID,
        "agent_id": agent_id,
        "session_id": session_id,
        "message": json.dumps(payload),
    }

    async with httpx.AsyncClient(base_url=settings.LYZR_BASE_URL, timeout=30) as client:
        resp = await client.post(LYZR_CHAT_PATH, json=body, headers=headers)
        resp.raise_for_status()
        raw_reply = resp.json()["response"]

        try:
            return parse_json_strict(raw_reply)
        except Exception:
            retry_body = {
                **body,
                "message": body["message"] + "\n\nYour previous reply was not valid JSON. Return only the JSON object.",
            }
            resp2 = await client.post(LYZR_CHAT_PATH, json=retry_body, headers=headers)
            resp2.raise_for_status()
            raw_reply_2 = resp2.json()["response"]
            return parse_json_strict(raw_reply_2)
