import re
from dataclasses import dataclass

PHONE_RE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b|\+?\d[\d\-\s]{8,13}\d")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
AADHAAR_RE = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")

REDACTION_TOKENS = {
    "phone": "[redacted-phone]",
    "email": "[redacted-email]",
    "id": "[redacted-id]",
    "card": "[redacted-card]",
}


@dataclass
class Finding:
    type: str  # phone | email | id | card
    text: str
    start: int
    end: int
    flagged_by: str  # regex | model | lyzr


def _luhn_ok(digits: str) -> bool:
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def scan(text: str) -> list[Finding]:
    findings: list[Finding] = []

    for m in AADHAAR_RE.finditer(text):
        findings.append(Finding("id", m.group(), m.start(), m.end(), "regex"))

    for m in PAN_RE.finditer(text):
        findings.append(Finding("id", m.group(), m.start(), m.end(), "regex"))

    for m in CARD_RE.finditer(text):
        digits = re.sub(r"[ -]", "", m.group())
        if len(digits) >= 13 and _luhn_ok(digits):
            findings.append(Finding("card", m.group(), m.start(), m.end(), "regex"))

    for m in EMAIL_RE.finditer(text):
        findings.append(Finding("email", m.group(), m.start(), m.end(), "regex"))

    for m in PHONE_RE.finditer(text):
        # skip spans that are already inside a longer id/card match to avoid double flags
        if any(f.start <= m.start() and m.end() <= f.end for f in findings):
            continue
        findings.append(Finding("phone", m.group(), m.start(), m.end(), "regex"))

    findings.sort(key=lambda f: f.start)
    return findings


def redact(text: str, findings: list[Finding]) -> str:
    result = text
    for f in sorted(findings, key=lambda x: x.start, reverse=True):
        token = REDACTION_TOKENS.get(f.type, "[redacted]")
        result = result[: f.start] + token + result[f.end :]
    return result


async def model_scan(text: str) -> list[Finding]:
    """second layer on top of the regexes -- catches PII that doesn't match a fixed pattern
    (names next to sensitive context, spelled-out numbers, etc)."""
    from google import genai
    from google.genai import types

    from app.config import settings

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    resp = await client.aio.models.generate_content(
        model=settings.GEMINI_FLASH_MODEL,
        contents=(
            "Does this text contain PII (phone numbers, personal emails, government IDs, "
            "card numbers, home addresses)? Text:\n\n" + text
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "contains_pii": {"type": "boolean"},
                    "findings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["type", "text"],
                        },
                    },
                },
                "required": ["contains_pii", "findings"],
            },
        ),
    )
    import json

    data = json.loads(resp.text)
    results = []
    for item in data.get("findings", []):
        needle = item.get("text", "")
        idx = text.find(needle)
        if idx == -1:
            continue
        results.append(Finding(item.get("type", "id"), needle, idx, idx + len(needle), "model"))
    return results


async def full_scan(text: str) -> list[Finding]:
    regex_findings = scan(text)
    try:
        extra = await model_scan(text)
    except Exception:
        extra = []
    covered = [(f.start, f.end) for f in regex_findings]
    for f in extra:
        if not any(a <= f.start and f.end <= b for a, b in covered):
            regex_findings.append(f)
    regex_findings.sort(key=lambda f: f.start)
    return regex_findings
