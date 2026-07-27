import json
import re

FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class AgentParseError(Exception):
    pass


def strip_fences(text: str) -> str:
    return FENCE_RE.sub("", text.strip()).strip()


def parse_json_strict(text: str) -> dict:
    try:
        return json.loads(strip_fences(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise AgentParseError(f"agent reply was not valid json: {e}") from e
