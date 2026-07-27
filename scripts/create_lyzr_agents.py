"""provisions the 5 Lyzr agents (manager/triage/scheduler/comms/policy) via the
platform's REST API.

Plain prompt text alone isn't enough -- live testing showed 3 of 5 agents ignoring
the "respond with ONLY a JSON object matching X" instruction and returning a
different shape entirely. Wrapping the schema in an OpenAI-style response_format
(type: json_schema) fixed it; a bare schema object in response_format was silently
ignored. See DECISIONS.md.

Run with no args to create fresh agents and print .env lines.
Run with --update to push the current prompts/schemas onto the IDs already in .env
(no new agents, no env changes needed).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx  # noqa: E402

from app.agents import prompts  # noqa: E402
from app.config import settings  # noqa: E402

SUBTASK_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "message_id": {"type": ["string", "null"]},
        "event_ids": {"type": "array", "items": {"type": "string"}},
        "attendee": {"type": ["string", "null"]},
        "duration_minutes": {"type": ["number", "null"]},
        "title": {"type": ["string", "null"]},
        "goal": {"type": ["string", "null"], "enum": ["reply", "delegate", None]},
        "recipient": {"type": ["string", "null"]},
        "task_title": {"type": ["string", "null"]},
        "task_due": {"type": ["string", "null"]},
        "instructions": {"type": ["string", "null"]},
    },
    # every field required (nullable where not applicable) -- a bare "type": "object" input let the
    # model hand back {} for every subtask; strict mode enforces required keys but not minProperties.
    "required": [
        "message_id", "event_ids", "attendee", "duration_minutes", "title",
        "goal", "recipient", "task_title", "task_due", "instructions",
    ],
}

MANAGER_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "enum": ["triage", "scheduler", "comms"]},
                    "input": SUBTASK_INPUT_SCHEMA,
                },
                "required": ["agent", "input"],
            },
        },
        "requires_gate": {"type": "boolean"},
    },
    "required": ["intent", "subtasks", "requires_gate"],
}

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "priority": {"type": "string", "enum": ["high", "normal", "low"]},
        "suggested_action": {
            "type": "string",
            "enum": ["archive", "reply_today", "delegate", "convert_to_task", "none"],
        },
        "reasoning": {"type": "string"},
        "cited_policy_id": {"type": ["string", "null"]},
    },
    "required": ["priority", "suggested_action", "reasoning", "cited_policy_id"],
}

SCHEDULER_SCHEMA = {
    "type": "object",
    "properties": {
        "conflict_summary": {"type": "string"},
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "number"},
                    "action": {
                        "type": "string",
                        "enum": ["event.move", "event.delete", "event.create", "none"],
                    },
                    "event_changes": {
                        "type": ["object", "null"],
                        "properties": {
                            "event_id": {"type": ["string", "null"]},
                            "new_start": {"type": "string"},
                            "new_end": {"type": "string"},
                            "title": {"type": ["string", "null"]},
                            "attendees": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["event_id", "new_start", "new_end", "title", "attendees"],
                    },
                    "justification": {"type": "string"},
                    "cited_episode_or_policy": {"type": ["string", "null"]},
                },
                "required": ["rank", "action", "event_changes", "justification", "cited_episode_or_policy"],
            },
        },
    },
    "required": ["conflict_summary", "options"],
}

COMMS_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "tone_notes": {"type": "string"},
    },
    "required": ["subject", "body", "tone_notes"],
}

POLICY_SCHEMA = {
    "anyOf": [
        {"type": "object", "properties": {"applies": {"type": "boolean"}}, "required": ["applies"]},
        {
            "type": "object",
            "properties": {"clarifying_question": {"type": "string"}},
            "required": ["clarifying_question"],
        },
        {
            "type": "object",
            "properties": {"proposed_policy_text": {"type": "string"}},
            "required": ["proposed_policy_text"],
        },
    ]
}


def _response_format(name: str, schema: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}}


AGENTS = [
    {
        "key": "manager",
        "name": "glance-manager",
        "description": "Chief of Staff -- decomposes user instructions into subtasks for the specialist agents.",
        "system_prompt": prompts.MANAGER_PROMPT,
        "model": settings.GEMINI_PRO_MODEL,
        "temperature": 0.3,
        "response_format": _response_format("manager_output", MANAGER_SCHEMA),
    },
    {
        "key": "triage",
        "name": "glance-triage",
        "description": "Email triage -- priority, suggested action, and policy citation for inbox messages.",
        "system_prompt": prompts.TRIAGE_PROMPT,
        "model": settings.GEMINI_FLASH_MODEL,
        "temperature": 0.3,
        "response_format": _response_format("triage_output", TRIAGE_SCHEMA),
    },
    {
        "key": "scheduler",
        "name": "glance-scheduler",
        "description": "Calendar conflict resolution -- ranks event-move options against episodes and preferences.",
        "system_prompt": prompts.SCHEDULER_PROMPT,
        "model": settings.GEMINI_PRO_MODEL,
        "temperature": 0.3,
        "response_format": _response_format("scheduler_output", SCHEDULER_SCHEMA),
    },
    {
        "key": "comms",
        "name": "glance-comms",
        "description": "Drafts reply and delegation emails on the user's behalf.",
        "system_prompt": prompts.COMMS_PROMPT,
        "model": settings.GEMINI_PRO_MODEL,
        "temperature": 0.6,
        "response_format": _response_format("comms_output", COMMS_SCHEMA),
    },
    {
        "key": "policy",
        "name": "glance-policy",
        "description": "Policy gate LLM steps -- applies-check, clarifying questions, policy-text proposals.",
        "system_prompt": prompts.POLICY_GATE_PROMPT,
        "model": settings.GEMINI_FLASH_MODEL,
        "temperature": 0.3,
        "response_format": _response_format("policy_output", POLICY_SCHEMA),
    },
]


def _body(spec: dict) -> dict:
    return {
        "name": spec["name"],
        "description": spec["description"],
        "system_prompt": spec["system_prompt"],
        "provider_id": "google",
        "model": spec["model"],
        "temperature": spec["temperature"],
        "top_p": 0.9,
        "response_format": spec["response_format"],
    }


def create() -> None:
    headers = {"x-api-key": settings.LYZR_API_KEY}
    ids: dict[str, str] = {}

    with httpx.Client(base_url=settings.LYZR_BASE_URL, timeout=30) as client:
        for spec in AGENTS:
            resp = client.post("/v3/agents/", json=_body(spec), headers=headers)
            resp.raise_for_status()
            agent_id = resp.json()["agent_id"]
            ids[spec["key"]] = agent_id
            print(f"{spec['key']}: {agent_id}")

    print("\npaste into backend/.env:")
    print(f"LYZR_MANAGER_AGENT_ID={ids['manager']}")
    sub_agents = {k: v for k, v in ids.items() if k != "manager"}
    print(f"LYZR_AGENT_IDS_JSON={sub_agents}".replace("'", '"'))


def update() -> None:
    existing = {"manager": settings.LYZR_MANAGER_AGENT_ID, **settings.lyzr_agent_ids}
    headers = {"x-api-key": settings.LYZR_API_KEY}

    with httpx.Client(base_url=settings.LYZR_BASE_URL, timeout=30) as client:
        for spec in AGENTS:
            agent_id = existing.get(spec["key"])
            if not agent_id:
                print(f"{spec['key']}: no id in .env, skipping")
                continue
            resp = client.put(f"/v3/agents/{agent_id}", json=_body(spec), headers=headers)
            resp.raise_for_status()
            print(f"{spec['key']}: updated ({agent_id})")


if __name__ == "__main__":
    if "--update" in sys.argv:
        update()
    else:
        create()
