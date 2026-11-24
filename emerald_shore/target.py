"""院校自命题资料的适用范围。"""

from __future__ import annotations

from typing import Any


def course_scope(profile: dict[str, Any], subject: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not profile.get("target_school"):
        return None
    return {
        "school": profile["target_school"],
        "major": profile.get("target_major"),
        "admission_year": profile.get("admission_year"),
        "exam_code": subject.get("exam_code") if subject else None,
    }


def matches_scope(record: dict[str, Any], profile: dict[str, Any], subject: dict[str, Any] | None) -> bool:
    scope = record.get("target_scope")
    if scope is None:
        # 旧版定向资料缺少当时的目标信息，等待重新核对。
        return record.get("evidence_level") != "target_school_open"
    return scope == course_scope(profile, subject)


def planning_subjects(profile: dict[str, Any], subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for subject in subjects:
        if not subject.get("target_specific"):
            result.append(subject)
            continue
        scope = course_scope(profile, subject)
        history = [
            row for row in subject.get("score_history", [])
            if scope and row.get("target_scope") == scope
        ]
        full = [row for row in history if row.get("normalized_score") is not None]
        entered = subject["baseline"] if scope and subject.get("target_scope") == scope else None
        current = full[-1]["normalized_score"] if full else entered
        result.append({
            **subject, "score_history": history, "baseline": entered, "current_score": current,
            "baseline_status": "needs_current_scope_baseline" if current is None else "current_scope",
        })
    return result
