"""通过 CLI 暴露给 Agent Skill 的本地证据服务。"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .errors import EmeraldError
from .execution import HISTORY_DIR, execution_window, save_day_plan, task_identity
from .materials import ingest_files, iter_material_files, question_stem
from .planner import KINDS, build_plan, determine_phase, due_reviews, rank_topics, stable_id, update_review_item
from .recall import QUALIFYING_BASES, classify_attempt, topic_evidence
from .recovery import preserve_original, restore_ledger
from .render import dashboard_markdown, efficiency_markdown, today_markdown, weekly_markdown
from .state import (
    STATE_DIR,
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    ensure_unique_subject,
    initialize_workspace,
    iter_jsonl,
    migrate_legacy_workspace,
    now_iso,
    read_json,
    read_jsonl,
    require_workspace,
    update_profile,
)

from .target import course_scope, matches_scope, planning_subjects

ERROR_TYPES = {"knowledge_gap", "reasoning", "procedure", "careless", "time_pressure"}
RESULTS = {"complete", "partial", "wrong", "skipped"}
QUESTION_RESULTS = {"correct", "partial", "wrong"}
EVIDENCE_LEVELS = {"user_material", "past_paper", "official", "target_school_open", "external_aid"}
CLASSIFICATION_CONFIDENCES = {"high", "medium", "low"}


def _response(command: str, workspace: Path, **kwargs: Any) -> dict[str, Any]:
    value = {
        "ok": True,
        "command": command,
        "workspace": str(workspace),
        "updated_files": kwargs.pop("updated_files", []),
        "summary": kwargs.pop("summary", "完成"),
        "next_action": kwargs.pop("next_action", None),
        "warnings": kwargs.pop("warnings", []),
    }
    value.update(kwargs)
    return value


def _find_subject(subjects: list[dict[str, Any]], name: str) -> dict[str, Any]:
    subject = next((item for item in subjects if item["name"].casefold() == name.casefold()), None)
    if subject is None:
        raise EmeraldError("subject_not_found", f"未找到科目：{name}", "先使用 subject add 添加该科目。")
    return subject


def _find_topic(
    topics: list[dict[str, Any]],
    subject_id: str,
    name: str,
) -> dict[str, Any]:
    topic = next(
        (
            item
            for item in topics
            if item.get("subject_id") == subject_id and item["name"].casefold() == name.casefold()
        ),
        None,
    )
    if topic is None:
        raise EmeraldError(
            "topic_not_found",
            f"该科目下未找到专题：{name}",
            "先使用 topic add 添加专题，或省略 --topic。",
        )
    return topic


def init(
    raw_workspace: str,
    exam_date: str,
    daily_hours: float,
    target: str,
    target_school: str | None = None,
    target_major: str | None = None,
    admission_year: int | None = None,
) -> dict[str, Any]:
    _validate_admission_year(admission_year)
    workspace, created = initialize_workspace(
        raw_workspace,
        exam_date,
        daily_hours,
        target,
        target_school,
        target_major,
        admission_year,
    )
    return _response(
        "init",
        workspace,
        updated_files=[f"{STATE_DIR}/{name}" for name in created],
        summary="青岸计划工作区已初始化。",
        next_action="使用 subject add 添加科目与分数基线。",
    )


def migrate(raw_workspace: str) -> dict[str, Any]:
    workspace, created = migrate_legacy_workspace(raw_workspace)
    return _response(
        "migrate",
        workspace,
        updated_files=created,
        summary="V0.1 工作区已复制并升级到 schema 2；原 .qingan 目录保持不变。",
        next_action="运行 status 核对科目和历史记录，再用 topic add 建立专题得分地图。",
    )


def set_routine(
    raw_workspace: str,
    weekday_hours: float | None,
    weekend_hours: float | None,
    sleep_floor_hours: float | None,
    preferred_place: str | None,
    fixed_commitments: list[str] | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if all(
        value is None
        for value in (weekday_hours, weekend_hours, sleep_floor_hours, preferred_place, fixed_commitments)
    ):
        raise EmeraldError(
            "no_routine_changes",
            "没有提供需要更新的校园节律字段。",
            "至少提供工作日/周末时间、睡眠底线、常用地点或固定安排之一。",
        )
    for label, value in (("工作日", weekday_hours), ("周末", weekend_hours)):
        if value is not None and not 0 <= value <= 24:
            raise EmeraldError(
                "invalid_routine_hours",
                f"{label}可用小时必须在 0–24 之间。",
                "填写扣除上课、通勤、吃饭和睡眠后的现实时间。",
            )
    if sleep_floor_hours is not None and (sleep_floor_hours <= 0 or sleep_floor_hours > 24):
        raise EmeraldError(
            "invalid_sleep_floor",
            "睡眠底线必须大于 0 且不超过 24 小时。",
            "填写你准备长期守住的最低睡眠时长。",
        )
    profile = read_json(root / "profile.json")
    routine = dict(profile.get("routine") or {})
    if weekday_hours is not None:
        routine["weekday_hours"] = round(float(weekday_hours), 2)
    if weekend_hours is not None:
        routine["weekend_hours"] = round(float(weekend_hours), 2)
    if sleep_floor_hours is not None:
        routine["sleep_floor_hours"] = round(float(sleep_floor_hours), 2)
    if preferred_place is not None:
        routine["preferred_place"] = preferred_place.strip() or None
    if fixed_commitments is not None:
        routine["fixed_commitments"] = [item.strip() for item in fixed_commitments if item.strip()]
    update_profile(root, {"routine": routine})
    return _response(
        "routine set",
        workspace,
        updated_files=[f"{STATE_DIR}/profile.json"],
        summary="已更新校园节律；计划会区分工作日与周末容量。",
        next_action="运行 replan，让课程、实习和生活约束进入今日容量。",
        routine=routine,
    )


def _validate_admission_year(year: int | None) -> None:
    if year is not None and not 1900 <= year <= 2200:
        raise EmeraldError("invalid_admission_year", "招生年度必须是四位年份。", "例如 --admission-year 2027。")


def set_profile_context(
    raw_workspace: str,
    target: str | None,
    target_school: str | None,
    target_major: str | None,
    admission_year: int | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    _validate_admission_year(admission_year)
    if all(value is None for value in (target, target_school, target_major, admission_year)):
        raise EmeraldError(
            "no_profile_changes",
            "没有提供需要更新的目标信息。",
            "至少提供考试目标、目标院校或目标专业之一。",
        )
    changes: dict[str, Any] = {}
    if target is not None:
        changes["target"] = target.strip() or "全国硕士研究生招生考试初试"
    if target_school is not None:
        changes["target_school"] = target_school.strip() or None
    if target_major is not None:
        changes["target_major"] = target_major.strip() or None
    if admission_year is not None:
        changes["admission_year"] = admission_year
    previous = read_json(root / "profile.json")
    profile = update_profile(root, changes)
    paths = [f"{STATE_DIR}/profile.json"]
    if course_scope(previous) != course_scope(profile):
        atomic_write_json(root / "focus.json", {})
        paths.append(f"{STATE_DIR}/focus.json")
        if read_json(root / "subjects.json") and date.fromisoformat(profile["exam_date"]) > date.today():
            paths.extend(make_plan(raw_workspace, "target-changed")["updated_files"])
        else:
            atomic_write_json(root / "plan.json", {})
            paths.append(f"{STATE_DIR}/plan.json")
    return _response(
        "profile set",
        workspace,
        updated_files=paths,
        summary="已更新考试目标、院校或专业信息。",
        next_action="核对目标院校官方范围；专业课再按科目代码绑定可靠资料。",
        profile=profile,
    )


def set_exam_goals(
    raw_workspace: str,
    total_target: float | None = None,
    floors: list[tuple[str, str]] | None = None,
    remove_floors: list[str] | None = None,
    clear_total_target: bool = False,
    basis: str | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if not any((total_target is not None, floors, remove_floors, clear_total_target, basis)):
        raise EmeraldError("no_goal_changes", "未提供目标变化。", "运行 profile goals --help。")
    if total_target is not None and clear_total_target:
        raise EmeraldError("conflicting_goal_changes", "总分目标同时设置和清除。", "保留一个操作。")
    subjects = read_json(root / "subjects.json")
    profile = read_json(root / "profile.json")
    goals = dict(profile.get("exam_goals") or {})
    configured = dict(goals.get("subject_floors") or {})
    for subject_name in remove_floors or []:
        configured.pop(_find_subject(subjects, subject_name)["id"], None)
    for subject_name, raw_floor in floors or []:
        subject = _find_subject(subjects, subject_name)
        try:
            floor = float(raw_floor)
        except (TypeError, ValueError):
            floor = float("nan")
        if not 0 <= floor <= float(subject["max_score"]):
            raise EmeraldError("invalid_subject_floor", f"{subject_name} 的门槛超出科目分值。",
                               "核对门槛、满分和适用科目。")
        configured[subject["id"]] = floor
    if total_target is not None:
        if not 0 <= total_target <= sum(float(subject["max_score"]) for subject in subjects):
            raise EmeraldError("invalid_total_target", "总分目标超出已登记科目的合计满分。",
                               "先登记完整科目，再核对总分目标。")
        goals["total_target"] = total_target
    if clear_total_target:
        goals.pop("total_target", None)
    if basis is not None:
        goals["basis"] = basis.strip() or None
    goals["subject_floors"] = configured
    updated = update_profile(root, {"exam_goals": goals})

    paths = [f"{STATE_DIR}/profile.json"]
    if subjects and date.fromisoformat(updated["exam_date"]) > date.today():
        response = make_plan(raw_workspace, "exam-goals")
        response["command"] = "profile goals"
        response["updated_files"] = paths + response["updated_files"]
        response["exam_goals"] = goals
        return response
    return _response("profile goals", workspace, updated_files=paths, exam_goals=goals,
                     summary="已保存总分目标和参考门槛。")


def add_subject(
    raw_workspace: str,
    name: str,
    max_score: float,
    baseline: float,
    target: float,
    kind: str,
    estimated_hours: float | None,
    exam_code: str | None = None,
    target_specific: bool = False,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    name = name.strip()
    if not name:
        raise EmeraldError("invalid_subject", "科目名不能为空。", "提供真实科目名后重试。")
    if kind not in KINDS:
        raise EmeraldError(
            "invalid_subject_kind",
            f"不支持能力类型：{kind}",
            f"请选择：{', '.join(sorted(KINDS))}。",
        )
    if max_score <= 0 or baseline < 0 or target < 0 or baseline > max_score or target > max_score:
        raise EmeraldError(
            "invalid_score",
            "分数必须满足 0 ≤ 当前分、目标分 ≤ 满分。",
            "核对满分、当前分和目标分后重试。",
        )
    if target < baseline:
        raise EmeraldError(
            "target_below_baseline",
            "目标分不能低于当前基线。",
            "提高目标分，或用最近一次 checkpoint 更新基线。",
        )
    if estimated_hours is not None and estimated_hours <= 0:
        raise EmeraldError("invalid_estimated_hours", "预计达标小时必须大于 0。", "移除该参数或填写正数。")
    subjects = read_json(root / "subjects.json")
    ensure_unique_subject(subjects, name)
    subject_id = "sub-" + hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()[:8]
    item = {
        "id": subject_id,
        "name": name,
        "max_score": float(max_score),
        "baseline": float(baseline),
        "current_score": float(baseline),
        "target": float(target),
        "kind": kind,
        "exam_code": exam_code.strip() if exam_code and exam_code.strip() else None,
        "estimated_hours": float(estimated_hours) if estimated_hours is not None else None,
        "score_history": [],
        "created_at": now_iso(),
    }
    if target_specific:
        scope = course_scope(read_json(root / "profile.json"), item)
        if not scope or not item["exam_code"]:
            raise EmeraldError("target_course_scope_missing", "自命题科目需要目标院校及科目代码。",
                               "先设目标院校，再用 --code 与 --target-specific 建档。")
        item.update(target_specific=True, target_scope=scope)
    subjects.append(item)
    atomic_write_json(root / "subjects.json", subjects)
    return _response(
        "subject add",
        workspace,
        updated_files=[".emerald-shore/subjects.json"],
        summary=f"已添加科目：{name}。",
        next_action="继续添加科目；全部添加后运行 plan。",
        subject=item,
    )


def add_topic(
    raw_workspace: str,
    subject_name: str,
    name: str,
    weight: float,
    mastery: float,
    confidence: float,
    estimated_hours: float | None,
    chapter: str | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name)
    name = name.strip()
    if not name:
        raise EmeraldError("invalid_topic", "专题名不能为空。", "提供考试大纲中的具体专题名。")
    if weight <= 0 or not 0 <= mastery <= 1 or not 0.1 <= confidence <= 1:
        raise EmeraldError(
            "invalid_topic_metrics",
            "专题必须满足 weight > 0、0 ≤ mastery ≤ 1、0.1 ≤ confidence ≤ 1。",
            "使用大纲/真题估算权重，用闭卷结果估算掌握度和置信度。",
        )
    if estimated_hours is not None and estimated_hours <= 0:
        raise EmeraldError("invalid_estimated_hours", "预计达标小时必须大于 0。", "移除参数或填写正数。")
    topics = read_json(root / "topics.json")
    profile = read_json(root / "profile.json")
    scope = course_scope(profile, subject) if subject.get("target_specific") else None
    if subject.get("target_specific") and scope is None:
        raise EmeraldError("target_course_scope_missing", "自命题专题需要选定目标。", "先设置目标院校。")
    if any(
        item.get("subject_id") == subject["id"] and item["name"].casefold() == name.casefold()
        and item.get("target_scope") == scope for item in topics
    ):
        raise EmeraldError("duplicate_topic", f"专题已存在：{name}", "换一个专题名或记录新的 attempt。")
    topic = {
        "id": "topic-" + hashlib.sha1(f"{subject['id']}|{name.casefold()}".encode("utf-8")).hexdigest()[:10],
        "subject_id": subject["id"],
        "name": name,
        "chapter": chapter.strip() if chapter and chapter.strip() else None,
        "weight": float(weight),
        "mastery": round(float(mastery), 4),
        "confidence": round(float(confidence), 4),
        "estimated_hours": float(estimated_hours) if estimated_hours is not None else None,
        "evidence_count": 0,
        "created_at": now_iso(),
    }
    if scope:
        topic["id"] = "topic-" + stable_id(topic["id"], str(scope))
        topic["target_scope"] = scope
    topics.append(topic)
    atomic_write_json(root / "topics.json", topics)
    return _response(
        "topic add",
        workspace,
        updated_files=[f"{STATE_DIR}/topics.json"],
        summary=f"已为 {subject_name} 添加专题：{name}。",
        next_action="继续添加高权重专题；随后运行 plan 查看主攻专题。",
        topic=topic,
    )


def update_topic(
    raw_workspace: str,
    subject_name: str,
    name: str,
    weight: float | None,
    mastery: float | None,
    confidence: float | None,
    estimated_hours: float | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subject = _find_subject(read_json(root / "subjects.json"), subject_name)
    topics = read_json(root / "topics.json")
    profile = read_json(root / "profile.json")
    topic = _find_topic([row for row in topics if matches_scope(row, profile, subject)], subject["id"], name)
    if all(value is None for value in (weight, mastery, confidence, estimated_hours)):
        raise EmeraldError(
            "no_topic_changes",
            "没有提供需要更新的专题字段。",
            "至少提供 --weight、--mastery、--confidence 或 --estimated-hours。",
        )
    if weight is not None and weight <= 0:
        raise EmeraldError("invalid_topic_weight", "专题权重必须大于 0。", "使用科目内相对权重。")
    if mastery is not None and not 0 <= mastery <= 1:
        raise EmeraldError("invalid_topic_mastery", "专题掌握度必须在 0–1。", "使用闭卷或限时证据校准。")
    if confidence is not None and not 0.1 <= confidence <= 1:
        raise EmeraldError("invalid_topic_confidence", "证据置信度必须在 0.1–1。", "降低或提高到有效范围。")
    if estimated_hours is not None and estimated_hours <= 0:
        raise EmeraldError("invalid_estimated_hours", "预计达标小时必须大于 0。", "填写正数。")
    if weight is not None:
        topic["weight"] = float(weight)
    if mastery is not None:
        topic["mastery"] = round(float(mastery), 4)
    if confidence is not None:
        topic["confidence"] = round(float(confidence), 4)
    if estimated_hours is not None:
        topic["estimated_hours"] = float(estimated_hours)
    topic["updated_at"] = now_iso()
    atomic_write_json(root / "topics.json", topics)
    return _response(
        "topic update",
        workspace,
        updated_files=[f"{STATE_DIR}/topics.json"],
        summary=f"已更新 {subject_name} 专题：{name}。",
        next_action="运行 replan 让新权重或证据进入主攻排序。",
        topic=topic,
    )


def _apply_task_results(plan: dict[str, Any], ledger: Iterable[dict[str, Any]]) -> None:
    results = {
        task_identity(row): row
        for row in ledger
        if row.get("type") == "task" and row.get("plan_date") == plan.get("plan_date")
    }
    for task in plan.get("tasks", []):
        recorded = results.get(task_identity(task))
        if recorded:
            task["status"] = recorded["result"]
            # An already executed task keeps the time planned when it was logged.
            task["planned_minutes"] = recorded.get("planned_minutes", task["planned_minutes"])
        else:
            task["status"] = "pending"


def _next_task(plan: dict[str, Any]) -> str:
    remaining = next((task for task in plan["tasks"] if task.get("status") == "pending"), None)
    if remaining:
        return remaining["title"]
    if not plan["tasks"]:
        return "今天休息，到期复习留待有容量时处理。"
    return "今天的任务都已有记录，按错因或到期安排继续。"


def _active_queue(
    root: Path, profile: dict[str, Any], subjects: list[dict[str, Any]], *,
    topics: list[dict[str, Any]] | None = None,
    questions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    subject_index = {row["id"]: row for row in subjects}
    if topics is None:
        topics = read_json(root / "topics.json")
    scope_by_key = {f"topic:{row['id']}": row for row in topics}
    source_index = {row["id"]: row for row in read_json(root / "sources.json")}
    if questions is None:
        questions = read_json(root / "question_bank.json")
    for row in questions:
        source = source_index.get(row["source_id"])
        if source:
            scope_by_key[f"question:{row['id']}"] = source
    return [
        row for row in read_json(root / "review_queue.json")
        if matches_scope(scope_by_key.get(row.get("key"), row), profile, subject_index.get(row.get("subject_id")))
    ]


def _write_views(
    root: Path, profile: dict[str, Any], subjects: list[dict[str, Any]], plan: dict[str, Any], *,
    queue: list[dict[str, Any]] | None = None,
    ledger: list[dict[str, Any]] | None = None,
) -> list[str]:
    if ledger is None:
        ledger = read_jsonl(root / "ledger.jsonl")
    _apply_task_results(plan, ledger)
    if queue is None:
        queue = _active_queue(root, profile, subjects)
    sources = read_json(root / "sources.json")
    end = date.today()
    completion = execution_window(root, ledger, end - timedelta(days=6), end, profile, subjects)
    subjects = planning_subjects(profile, subjects)
    atomic_write_text(root / "today.md", today_markdown(plan, subjects))
    atomic_write_text(
        root / "dashboard.md",
        dashboard_markdown(profile, subjects, plan, completion["completion_rate"], len(due_reviews(queue)), len(sources)),
    )
    return [".emerald-shore/plan.json", ".emerald-shore/today.md", ".emerald-shore/dashboard.md"]


def make_plan(
    raw_workspace: str, reason: str = "manual", available_minutes: int | None = None,
    main_only: bool | None = None, *, previous_plan: dict[str, Any] | None = None,
    ledger: list[dict[str, Any]] | None = None,
    mistakes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    if mistakes is None:
        mistakes = read_jsonl(root / "mistakes.jsonl")
    topics = read_json(root / "topics.json")
    queue = _active_queue(root, profile, subjects, topics=topics)
    subject_index = {row["id"]: row for row in subjects}
    topics = [row for row in topics if matches_scope(row, profile, subject_index.get(row["subject_id"]))]
    subjects = planning_subjects(profile, subjects)
    # A previous target's topic errors stay in the ledger and out of active ranking.
    active_topics = {row["id"] for row in topics}
    mistakes = [
        row for row in mistakes
        if (not row.get("topic_id") or row["topic_id"] in active_topics)
        and matches_scope(row, profile, subject_index.get(row.get("subject_id")))
    ]
    if available_minutes is not None and not 0 <= available_minutes <= 1440:
        raise EmeraldError("invalid_available_minutes", "当日可用分钟必须在 0–1440 之间。", "核对剩余可用时间。")
    current = date.today()
    previous = read_json(root / "plan.json", {}) if previous_plan is None else previous_plan
    same_day = previous.get("plan_date") == current.isoformat()
    if same_day:
        context = previous.get("day_context") or {}
        if available_minutes is None:
            available_minutes = context.get("available_minutes_override")
        if main_only is None:
            main_only = context.get("main_only")
    plan = build_plan(profile, subjects, mistakes, queue, reason, today=current,
                      topics=topics, available_minutes=available_minutes, main_only=bool(main_only))
    if not same_day:
        recovered = save_day_plan(root, previous, replace=False)
    else:
        recovered = None
    saved = save_day_plan(root, plan)
    updated = _write_views(root, profile, subjects, plan, queue=queue, ledger=ledger)
    updated.extend(f"{STATE_DIR}/{path}" for path in (recovered, saved) if path)
    atomic_write_json(root / "plan.json", plan)
    return _response(
        "replan" if reason == "replan" else "plan",
        workspace,
        updated_files=updated,
        summary=f"已生成 {plan['phase']['label']} 计划，主攻 {plan['main_subject_name']}。",
        next_action=_next_task(plan),
        warnings=plan["warnings"],
        plan=plan,
    )


def recover(raw_workspace: str, ledger_backup: str | None = None) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if ledger_backup is not None:
        paths, count = restore_ledger(root, Path(ledger_backup).expanduser().resolve())
        return _response(
            "recover", workspace, updated_files=[f"{STATE_DIR}/{path}" for path in paths],
            summary=f"账本已核验，共 {count} 条记录。", restored_records=count,
            next_action="运行 status、review 或 today 核对。派生计划若损坏，可单独运行 recover。",
        )
    read_jsonl(root / "ledger.jsonl")
    path = root / "plan.json"
    backup = None
    try:
        old = read_json(path, {})
        if not isinstance(old, dict) or (old and (not isinstance(old.get("tasks"), list) or not old.get("plan_date"))):
            raise EmeraldError("corrupt_state", "今日计划结构不完整。", "从快照重建。")
    except EmeraldError as exc:
        if exc.code != "corrupt_state":
            raise
        backup = preserve_original(root, "plan.json", path.read_bytes())
        old = {}

    using_snapshot = False
    today = date.today().isoformat()
    if not old or old.get("plan_date") != today:
        snapshot = read_json(root / HISTORY_DIR / f"{today}.json", {})
        context = snapshot.get("day_context") if isinstance(snapshot, dict) else None
        if context:
            old = {"plan_date": today, "day_context": context, "tasks": snapshot["tasks"]}
            using_snapshot = True
    response = make_plan(raw_workspace, "recovery", previous_plan=old)
    response["command"] = "recover"
    response["recovery"] = {"preserved_plan": backup, "used_today_snapshot": using_snapshot}
    if backup:
        response["updated_files"].insert(0, f"{STATE_DIR}/{backup}")
        if not using_snapshot:
            response["warnings"].append("当日临时设置无可用快照，已按档案节律重建；请核对今天的容量。")
    return response


def today(raw_workspace: str, *, read_only: bool = False) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    plan = read_json(root / "plan.json", {})
    if read_only and not isinstance(plan, dict):
        raise EmeraldError(
            "corrupt_state",
            "已保存的计划格式无法读取。",
            "保留原文件，需要重建时使用 recover。",
            {"file": "plan.json"},
        )
    if not plan or plan.get("plan_date") != date.today().isoformat():
        if read_only:
            raise EmeraldError(
                "today_plan_unavailable",
                "当前没有可查询的今日计划。",
                "需要生成计划时，可另行运行 today。",
                {"saved_plan_date": plan.get("plan_date")},
            )
        response = make_plan(raw_workspace, "daily-refresh")
        response["command"] = "today"
        return response
    _apply_task_results(plan, iter_jsonl(root / "ledger.jsonl"))
    return _response(
        "today",
        workspace,
        summary=f"今日共有 {len(plan['tasks'])} 个关键任务。",
        next_action=_next_task(plan),
        warnings=plan.get("warnings", []),
        plan=plan,
    )


def log_task(
    raw_workspace: str,
    task_id: str,
    minutes: int,
    result: str,
    error_type: str | None,
    note: str | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    read_jsonl(root / "ledger.jsonl")
    read_jsonl(root / "mistakes.jsonl")
    if minutes < 0 or minutes > 24 * 60:
        raise EmeraldError("invalid_minutes", "实际分钟必须在 0–1440 之间。", "核对学习时长后重试。")
    if result not in RESULTS:
        raise EmeraldError("invalid_result", f"不支持结果：{result}", f"请选择：{', '.join(sorted(RESULTS))}。")
    if error_type is not None and error_type not in ERROR_TYPES:
        raise EmeraldError(
            "invalid_error_type",
            f"不支持错因：{error_type}",
            f"请选择：{', '.join(sorted(ERROR_TYPES))}。",
        )
    plan = read_json(root / "plan.json", {})
    task = next((item for item in plan.get("tasks", []) if item.get("id") == task_id), None)
    if task is None:
        raise EmeraldError(
            "task_not_found",
            f"当前计划中没有 task-id：{task_id}",
            "运行 today 获取当前任务 ID。",
        )
    row = {
        "type": "task",
        "recorded_at": now_iso(),
        "plan_date": plan.get("plan_date"),
        "task_id": task_id,
        "subject_id": task.get("subject_id"),
        "topic_id": task.get("topic_id"),
        "planned_minutes": task.get("planned_minutes"),
        "review_keys": task.get("review_keys"),
        "actual_minutes": minutes,
        "result": result,
        "error_type": error_type,
        "note": note,
    }
    if task.get("target_scope"):
        row["target_scope"] = task["target_scope"]
    append_jsonl(root / "ledger.jsonl", row)
    if result in {"partial", "wrong"}:
        append_jsonl(
            root / "mistakes.jsonl",
            {
                "recorded_at": row["recorded_at"],
                "task_id": task_id,
                "subject_id": task.get("subject_id"),
                "topic_id": task.get("topic_id"),
                "target_scope": task.get("target_scope"),
                "error_type": error_type or "knowledge_gap",
                "note": note,
            },
        )
    queue = read_json(root / "review_queue.json")
    if task.get("role") == "review" and task.get("review_keys"):
        for review_key in task["review_keys"]:
            if review_key.startswith("question:"):
                continue  # Item-level evidence must come through attempt.
            existing = next((item for item in queue if item.get("key") == review_key), None)
            if existing is None:
                continue
            queue = update_review_item(
                queue,
                {
                    "id": task_id,
                    "review_key": review_key,
                    "subject_id": existing.get("subject_id"),
                    "title": existing.get("label", task.get("title")),
                },
                result,
            )
    else:
        queue = update_review_item(queue, task, result)
    atomic_write_json(root / "review_queue.json", queue)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    _write_views(root, profile, subjects, plan)
    return _response(
        "log",
        workspace,
        updated_files=[f"{STATE_DIR}/{name}" for name in ("ledger.jsonl", "review_queue.json", "today.md", "dashboard.md")]
        + ([".emerald-shore/mistakes.jsonl"] if result in {"partial", "wrong"} else []),
        summary=f"已记录任务结果：{result}，实际 {minutes} 分钟。",
        next_action="运行 review 查看到期复习，或继续今日下一项任务。",
    )


def checkpoint(
    raw_workspace: str, subject_name: str, score: float, max_score: float, minutes: int,
    scope: str | None = None, series: str | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    read_jsonl(root / "ledger.jsonl")
    read_jsonl(root / "mistakes.jsonl")
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name)
    if not all(math.isfinite(value) for value in (score, max_score)) or not 0 <= score <= max_score or max_score <= 0 or minutes <= 0:
        raise EmeraldError(
            "invalid_checkpoint",
            "检查点必须满足 0 ≤ 得分 ≤ 满分，且用时大于 0。",
            "核对得分、满分和用时后重试。",
        )
    subject_max = float(subject["max_score"])
    scope = scope or ("full" if max_score == subject_max else "partial")
    if scope not in {"full", "partial"} or (scope == "full" and max_score != subject_max):
        raise EmeraldError(
            "invalid_checkpoint_scope", "整科检查点的满分须与科目满分一致。",
            "专题或模块小测请使用 --scope partial。",
        )
    target = course_scope(read_json(root / "profile.json"), subject) if subject.get("target_specific") else None
    if subject.get("target_specific") and target is None:
        raise EmeraldError("target_course_scope_missing", "自命题成绩需要选定目标。", "先设置目标院校。")
    normalized = round(float(score), 2) if scope == "full" else None
    entry = {
        "recorded_at": now_iso(),
        "raw_score": float(score),
        "raw_max_score": float(max_score),
        "normalized_score": normalized,
        "scope": scope,
        "series": series.strip() if series else None,
        "minutes": int(minutes),
    }
    if target:
        entry["target_scope"] = target
    if normalized is not None:
        subject["current_score"] = normalized
    subject.setdefault("score_history", []).append(entry)
    atomic_write_json(root / "subjects.json", subjects)
    append_jsonl(
        root / "ledger.jsonl",
        {"type": "checkpoint", "subject_id": subject["id"], **entry},
    )
    if scope == "partial":
        return _response(
            "checkpoint", workspace,
            updated_files=[f"{STATE_DIR}/subjects.json", f"{STATE_DIR}/ledger.jsonl"],
            summary=f"已记录 {subject_name} 专题小测 {score:g}/{max_score:g}。",
            next_action="按专题错因安排复测。整科主攻变化以整卷限时证据为准。",
            checkpoint=entry,
        )
    if date.fromisoformat(read_json(root / "profile.json")["exam_date"]) <= date.today():
        return _response(
            "checkpoint", workspace,
            updated_files=[f"{STATE_DIR}/subjects.json", f"{STATE_DIR}/ledger.jsonl"],
            summary=f"已记录 {subject_name} 整科检查点。",
            warnings=["考试日期已到或已过。本次只保存成绩。"],
            checkpoint=entry,
        )
    response = make_plan(raw_workspace, "checkpoint")
    response["command"] = "checkpoint"
    response["checkpoint"] = entry
    response["summary"] = f"已记录 {subject_name} 检查点，并据此重排计划。"
    response["updated_files"] = list(dict.fromkeys([".emerald-shore/subjects.json", ".emerald-shore/ledger.jsonl", *response["updated_files"]]))
    return response


def ingest(
    raw_workspace: str,
    inputs: list[str],
    evidence_level: str,
    subject_name: str | None = None,
    topic_name: str | None = None,
    classification_confidence: str = "high",
    match_note: str | None = None,
    replace_metadata: bool = False,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if evidence_level not in EVIDENCE_LEVELS:
        raise EmeraldError(
            "invalid_evidence_level",
            f"不支持证据等级：{evidence_level}",
            f"请选择：{', '.join(sorted(EVIDENCE_LEVELS))}。",
        )
    if classification_confidence not in CLASSIFICATION_CONFIDENCES:
        raise EmeraldError(
            "invalid_classification_confidence",
            f"不支持材料归类置信度：{classification_confidence}",
            f"请选择：{', '.join(sorted(CLASSIFICATION_CONFIDENCES))}。",
        )
    if classification_confidence == "low" and (subject_name or topic_name):
        raise EmeraldError(
            "low_confidence_binding",
            "低置信材料不能直接绑定科目或专题。",
            "先不带 --subject/--topic 建库并标记待确认；核对后以更高置信度重新绑定。",
        )
    if classification_confidence == "medium" and topic_name:
        raise EmeraldError(
            "medium_confidence_topic_binding",
            "中等置信材料可以暂归科目，但不能直接绑定具体专题。",
            "移除 --topic；确认范围和题型证据后再绑定专题。",
        )
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name) if subject_name else None
    profile = read_json(root / "profile.json")
    if evidence_level == "target_school_open":
        if not profile.get("target_school"):
            raise EmeraldError(
                "target_school_required",
                "目标院校公开资料需要先记录目标院校。",
                "运行 profile set WORKSPACE --target-school NAME 后重试。",
            )
        if subject is None or not match_note or not match_note.strip():
            raise EmeraldError(
                "target_school_match_required",
                "目标院校公开资料必须绑定科目并记录匹配依据。",
                "提供 --subject 和 --match-note，写明院校、科目/代码、资料类型与可追溯年份。",
            )
    topics = read_json(root / "topics.json")
    if topic_name and subject is None:
        raise EmeraldError("topic_requires_subject", "使用 --topic 时必须同时提供 --subject。", "补充科目名后重试。")
    scoped = evidence_level == "target_school_open" or bool(subject and subject.get("target_specific"))
    target = course_scope(profile, subject) if scoped else None
    if scoped and target is None:
        raise EmeraldError("target_course_scope_missing", "定向资料需要选定目标。", "先设置目标院校。")
    topics = [row for row in topics if matches_scope(row, profile, subject)]
    topic = _find_topic(topics, subject["id"], topic_name) if topic_name and subject else None
    files = iter_material_files(inputs, root)
    if not files:
        raise EmeraldError(
            "no_supported_materials",
            "没有找到支持的材料文件。",
            "提供 PDF、DOCX、PPTX、TXT、Markdown 或 HTML 文件。",
        )
    sources = read_json(root / "sources.json")
    questions = read_json(root / "question_bank.json")
    sources, questions, added, warnings = ingest_files(
        files,
        root,
        sources,
        questions,
        evidence_level,
        subject["id"] if subject else None,
        topic["id"] if topic else None,
        classification_confidence,
        match_note.strip() if match_note and match_note.strip() else None,
        replace_metadata,
        target_scope=target,
    )
    atomic_write_json(root / "sources.json", sources)
    atomic_write_json(root / "question_bank.json", questions, indent=None)
    plan = read_json(root / "plan.json", {})
    if plan:
        _write_views(root, profile, subjects, plan)
    binding_updates = sum(1 for warning in warnings if warning.startswith("更新重复材料的科目/专题绑定"))
    if classification_confidence in {"medium", "low"}:
        warnings.append("材料尚未达到高置信归类；不得用它单独确定考试范围或专题权重。")
    summary = f"已建库 {len(added)} 个新材料，提取 {sum(item['question_count'] for item in added)} 道来源题。"
    if binding_updates:
        summary += f"另更新 {binding_updates} 个已有材料的科目/专题绑定。"
    return _response(
        "ingest",
        workspace,
        updated_files=[".emerald-shore/sources.json", ".emerald-shore/question_bank.json", ".emerald-shore/materials/"],
        summary=summary,
        next_action="核对材料警告；随后运行 plan 或开始一次来源可追溯的闭卷训练。",
        warnings=warnings,
        added_sources=added,
        binding_updates=binding_updates,
    )


def drill(
    raw_workspace: str, subject_name: str, topic_name: str | None = None, fresh: bool = False,
    question_id: str | None = None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name)
    profile = read_json(root / "profile.json")
    topics = [row for row in read_json(root / "topics.json") if matches_scope(row, profile, subject)]
    topic = _find_topic(topics, subject["id"], topic_name) if topic_name else None
    questions = read_json(root / "question_bank.json")
    sources = {row["id"]: row for row in read_json(root / "sources.json")}
    if question_id and fresh:
        raise EmeraldError("review_filter_conflict", "指定原题与只抽新题冲突。", "保留 --question-id 或 --fresh。")
    candidates = []
    for item in questions:
        if item.get("subject_id") != subject["id"]:
            continue
        if question_id and item["id"] != question_id:
            continue
        if topic and item.get("topic_id") != topic["id"]:
            continue
        source = sources.get(item["source_id"])
        if source is None or not matches_scope(source, profile, subject):
            continue
        stem = question_stem(item["text"])
        if stem:
            candidates.append((item, stem))
    if not candidates:
        unassigned = sum(1 for item in questions if not item.get("subject_id"))
        recovery = "先用 ingest --subject 绑定该科目的来源材料。"
        if unassigned:
            recovery += f" 当前还有 {unassigned} 道旧版未绑定来源题，可重新 ingest 其材料完成绑定。"
        raise EmeraldError("no_source_questions", f"{subject_name} 暂无可用来源题。", recovery)
    if fresh:
        candidates = [
            (item, stem) for item, stem in candidates
            if not item.get("attempts") and not item.get("presented_count")
        ]
        if not candidates:
            raise EmeraldError("no_fresh_source_questions", "当前范围没有未展示的新来源题。",
                               "导入同范围的其他来源题，或经学生同意改为重做旧题。")
    queue = read_json(root / "review_queue.json")
    due_keys = {item.get("key") for item in due_reviews(queue)}

    def order(question: dict[str, Any]):
        attempts = question.get("attempts", [])
        last_result = attempts[-1].get("result") if attempts else None
        question_key = f"question:{question['id']}"
        if question_key in due_keys:
            band = 0
        elif last_result in {"wrong", "partial"}:
            band = 1
        elif not attempts:
            band = 2
        else:
            band = 3
        return band, question.get("last_presented_at", ""), question["id"]

    selected, selected_stem = min(candidates, key=lambda candidate: order(candidate[0]))
    selected["presented_count"] = int(selected.get("presented_count", 0)) + 1
    selected["last_presented_at"] = now_iso()
    atomic_write_json(root / "question_bank.json", questions, indent=None)
    source = sources[selected["source_id"]]
    public_question = {
        key: selected.get(key)
        for key in ("id", "subject_id", "topic_id", "locator", "source_grounded")
    }
    public_question["text"] = selected_stem
    public_source = None
    if source:
        public_source = {
            "id": source["id"],
            "name": source["name"],
            "path": source["path"],
            "evidence_level": source["evidence_level"],
            "classification_confidence": source.get("classification_confidence", "high"),
            "match_note": source.get("match_note"),
            "target_scope": source.get("target_scope"),
            "locator": selected.get("locator"),
        }
    return _response(
        "drill",
        workspace,
        updated_files=[f"{STATE_DIR}/question_bank.json"],
        summary=f"已选择一道 {subject_name} 来源题；答案保持隐藏。",
        next_action="让学生独立作答；完成后运行 attempt 记录结果。",
        question=public_question,
        source=public_source,
    )


def record_attempt(
    raw_workspace: str,
    question_id: str,
    result: str,
    minutes: int,
    error_type: str | None,
    note: str | None,
    mode: str = "independent",
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    read_jsonl(root / "ledger.jsonl")
    read_jsonl(root / "mistakes.jsonl")
    if result not in QUESTION_RESULTS:
        raise EmeraldError("invalid_question_result", "答题结果无效。", "使用 correct、partial 或 wrong。")
    if mode not in {"independent", "assisted"}:
        raise EmeraldError("invalid_question_mode", "作答模式无效。", "使用 independent 或 assisted。")
    if not 0 <= minutes <= 1440:
        raise EmeraldError("invalid_minutes", "实际分钟必须在 0–1440 之间。", "核对用时后重试。")
    if error_type is not None and error_type not in ERROR_TYPES:
        raise EmeraldError("invalid_error_type", f"不支持错因：{error_type}", f"请选择：{', '.join(sorted(ERROR_TYPES))}。")
    questions = read_json(root / "question_bank.json")
    question = next((item for item in questions if item["id"] == question_id), None)
    if question is None:
        raise EmeraldError("question_not_found", f"未找到 question-id：{question_id}", "运行 drill 获取当前来源题。")
    sources = {row["id"]: row for row in read_json(root / "sources.json")}
    profile = read_json(root / "profile.json")
    subject = next((row for row in read_json(root / "subjects.json") if row["id"] == question.get("subject_id")), None)
    source = sources.get(question["source_id"], {})
    if not matches_scope(source, profile, subject):
        raise EmeraldError("inactive_target_question", "这道题不属于当前目标。", "选择当前院校的来源题。")

    today = date.today()
    queue = read_json(root / "review_queue.json")
    key = f"question:{question_id}"
    scheduled = next((item for item in queue if item["key"] == key), None)
    history = question.setdefault("attempts", [])
    basis = classify_attempt(history, scheduled, today, mode)
    qualified = basis in QUALIFYING_BASES
    attempt = {
        "recorded_at": now_iso(), "study_date": today.isoformat(), "result": result,
        "minutes": minutes, "mode": mode, "evidence_basis": basis, "error_type": error_type, "note": note,
    }
    history.append(attempt)
    atomic_write_json(root / "question_bank.json", questions, indent=None)
    paths = [f"{STATE_DIR}/question_bank.json", f"{STATE_DIR}/ledger.jsonl"]

    topics = read_json(root / "topics.json")
    topic = next((item for item in topics if item["id"] == question.get("topic_id")), None)
    if topic and qualified:
        observed = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}[result]
        topic["mastery"] = round(float(topic.get("mastery", 0.0)) * 0.7 + observed * 0.3, 4)
        topic["confidence"] = round(min(1.0, float(topic.get("confidence", 0.5)) + 0.05), 4)
        topic["evidence_count"] = int(topic.get("evidence_count", 0)) + 1
        topic["last_evidence_at"] = attempt["recorded_at"]
        atomic_write_json(root / "topics.json", topics)
        paths.append(f"{STATE_DIR}/topics.json")

    row = {
        **attempt, "type": "question-attempt", "question_id": question_id,
        "subject_id": question.get("subject_id"), "topic_id": question.get("topic_id"),
        "target_scope": source.get("target_scope"), "actual_minutes": minutes,
    }
    append_jsonl(root / "ledger.jsonl", row)
    if qualified and result in {"partial", "wrong"}:
        append_jsonl(root / "mistakes.jsonl", {**row, "error_type": error_type or "knowledge_gap"})
        paths.append(f"{STATE_DIR}/mistakes.jsonl")
    if qualified:
        update_review_item(
            queue, {
                "id": question_id, "review_key": key, "subject_id": question.get("subject_id"),
                "title": f"重做来源题 {question_id}",
            }, "complete" if result == "correct" else "wrong", today,
        )
        scheduled = next(item for item in queue if item["key"] == key)
        atomic_write_json(root / "review_queue.json", queue)
        paths.append(f"{STATE_DIR}/review_queue.json")
    next_action = "原题按原日期回测；可用未见变式检验能否独立做出。"
    if qualified:
        next_action = "先说出决定性步骤，再做一题近迁移。" if result == "correct" else (
            "定位第一个关键错因，补最小解释，然后用未见变式验证。"
        )
    return _response(
        "attempt", workspace, updated_files=paths,
        summary=f"已记录来源题结果：{result}。" + ("更新独立证据。" if qualified else "保留为练习记录。"),
        next_action=next_action, topic=topic, evidence_basis=basis,
        mastery_evidence=topic_evidence(questions, topic["id"]) if topic else None, review_item=scheduled,
    )


def set_focus(
    raw_workspace: str,
    task_id: str,
    when: str,
    where: str | None,
    obstacle: str | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    plan = read_json(root / "plan.json", {})
    task = next((item for item in plan.get("tasks", []) if item["id"] == task_id), None)
    if task is None:
        raise EmeraldError("task_not_found", f"当前计划中没有 task-id：{task_id}", "运行 today 获取当前任务。")
    profile = read_json(root / "profile.json")
    routine = profile.get("routine") if isinstance(profile.get("routine"), dict) else {}
    resolved_place = where.strip() if where and where.strip() else routine.get("preferred_place")
    if not when.strip() or not resolved_place:
        raise EmeraldError(
            "invalid_focus_cue",
            "启动触发必须包含可观察的时间/事件和地点。",
            "提供 --where，或先用 routine set 保存常用学习地点。",
        )
    focus = {
        "schema_version": 2,
        "created_at": now_iso(),
        "task_id": task_id,
        "when": when.strip(),
        "where": resolved_place,
        "obstacle": obstacle.strip() if obstacle else None,
        "if_then": f"如果到了{when.strip()}，并且我在{resolved_place}，那么我先打开任务“{task['title']}”，完成 5 分钟闭卷启动。",
        "coping_plan": (
            f"如果出现“{obstacle.strip()}”，那么把任务缩成 2 分钟，并先完成第一步。" if obstacle else None
        ),
    }
    atomic_write_json(root / "focus.json", focus)
    return _response(
        "focus",
        workspace,
        updated_files=[f"{STATE_DIR}/focus.json"],
        summary="已把意愿转换为可观察的 if–then 启动协议。",
        next_action=focus["if_then"],
        focus=focus,
    )


def _dated_rows(rows: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        try:
            occurred = datetime.fromisoformat(row["recorded_at"]).astimezone().date()
        except (KeyError, TypeError, ValueError):
            continue
        if start <= occurred <= end:
            result.append(row)
    return result


def _efficiency_snapshot(
    root: Path, days: int, *, full_ledger: list[dict[str, Any]] | None = None,
    full_mistakes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    if full_ledger is None:
        full_ledger = read_jsonl(root / "ledger.jsonl")
    if full_mistakes is None:
        full_mistakes = read_jsonl(root / "mistakes.jsonl")
    ledger = _dated_rows(full_ledger, start, end)
    mistakes = _dated_rows(full_mistakes, start, end)
    profile = read_json(root / "profile.json")
    subject_index = {item["id"]: item for item in read_json(root / "subjects.json")}
    ledger = [row for row in ledger if matches_scope(row, profile, subject_index.get(row.get("subject_id")))]
    mistakes = [row for row in mistakes if matches_scope(row, profile, subject_index.get(row.get("subject_id")))]
    execution = execution_window(root, full_ledger, start, end, profile, list(subject_index.values()))
    all_attempts = [row for row in ledger if row.get("type") == "question-attempt"]
    attempt_rows = [row for row in all_attempts if row.get("evidence_basis") in QUALIFYING_BASES]
    checkpoint_rows = [row for row in ledger if row.get("type") == "checkpoint"]

    completion_rate = execution["completion_rate"]
    outcome_counts = {name: 0 for name in ("correct", "partial", "wrong")}
    for row in attempt_rows:
        result = row.get("result")
        if result in outcome_counts:
            outcome_counts[result] += 1
    correct_rate = outcome_counts["correct"] / len(attempt_rows) if attempt_rows else None

    error_counts: dict[str, int] = {}
    for row in mistakes:
        key = row.get("error_type") or "knowledge_gap"
        error_counts[key] = error_counts.get(key, 0) + 1
    recurring_types = sorted(key for key, count in error_counts.items() if count >= 2)

    subjects = subject_index
    checkpoint_groups: dict[tuple[str, str | None, int], list[float]] = {}
    for row in checkpoint_rows:
        subject_id = row.get("subject_id")
        score = row.get("normalized_score")
        if (
            subject_id in subjects and isinstance(score, (int, float))
            and row.get("scope") != "partial"
            and row.get("raw_max_score") == float(subjects[subject_id]["max_score"])
        ):
            group = (subject_id, row.get("series") or None, row.get("minutes", 0))
            checkpoint_groups.setdefault(group, []).append(float(score))
    checkpoint_changes = []
    for (subject_id, series, minutes), scores in checkpoint_groups.items():
        if len(scores) >= 2:
            checkpoint_changes.append(
                {
                    "subject_id": subject_id,
                    "subject": subjects[subject_id]["name"],
                    "series": series,
                    "minutes": minutes,
                    "first": scores[0],
                    "latest": scores[-1],
                    "delta_points": round(scores[-1] - scores[0], 2),
                }
            )

    evidence_events = len(attempt_rows) + len(checkpoint_rows)
    if not execution["planned_tasks"] and evidence_events == 0:
        diagnosis = "insufficient_evidence"
        label = "证据不足，暂不评价效率"
        explanation = "现在只有感觉，没有足够记录。先完成一次今日任务和一次闭卷或限时检查，再谈效率。"
        next_action = "执行当前主攻任务并记录结果；不要用‘今天坐了很久’代替训练证据。"
    elif completion_rate is not None and completion_rate < 0.60:
        diagnosis = "load_mismatch"
        label = "计划与现实容量不匹配"
        explanation = "主要问题不是不够努力，而是计划没有稳定发生。先缩小任务，再判断学习方法。"
        next_action = "运行 replan，保留一个主攻和必要复习，删除本周最低价值任务。"
    elif evidence_events == 0:
        diagnosis = "input_heavy"
        label = "输入很多，验证太少"
        explanation = "已有学习记录，但缺少闭卷、来源题或检查点。知识可能只是看着眼熟。"
        next_action = "把下一次学习改成闭卷提取、来源题或限时输出，并记录结果。"
    elif len(attempt_rows) >= 3 and correct_rate is not None and correct_rate < 0.50:
        diagnosis = "accuracy_gap"
        label = "练习已经发生，但独立正确率偏低"
        explanation = "继续堆题只会把错误练熟。先定位定义、识别、推理、步骤还是时间压力。"
        next_action = "暂停扩题，回到第一个重复错因做最小重建，再用替代题复测。"
    elif recurring_types:
        diagnosis = "recurring_error"
        label = "同类错因正在复发"
        explanation = "错题数量不是核心，重复出现的同类错误才是当前效率漏点。"
        next_action = f"只处理重复错因：{recurring_types[0]}；修正后安排一次无提示复测。"
    elif not checkpoint_groups:
        diagnosis = "checkpoint_missing"
        label = "日常训练有证据，但缺少阶段检查点"
        explanation = "局部练习在推进，但还不能判断是否转化成考试表现。"
        next_action = "为主攻科目安排一次同口径限时检查点，建立可比较基线。"
    else:
        diagnosis = "evidence_loop_stable"
        label = "证据闭环正在稳定运行"
        explanation = "执行、独立训练和检查点都已发生。接下来关注趋势，不追求把每个数字刷得漂亮。"
        next_action = "保持当前主攻；下一周只根据检查点变化和重复错因调整策略。"

    return {
        "schema_version": 2,
        "generated_at": now_iso(),
        "days": days,
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "principle": "multi-dimensional-no-composite-score",
        "execution": execution,
        "evidence": {
            "verified_events": evidence_events,
            "question_attempts": len(attempt_rows),
            "recorded_question_attempts": len(all_attempts),
            "practice_only_attempts": sum(row.get("evidence_basis") not in QUALIFYING_BASES and row.get("evidence_basis") is not None for row in all_attempts),
            "legacy_attempts": sum(row.get("evidence_basis") is None for row in all_attempts),
            "question_attempt_minutes": sum(int(row.get("actual_minutes") or 0) for row in all_attempts),
            "checkpoints": len(checkpoint_rows),
        },
        "outcomes": {
            "attempts": len(attempt_rows),
            **outcome_counts,
            "correct_rate": correct_rate,
        },
        "errors": {"counts": error_counts, "recurring_types": recurring_types},
        "checkpoints": {"count": len(checkpoint_rows), "changes": checkpoint_changes},
        "diagnosis": diagnosis,
        "diagnosis_label": label,
        "explanation": explanation,
        "next_action": next_action,
    }


def efficiency_report(raw_workspace: str, days: int = 7) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if days < 1 or days > 90:
        raise EmeraldError(
            "invalid_efficiency_window",
            "效率评估窗口必须在 1–90 天之间。",
            "使用 --days 7 查看一周，或 --days 30 查看一个月。",
        )
    report = _efficiency_snapshot(root, days)
    atomic_write_text(root / "efficiency.md", efficiency_markdown(report))
    return _response(
        "efficiency",
        workspace,
        updated_files=[f"{STATE_DIR}/efficiency.md"],
        summary=f"效率评估完成：{report['diagnosis_label']}。",
        next_action=report["next_action"],
        efficiency=report,
    )


def weekly_review(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    mistakes = read_jsonl(root / "mistakes.jsonl")
    ledger = read_jsonl(root / "ledger.jsonl")
    replanned = make_plan(raw_workspace, "weekly-review", ledger=ledger, mistakes=mistakes)
    plan = replanned["plan"]
    today_value = date.today()
    start = today_value - timedelta(days=6)
    efficiency = _efficiency_snapshot(root, 7, full_ledger=ledger, full_mistakes=mistakes)
    execution = efficiency["execution"]
    adherence = execution["completion_rate"]
    error_counts = efficiency["errors"]["counts"]
    evidence_events = efficiency["evidence"]["verified_events"]
    if adherence is not None and adherence < 0.60:
        decision = "执行率低于 60%：不补旧计划；下周缩小单次任务，保留主攻并删除低价值任务。"
    elif evidence_events == 0:
        decision = "本周缺少闭卷或限时证据：下周减少输入型学习，先安排一次可判定检查点。"
    else:
        decision = "保留当前主攻，用错因和限时结果继续校准；不因单次情绪波动改动全局。"
    focus = read_json(root / "focus.json", {})
    if efficiency["diagnosis"] == "evidence_loop_stable":
        next_action = focus.get("if_then") or "保持当前主攻，并为下一次训练设置具体启动条件。"
    else:
        next_action = efficiency["next_action"]
    review_payload = {
        "schema_version": 2,
        "generated_at": now_iso(),
        "period": {"start": start.isoformat(), "end": today_value.isoformat()},
        "adherence": adherence,
        "planned_minutes": execution["planned_minutes"],
        "actual_minutes": execution["actual_task_minutes"] + efficiency["evidence"]["question_attempt_minutes"],
        "execution": execution,
        "evidence_events": evidence_events,
        "error_counts": error_counts,
        "efficiency": efficiency,
        "next_main_subject": plan["main_subject_name"],
        "next_main_topic": plan.get("main_topic_name"),
        "decision": decision,
        "next_action": next_action,
    }
    atomic_write_text(root / "weekly.md", weekly_markdown(review_payload))
    atomic_write_text(root / "efficiency.md", efficiency_markdown(efficiency))
    return _response(
        "weekly",
        workspace,
        updated_files=list(
            dict.fromkeys(
                [*replanned["updated_files"], f"{STATE_DIR}/weekly.md", f"{STATE_DIR}/efficiency.md"]
            )
        ),
        summary=f"周复盘完成；下周主攻 {plan['main_subject_name']}。",
        next_action=next_action,
        warnings=replanned.get("warnings", []),
        weekly=review_payload,
        plan=plan,
    )


def review(raw_workspace: str, through: str | None = None) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    try:
        cutoff = date.fromisoformat(through) if through else date.today()
    except ValueError as exc:
        raise EmeraldError("invalid_review_date", "复习截止日期格式错误。", "使用 YYYY-MM-DD。") from exc
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    index = {row["id"]: row for row in subjects}
    topics = read_json(root / "topics.json")
    questions = read_json(root / "question_bank.json")
    due = due_reviews(_active_queue(root, profile, subjects, topics=topics, questions=questions), cutoff)
    questions_by_topic = defaultdict(list)
    for question in questions:
        if isinstance(question.get("topic_id"), str):
            questions_by_topic[question["topic_id"]].append(question)
    mastery = [{
        "topic_id": row["id"], "topic": row["name"], "mastery": row["mastery"],
        **topic_evidence(questions_by_topic.get(row["id"], []), row["id"]),
    } for row in topics if matches_scope(row, profile, index.get(row["subject_id"]))]
    return _response(
        "review", workspace,
        summary=f"截至 {cutoff.isoformat()} 有 {len(due)} 个复习项。",
        next_action=due[0]["label"] if due else "此前没有到期项；执行今日主攻任务。",
        through=cutoff.isoformat(), due=due, topic_evidence=mastery,
    )


def status(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    plan = read_json(root / "plan.json", {})
    queue = _active_queue(root, profile, subjects)
    subject_index = {row["id"]: row for row in subjects}
    subjects = planning_subjects(profile, subjects)
    ledger = read_jsonl(root / "ledger.jsonl")
    sources = read_json(root / "sources.json")
    topics = [row for row in read_json(root / "topics.json") if matches_scope(row, profile, subject_index.get(row["subject_id"]))]
    focus = read_json(root / "focus.json", {})
    phase = determine_phase(profile["exam_date"])
    efficiency = _efficiency_snapshot(root, 7, full_ledger=ledger)
    due_count = len(due_reviews(queue))
    adherence = efficiency["execution"]["completion_rate"]
    warnings = []
    if adherence is not None and adherence < 0.60:
        warnings.append("近 7 天执行率低于 60%；建议缩小任务并运行 replan，不做人格归因。")
    return _response(
        "status",
        workspace,
        summary=f"距考试 {phase['days_remaining']} 天；{len(subjects)} 门科目；{due_count} 个到期复习项。",
        next_action=plan.get("tasks", [{}])[0].get("title") if plan.get("tasks") else "添加科目并运行 plan。",
        warnings=warnings,
        profile=profile,
        phase=phase,
        subjects=subjects,
        main_subject=plan.get("main_subject_name"),
        main_topic=plan.get("main_topic_name"),
        adherence_7d=adherence,
        efficiency_diagnosis=efficiency["diagnosis"],
        efficiency_label=efficiency["diagnosis_label"],
        due_review_count=due_count,
        source_count=len(sources),
        topic_count=len(topics),
        focus=focus or None,
        ledger_count=len(ledger),
    )
