"""将练习记录、独立提取和跨日回测分开。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

QUALIFYING_BASES = {"first-independent", "spaced-independent"}


def _study_date(attempt: dict[str, Any]) -> str | None:
    try:
        if attempt.get("study_date"):
            return date.fromisoformat(attempt["study_date"]).isoformat()
        return datetime.fromisoformat(attempt["recorded_at"]).astimezone().date().isoformat()
    except (KeyError, ValueError, TypeError):
        return None


def classify_attempt(
    history: list[dict[str, Any]], queue_item: dict[str, Any] | None, current: date, mode: str,
) -> str:
    if mode == "assisted":
        return "assisted-practice"
    if not history:
        return "first-independent"
    day = current.isoformat()
    if any(_study_date(attempt) == day for attempt in history):
        return "same-day-repeat"
    next_due = (queue_item or {}).get("next_due")
    if next_due and next_due > day:
        return "early-repeat"
    # A prior assisted-only attempt can familiarize the learner with the particular item.
    # The first later independent retrieval from that item is treated as spaced.
    known_days = [_study_date(attempt) for attempt in history]
    if not any(stamp and stamp < day for stamp in known_days):
        return "unconfirmed-spacing"
    return "spaced-independent"


def topic_evidence(questions: list[dict[str, Any]], topic_id: str) -> dict[str, Any]:
    observations = 0
    legacy = 0
    successes = 0
    spaced = 0
    practice = 0
    successful_questions = set()
    latest_results = {}
    for question in questions:
        if question.get("topic_id") != topic_id:
            continue
        for attempt in question.get("attempts", []):
            basis = attempt.get("evidence_basis")
            if basis not in QUALIFYING_BASES:
                legacy += basis is None
                practice += basis is not None
                continue
            observations += 1
            latest_results[question["id"]] = attempt["result"]
            if attempt["result"] == "correct":
                successes += 1
                successful_questions.add(question["id"])
                spaced += basis == "spaced-independent"
    open_errors = sum(result != "correct" for result in latest_results.values())
    ready = successes >= 3 and len(successful_questions) >= 2 and spaced >= 1 and not open_errors
    return {
        "qualified_attempts": observations,
        "independent_successes": successes,
        "distinct_correct_questions": len(successful_questions),
        "spaced_successes": spaced,
        "open_question_errors": open_errors,
        "practice_only_attempts": practice,
        "legacy_unclassified_attempts": legacy,
        "status": "stable" if ready else "needs_more_evidence",
    }
