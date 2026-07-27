import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import lyzr_client
from app.config import CLARIFICATION_MATCH_THRESHOLD, POLICY_CANDIDATE_K, POLICY_MATCH_THRESHOLD
from app.ledger.models import Clarification
from app.memory import embeddings, qdrant_client as qdrant


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def infer_scope(instruction: str) -> str:
    lowered = instruction.lower()
    if any(w in lowered for w in ("meeting", "schedule", "calendar", "event", "call", "time with")):
        return "calendar"
    if any(w in lowered for w in ("email", "inbox", "reply", "archive", "newsletter", "mail")):
        return "email"
    if any(w in lowered for w in ("task", "todo", "to-do")):
        return "tasks"
    return "global"


@dataclass
class GateResult:
    verdict: str  # ACT | CLARIFY
    matched_policy_id: str | None = None
    matched_policy_text: str | None = None
    score: float | None = None
    clarification_id: str | None = None
    clarifying_question: str | None = None


async def _find_answered_match(db: Session, instruction: str) -> Clarification | None:
    rows = db.execute(
        select(Clarification).where(Clarification.answer_text.is_not(None))
    ).scalars().all()
    if not rows:
        return None

    texts = [r.instruction_text for r in rows] + [instruction]
    vectors = await embeddings.embed(texts)
    instruction_vec = vectors[-1]

    best_row, best_score = None, 0.0
    for row, vec in zip(rows, vectors[:-1]):
        score = _cosine(vec, instruction_vec)
        if score > best_score:
            best_row, best_score = row, score

    if best_row is not None and best_score >= CLARIFICATION_MATCH_THRESHOLD:
        return best_row
    return None


async def evaluate(db: Session, instruction: str, trace_id: str) -> GateResult:
    candidates = await qdrant.search_preferences(instruction, k=POLICY_CANDIDATE_K)
    best = max(candidates, key=lambda c: c["score"]) if candidates else None

    if best is not None and best["score"] >= POLICY_MATCH_THRESHOLD:
        check = await lyzr_client.invoke(
            "policy",
            {"mode": "applies_check", "policy_text": best["text"], "situation": instruction},
            trace_id,
        )
        if check.get("applies"):
            await qdrant.increment_times_applied(best["id"])
            return GateResult(
                verdict="ACT", matched_policy_id=best["id"], matched_policy_text=best["text"], score=best["score"]
            )

    answered = await _find_answered_match(db, instruction)
    if answered is not None:
        return GateResult(
            verdict="ACT",
            matched_policy_id=answered.resulting_policy_id,
            matched_policy_text=answered.answer_text,
            score=None,
        )

    clarify = await lyzr_client.invoke(
        "policy",
        {"mode": "clarify", "instruction": instruction, "gap": "no matching stored preference"},
        trace_id,
    )
    question = clarify["clarifying_question"]

    row = Clarification(instruction_text=instruction, question_text=question)
    db.add(row)
    db.commit()
    db.refresh(row)

    return GateResult(verdict="CLARIFY", clarification_id=str(row.id), clarifying_question=question)


async def learn(db: Session, clarification: Clarification, answer: str, save_as_policy: bool, trace_id: str) -> str | None:
    clarification.answer_text = answer

    if not save_as_policy:
        db.add(clarification)
        db.commit()
        return None

    proposed = await lyzr_client.invoke(
        "policy",
        {
            "mode": "propose_policy",
            "instruction": clarification.instruction_text,
            "question": clarification.question_text,
            "answer": answer,
        },
        trace_id,
    )
    policy_text = proposed["proposed_policy_text"]

    new_id = str(uuid.uuid4())
    await qdrant.upsert_preference(
        new_id,
        policy_text,
        {
            "scope": infer_scope(clarification.instruction_text),
            "confidence": 1.0,
            "provenance": "explicit",
            "times_applied": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    clarification.resulting_policy_id = new_id
    db.add(clarification)
    db.commit()
    return new_id
