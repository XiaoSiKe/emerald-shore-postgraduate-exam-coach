"""冲刺阶段、优先级、复习队列和每日任务。"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .errors import QinganError

KINDS = {"memory", "understanding", "calculation", "writing", "language", "timed"}
KIND_LABELS = {
    "memory": "记忆",
    "understanding": "理解",
    "calculation": "计算",
    "writing": "写作",
    "language": "语言",
    "timed": "限时输出",
}
PHASES = (
    (91, "foundation", "基础重建与知识地图"),
    (46, "strengthening", "专题突破与混合练习"),
    (15, "past-paper", "真题限时与错因修补"),
    (1, "final", "错题回忆与节奏稳定"),
)
REVIEW_INTERVALS = (1, 3, 7, 14, 30)


def determine_phase(exam_date: str, today: date | None = None) -> dict[str, Any]:
    current = today or date.today()
    target = date.fromisoformat(exam_date)
    days = (target - current).days
    if days < 1:
        raise QinganError(
            "exam_date_not_future",
            "考试日期已经到达或过去。",
            "更新 profile.json 中的考试日期后重新规划。",
        )
    for minimum, code, label in PHASES:
        if days >= minimum:
            return {"code": code, "label": label, "days_remaining": days}
    raise AssertionError("unreachable")


def stable_id(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def due_reviews(queue: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    current = today or date.today()
    result = []
    for item in queue:
        try:
            due = date.fromisoformat(item["next_due"])
        except (KeyError, TypeError, ValueError):
            continue
        if due <= current:
            result.append(item)
    return sorted(result, key=lambda item: (item.get("next_due", ""), -item.get("error_count", 0)))


def _mistake_counts(mistakes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in mistakes:
        subject_id = row.get("subject_id")
        if subject_id:
            counts[subject_id] = counts.get(subject_id, 0) + 1
    return counts


def rank_subjects(
    subjects: list[dict[str, Any]], mistakes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not subjects:
        raise QinganError(
            "no_subjects",
            "还没有科目，无法生成冲刺计划。",
            "先使用 subject add 添加至少一门科目。",
        )
    total_score = sum(float(item["max_score"]) for item in subjects)
    counts = _mistake_counts(mistakes)
    has_all_costs = all(item.get("estimated_hours") for item in subjects)
    ranked = []
    for subject in subjects:
        maximum = float(subject["max_score"])
        current = float(subject.get("current_score", subject["baseline"]))
        target = float(subject["target"])
        gap_ratio = max(0.0, target - current) / maximum
        exam_weight = maximum / total_score if total_score else 0.0
        error_bonus = 1.0 + min(counts.get(subject["id"], 0), 5) * 0.08
        prerequisite = 1.15 if subject["kind"] in {"calculation", "language", "understanding"} else 1.0
        confidence = 1.0 if subject.get("score_history") else 0.8
        estimated_hours = subject.get("estimated_hours")
        if has_all_costs and estimated_hours:
            time_cost = max(1.0, math.sqrt(float(estimated_hours)))
            basis = "quantitative"
        else:
            time_cost = 1.0
            basis = "partial-no-time-cost"
        priority = gap_ratio * exam_weight * error_bonus * prerequisite * confidence / time_cost
        ranked.append(
            {
                **subject,
                "priority": round(priority, 6),
                "priority_basis": basis,
                "gap_points": round(max(0.0, target - current), 2),
                "mistake_count": counts.get(subject["id"], 0),
            }
        )
    return sorted(ranked, key=lambda item: (-item["priority"], -item["gap_points"], item["name"]))


def _minutes_split(capacity: int, task_count: int, has_reviews: bool) -> list[int]:
    if task_count == 1:
        return [capacity]
    if has_reviews:
        if task_count == 2:
            first = min(max(1, round(capacity * 0.25)), capacity - 1)
            return [first, capacity - first]
        first = min(max(1, round(capacity * 0.20)), capacity - 2)
        second = max(1, round((capacity - first) * 0.70))
        return [first, second, capacity - first - second]
    if task_count == 2:
        first = round(capacity * 0.75)
        return [first, capacity - first]
    first = round(capacity * 0.70)
    second = round(capacity * 0.15)
    return [first, second, capacity - first - second]


def build_plan(
    profile: dict[str, Any],
    subjects: list[dict[str, Any]],
    mistakes: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    reason: str,
    today: date | None = None,
) -> dict[str, Any]:
    current = today or date.today()
    phase = determine_phase(profile["exam_date"], current)
    ranked = rank_subjects(subjects, mistakes)
    capacity = max(1, int(float(profile["daily_hours"]) * 60 * (1 - float(profile.get("buffer_ratio", 0.15)))))
    due = due_reviews(review_queue, current)
    specs = []
    if due:
        names = []
        subject_by_id = {item["id"]: item["name"] for item in subjects}
        for item in due[:6]:
            names.append(subject_by_id.get(item.get("subject_id"), item.get("label", "待复习项")))
        specs.append(("review", None, f"闭卷提取到期内容：{'、'.join(dict.fromkeys(names))}"))
    main = ranked[0]
    specs.append(
        (
            "main",
            main["id"],
            f"主攻 {main['name']}：围绕 {KIND_LABELS[main['kind']]}薄弱点完成一次可判定训练",
        )
    )
    for subject in ranked[1:]:
        if len(specs) >= 3:
            break
        specs.append(
            (
                "maintenance",
                subject["id"],
                f"维持 {subject['name']}：完成短时闭卷回忆或限时练习",
            )
        )
    specs = specs[: max(1, min(len(specs), capacity))]
    minutes = _minutes_split(capacity, len(specs), bool(due))
    tasks = []
    for index, ((role, subject_id, title), planned) in enumerate(zip(specs, minutes), 1):
        task = {
                "id": stable_id(current.isoformat(), role, subject_id or "all"),
                "order": index,
                "role": role,
                "subject_id": subject_id,
                "title": title,
                "planned_minutes": planned,
                "verification": "闭卷作答、限时题或可核验产出；仅阅读不算完成",
                "status": "pending",
            }
        if role == "review":
            task["review_keys"] = [item["key"] for item in due[:6] if item.get("key")]
        tasks.append(task)
    warnings = []
    if any(item["priority_basis"] != "quantitative" for item in ranked):
        warnings.append("部分科目缺少预计达标成本，优先级为保守估计；用 checkpoint 和 estimated-hours 校准。")
    if phase["days_remaining"] > 120:
        warnings.append("距离考试超过典型冲刺窗口，当前按基础重建阶段运行。")
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "plan_date": current.isoformat(),
        "reason": reason,
        "phase": phase,
        "daily_capacity_minutes": capacity,
        "buffer_ratio": profile.get("buffer_ratio", 0.15),
        "main_subject_id": main["id"],
        "main_subject_name": main["name"],
        "maintenance_subject_ids": [item["id"] for item in ranked[1:3]],
        "ranked_subjects": [
            {
                "id": item["id"],
                "name": item["name"],
                "priority": item["priority"],
                "priority_basis": item["priority_basis"],
                "gap_points": item["gap_points"],
                "mistake_count": item["mistake_count"],
            }
            for item in ranked
        ],
        "tasks": tasks,
        "warnings": warnings,
    }


def update_review_item(
    queue: list[dict[str, Any]],
    task: dict[str, Any],
    result: str,
    current: date | None = None,
) -> list[dict[str, Any]]:
    today = current or date.today()
    key = task.get("review_key") or (
        f"subject:{task['subject_id']}" if task.get("subject_id") else task["id"]
    )
    existing = next((item for item in queue if item.get("key") == key), None)
    if result == "skipped":
        return queue
    if existing is None:
        existing = {
            "key": key,
            "subject_id": task.get("subject_id"),
            "label": task.get("title", "复习项"),
            "success_streak": 0,
            "error_count": 0,
            "status": "introduced",
        }
        queue.append(existing)
    if result == "complete":
        existing["success_streak"] = int(existing.get("success_streak", 0)) + 1
        index = min(existing["success_streak"] - 1, len(REVIEW_INTERVALS) - 1)
        interval = REVIEW_INTERVALS[index]
        existing["status"] = "practicing" if existing["success_streak"] < 3 else "mastered"
    else:
        existing["success_streak"] = 0
        existing["error_count"] = int(existing.get("error_count", 0)) + 1
        existing["status"] = "review-needed"
        interval = 1
    existing["last_result"] = result
    existing["last_reviewed"] = today.isoformat()
    existing["next_due"] = (today + timedelta(days=interval)).isoformat()
    return queue
