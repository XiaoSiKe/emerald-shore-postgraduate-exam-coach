"""冲刺阶段、优先级、复习调度与今日任务。"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .errors import EmeraldError
from .target import course_scope

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
        raise EmeraldError(
            "exam_date_not_future",
            "考试日期已经到达或过去。",
            "更新 profile.json 中的考试日期后重新规划。",
        )
    for minimum, code, label in PHASES:
        if days >= minimum:
            return {"code": code, "label": label, "days_remaining": days}
    raise AssertionError("无法到达的冲刺阶段分支")


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


def campus_day_context(profile: dict[str, Any], current: date) -> dict[str, Any]:
    """把大学生日常节律转换为当天容量，同时兼容旧工作区。"""
    routine = profile.get("routine") if isinstance(profile.get("routine"), dict) else {}
    is_weekend = current.weekday() >= 5
    hours_key = "weekend_hours" if is_weekend else "weekday_hours"
    raw_hours = routine.get(hours_key)
    basis = f"routine-{hours_key}"
    try:
        available_hours = float(raw_hours)
        if not 0 <= available_hours <= 24:
            raise ValueError
    except (TypeError, ValueError):
        available_hours = float(profile["daily_hours"])
        basis = "profile-daily-hours"
    return {
        "day_type": "weekend" if is_weekend else "weekday",
        "available_hours": round(available_hours, 2),
        "capacity_basis": basis,
        "sleep_floor_hours": routine.get("sleep_floor_hours"),
        "preferred_place": routine.get("preferred_place"),
        "fixed_commitments": list(routine.get("fixed_commitments") or []),
    }


def _mistake_counts(mistakes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in mistakes:
        subject_id = row.get("subject_id")
        if subject_id:
            counts[subject_id] = counts.get(subject_id, 0) + 1
    return counts


def _topic_mistake_counts(mistakes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in mistakes:
        topic_id = row.get("topic_id")
        if topic_id:
            counts[topic_id] = counts.get(topic_id, 0) + 1
    return counts


def rank_topics(
    topics: list[dict[str, Any]],
    mistakes: list[dict[str, Any]],
    subject_id: str | None = None,
) -> list[dict[str, Any]]:
    candidates = [item for item in topics if subject_id is None or item.get("subject_id") == subject_id]
    if not candidates:
        return []
    counts = _topic_mistake_counts(mistakes)
    has_all_costs = all(item.get("estimated_hours") for item in candidates)
    ranked = []
    for topic in candidates:
        mastery = min(1.0, max(0.0, float(topic.get("mastery", 0.0))))
        weight = max(0.0, float(topic.get("weight", 1.0)))
        confidence = min(1.0, max(0.1, float(topic.get("confidence", 0.5))))
        error_bonus = 1.0 + min(counts.get(topic["id"], 0), 5) * 0.10
        if has_all_costs:
            time_cost = max(1.0, math.sqrt(float(topic["estimated_hours"])))
            basis = "quantitative"
        else:
            time_cost = 1.0
            basis = "partial-no-time-cost"
        priority = weight * (1.0 - mastery) * confidence * error_bonus / time_cost
        ranked.append(
            {
                **topic,
                "priority": round(priority, 6),
                "priority_basis": basis,
                "mistake_count": counts.get(topic["id"], 0),
            }
        )
    return sorted(ranked, key=lambda item: (-item["priority"], item["name"]))


def _recent_full_scores(subject: dict[str, Any], current: date) -> list[float]:
    """Return at most three recent full checks with the latest named testing conditions."""
    recent = []
    for row in subject.get("score_history", []):
        if (
            row.get("scope") == "partial"
            or row.get("raw_max_score") != float(subject["max_score"])
            or not isinstance(row.get("normalized_score"), (int, float))
        ):
            continue
        try:
            day = datetime.fromisoformat(row["recorded_at"]).astimezone().date()
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= (current - day).days <= 28:
            recent.append(row)
    if not recent or recent[-1]["normalized_score"] != subject.get("current_score", subject["baseline"]):
        return []
    latest = recent[-1]
    if not latest.get("series"):
        return [float(latest["normalized_score"])]
    matched = [
        float(row["normalized_score"]) for row in recent
        if row.get("series") == latest["series"] and row.get("minutes") == latest.get("minutes")
    ]
    return matched[-3:]


def assess_exam_goals(
    goals: dict[str, Any], subjects: list[dict[str, Any]], current: date
) -> dict[str, Any]:
    floors = goals.get("subject_floors", {})
    subject_results = {}
    for subject in subjects:
        floor = floors.get(subject["id"])
        if floor is None:
            continue
        recorded = subject.get("current_score", subject["baseline"])
        if recorded is None:
            subject_results[subject["id"]] = {
                "name": subject["name"], "reference_floor": floor, "score": None,
                "status": "needs_current_scope_baseline", "basis": "no-current-scope-baseline",
                "comparable_scores": [], "observed_spread": None,
            }
            continue
        score = float(recorded)
        scores = _recent_full_scores(subject, current)
        spread = round(max(scores) - min(scores), 2) if len(scores) > 1 else None
        if score < floor:
            risk = "below_floor"
        elif score == floor or (spread is not None and score - floor <= spread):
            risk = "at_risk"
        else:
            risk = "above_floor" if scores else "unconfirmed_above_floor"
        subject_results[subject["id"]] = {
            "name": subject["name"],
            "reference_floor": floor,
            "score": score,
            "status": risk,
            "basis": "recent-full-checkpoint" if scores else "unconfirmed-baseline",
            "comparable_scores": scores,
            "observed_spread": spread,
        }
    target_total = goals.get("total_target")
    total = None
    if target_total is not None:
        scores = [subject.get("current_score", subject["baseline"]) for subject in subjects]
        observed = round(sum(scores), 2) if all(score is not None for score in scores) else None
        total = {
            "target": target_total,
            "reference_sum": observed,
            "gap_points": round(max(0.0, target_total - observed), 2) if observed is not None else None,
            "basis": "sum-of-latest-subject-scores" if observed is not None else "incomplete-current-baselines",
        }
    return {"basis": goals.get("basis"), "subjects": subject_results, "total": total}


def _floor_priority(subject: dict[str, Any], assessment: dict[str, Any]) -> tuple[int, float]:
    result = assessment.get(subject["id"], {})
    tier = {"below_floor": 2, "at_risk": 1}.get(result.get("status"), 0)
    score = result.get("score")
    deficit = max(0.0, result["reference_floor"] - score) if score is not None else 0.0
    return tier, deficit


def rank_subjects(
    subjects: list[dict[str, Any]], mistakes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not subjects:
        raise EmeraldError(
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
        entered = subject.get("current_score", subject["baseline"])
        current = float(entered) if entered is not None else 0.0
        target = float(subject["target"])
        gap_ratio = max(0.0, target - current) / maximum
        exam_weight = maximum / total_score if total_score else 0.0
        error_bonus = 1.0 + min(counts.get(subject["id"], 0), 5) * 0.08
        prerequisite = 1.15 if subject["kind"] in {"calculation", "language", "understanding"} else 1.0
        confidence = 1.0 if any(
            row.get("scope") != "partial" for row in subject.get("score_history", [])
        ) else 0.8
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
                "gap_points": round(max(0.0, target - current), 2) if entered is not None else None,
                "mistake_count": counts.get(subject["id"], 0),
            }
        )
    return sorted(ranked, key=lambda item: (-item["priority"], -(item["gap_points"] or 0), item["name"]))


def _minutes_split(capacity: int, task_count: int, has_reviews: bool) -> list[int]:
    if task_count == 0:
        return []
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
        first = min(round(capacity * 0.75), capacity - 1)
        return [first, capacity - first]
    first = min(round(capacity * 0.70), capacity - 2)
    second = min(max(1, round(capacity * 0.15)), capacity - first - 1)
    return [first, second, capacity - first - second]


def build_plan(
    profile: dict[str, Any],
    subjects: list[dict[str, Any]],
    mistakes: list[dict[str, Any]],
    review_queue: list[dict[str, Any]],
    reason: str,
    today: date | None = None,
    topics: list[dict[str, Any]] | None = None,
    available_minutes: int | None = None,
    main_only: bool = False,
) -> dict[str, Any]:
    current = today or date.today()
    phase = determine_phase(profile["exam_date"], current)
    ranked = rank_subjects(subjects, mistakes)
    goals = profile.get("exam_goals") or {}
    assessment = assess_exam_goals(goals, ranked, current)
    ranked.sort(key=lambda subject: _floor_priority(subject, assessment["subjects"]), reverse=True)
    day_context = campus_day_context(profile, current)
    day_context["main_only"] = main_only
    if available_minutes is not None:
        day_context.update(
            available_hours=round(available_minutes / 60, 2),
            capacity_basis="day-override",
            available_minutes_override=available_minutes,
        )
    else:
        available_minutes = round(day_context["available_hours"] * 60)
    capacity = (
        max(1, int(available_minutes * (1 - float(profile.get("buffer_ratio", 0.15)))))
        if available_minutes else 0
    )
    due = [] if main_only else due_reviews(review_queue, current)
    specs = []
    if due:
        names = []
        subject_by_id = {item["id"]: item["name"] for item in subjects}
        for item in due[:6]:
            names.append(subject_by_id.get(item.get("subject_id"), item.get("label", "待复习项")))
        specs.append(("review", None, f"闭卷提取到期内容：{'、'.join(dict.fromkeys(names))}"))
    main = ranked[0]
    main_assessment = assessment["subjects"].get(main["id"], {})
    main_basis = {
        "below_floor": "below-reference-floor",
        "at_risk": "near-reference-floor",
    }.get(main_assessment.get("status"), "subject-target-gap")
    if main.get("baseline_status") == "needs_current_scope_baseline":
        main_basis = "current-scope-diagnostic"
    assessment["main_basis"] = main_basis
    ranked_topics = rank_topics(topics or [], mistakes, main["id"])
    main_topic = ranked_topics[0] if ranked_topics else None
    topic_phrase = f"的「{main_topic['name']}」专题" if main_topic else ""
    title = f"主攻 {main['name']}{topic_phrase}：围绕 {KIND_LABELS[main['kind']]}薄弱点完成一次可判定训练"
    if main_basis == "current-scope-diagnostic":
        title = f"校准 {main['name']}{topic_phrase}：按当前范围做一次短测，记录用时与首个卡点"
    specs.append(("main", main["id"], title))
    for subject in ([] if main_only else ranked[1:]):
        if len(specs) >= 3:
            break
        specs.append(
            (
                "maintenance",
                subject["id"],
                f"维持 {subject['name']}：完成短时闭卷回忆或限时练习",
            )
        )
    specs = specs[:capacity]
    minutes = _minutes_split(capacity, len(specs), bool(due))
    tasks = []
    for index, ((role, subject_id, title), planned) in enumerate(zip(specs, minutes), 1):
        task = {
            "id": stable_id(current.isoformat(), role, subject_id or "all"),
            "order": index,
            "role": role,
            "subject_id": subject_id,
            "topic_id": main_topic["id"] if role == "main" and main_topic else None,
            "title": title,
            "planned_minutes": planned,
            "verification": "闭卷作答、限时题或可核验产出；仅阅读不算完成",
            "status": "pending",
        }
        if role == "review":
            task["review_keys"] = [item["key"] for item in due[:6] if item.get("key")]
        if subject_id:
            scoped_subject = next((row for row in subjects if row["id"] == subject_id and row.get("target_specific")), None)
            if scoped_subject:
                task["target_scope"] = course_scope(profile, scoped_subject)
                task["id"] = stable_id(task["id"], str(task["target_scope"]))
        tasks.append(task)
    warnings = []
    if any(item["priority_basis"] != "quantitative" for item in ranked):
        warnings.append("部分科目缺少预计达标成本，优先级为保守估计；用 checkpoint 和 estimated-hours 校准。")
    if phase["days_remaining"] > 120:
        warnings.append("距离考试超过典型冲刺窗口，当前按基础重建阶段运行。")
    sleep_floor = day_context.get("sleep_floor_hours")
    if sleep_floor is not None and float(sleep_floor) < 6:
        warnings.append("当前睡眠底线低于 6 小时；计划不会把继续熬夜或压缩睡眠计入可用容量。")
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "plan_date": current.isoformat(),
        "reason": reason,
        "phase": phase,
        "day_context": day_context,
        "daily_capacity_minutes": capacity,
        "buffer_ratio": profile.get("buffer_ratio", 0.15),
        "main_subject_id": main["id"],
        "main_subject_name": main["name"],
        "goal_assessment": assessment,
        "main_topic_id": main_topic["id"] if main_topic else None,
        "main_topic_name": main_topic["name"] if main_topic else None,
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
        "ranked_topics": [
            {
                "id": item["id"],
                "name": item["name"],
                "priority": item["priority"],
                "priority_basis": item["priority_basis"],
                "mastery": item.get("mastery", 0.0),
                "mistake_count": item["mistake_count"],
            }
            for item in ranked_topics
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
    key = task.get("review_key")
    if not key and task.get("topic_id"):
        key = f"topic:{task['topic_id']}"
    if not key:
        key = f"subject:{task['subject_id']}" if task.get("subject_id") else task["id"]
        if task.get("target_scope"):
            key += ":" + stable_id(str(task["target_scope"]))
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
        if task.get("target_scope"):
            existing["target_scope"] = task["target_scope"]
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
