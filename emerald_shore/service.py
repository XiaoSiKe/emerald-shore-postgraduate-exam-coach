"""通过 CLI 暴露给 Agent Skill 的本地证据服务。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import EmeraldError
from .materials import ingest_files, iter_material_files
from .planner import KINDS, build_plan, determine_phase, due_reviews, rank_topics, update_review_item
from .render import dashboard_markdown, today_markdown, weekly_markdown
from .state import (
    STATE_DIR,
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    ensure_unique_subject,
    initialize_workspace,
    migrate_legacy_workspace,
    now_iso,
    read_json,
    read_jsonl,
    require_workspace,
    update_profile,
)

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
) -> dict[str, Any]:
    workspace, created = initialize_workspace(
        raw_workspace,
        exam_date,
        daily_hours,
        target,
        target_school,
        target_major,
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
        if value is not None and (value <= 0 or value > 24):
            raise EmeraldError(
                "invalid_routine_hours",
                f"{label}可用小时必须大于 0 且不超过 24。",
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


def set_profile_context(
    raw_workspace: str,
    target: str | None,
    target_school: str | None,
    target_major: str | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if all(value is None for value in (target, target_school, target_major)):
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
    profile = update_profile(root, changes)
    return _response(
        "profile set",
        workspace,
        updated_files=[f"{STATE_DIR}/profile.json"],
        summary="已更新考试目标、院校或专业信息。",
        next_action="核对目标院校官方范围；专业课再按科目代码绑定可靠资料。",
        profile=profile,
    )


def add_subject(
    raw_workspace: str,
    name: str,
    max_score: float,
    baseline: float,
    target: float,
    kind: str,
    estimated_hours: float | None,
    exam_code: str | None = None,
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
    if any(
        item.get("subject_id") == subject["id"] and item["name"].casefold() == name.casefold()
        for item in topics
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
    topic = _find_topic(topics, subject["id"], name)
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


def _adherence(ledger: list[dict[str, Any]], current: date | None = None) -> float | None:
    today = current or date.today()
    start = today - timedelta(days=6)
    task_rows = []
    for row in ledger:
        if row.get("type") != "task":
            continue
        try:
            occurred = datetime.fromisoformat(row["recorded_at"]).date()
        except (KeyError, ValueError):
            continue
        if start <= occurred <= today:
            task_rows.append(row)
    if not task_rows:
        return None
    completed = sum(1 for row in task_rows if row.get("result") == "complete")
    return completed / len(task_rows)


def _write_views(root: Path, profile: dict[str, Any], subjects: list[dict[str, Any]], plan: dict[str, Any]) -> list[str]:
    ledger = read_jsonl(root / "ledger.jsonl")
    queue = read_json(root / "review_queue.json")
    sources = read_json(root / "sources.json")
    atomic_write_text(root / "today.md", today_markdown(plan, subjects))
    atomic_write_text(
        root / "dashboard.md",
        dashboard_markdown(profile, subjects, plan, _adherence(ledger), len(due_reviews(queue)), len(sources)),
    )
    return [".emerald-shore/plan.json", ".emerald-shore/today.md", ".emerald-shore/dashboard.md"]


def make_plan(raw_workspace: str, reason: str = "manual") -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    mistakes = read_jsonl(root / "mistakes.jsonl")
    queue = read_json(root / "review_queue.json")
    topics = read_json(root / "topics.json")
    plan = build_plan(profile, subjects, mistakes, queue, reason, topics=topics)
    atomic_write_json(root / "plan.json", plan)
    updated = _write_views(root, profile, subjects, plan)
    return _response(
        "replan" if reason == "replan" else "plan",
        workspace,
        updated_files=updated,
        summary=f"已生成 {plan['phase']['label']} 计划，主攻 {plan['main_subject_name']}。",
        next_action=plan["tasks"][0]["title"],
        warnings=plan["warnings"],
        plan=plan,
    )


def today(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    plan = read_json(root / "plan.json", {})
    if not plan or plan.get("plan_date") != date.today().isoformat():
        response = make_plan(raw_workspace, "daily-refresh")
        response["command"] = "today"
        return response
    return _response(
        "today",
        workspace,
        summary=f"今日共有 {len(plan['tasks'])} 个关键任务。",
        next_action=plan["tasks"][0]["title"] if plan["tasks"] else None,
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
        "actual_minutes": minutes,
        "result": result,
        "error_type": error_type,
        "note": note,
    }
    append_jsonl(root / "ledger.jsonl", row)
    if result in {"partial", "wrong"}:
        append_jsonl(
            root / "mistakes.jsonl",
            {
                "recorded_at": row["recorded_at"],
                "task_id": task_id,
                "subject_id": task.get("subject_id"),
                "topic_id": task.get("topic_id"),
                "error_type": error_type or "knowledge_gap",
                "note": note,
            },
        )
    queue = read_json(root / "review_queue.json")
    if task.get("role") == "review" and task.get("review_keys"):
        for review_key in task["review_keys"]:
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
        updated_files=[".emerald-shore/ledger.jsonl", ".emerald-shore/review_queue.json", ".emerald-shore/dashboard.md"]
        + ([".emerald-shore/mistakes.jsonl"] if result in {"partial", "wrong"} else []),
        summary=f"已记录任务结果：{result}，实际 {minutes} 分钟。",
        next_action="运行 review 查看到期复习，或继续今日下一项任务。",
    )


def checkpoint(raw_workspace: str, subject_name: str, score: float, max_score: float, minutes: int) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name)
    if max_score <= 0 or score < 0 or score > max_score or minutes <= 0:
        raise EmeraldError(
            "invalid_checkpoint",
            "检查点必须满足 0 ≤ 得分 ≤ 满分，且用时大于 0。",
            "核对得分、满分和用时后重试。",
        )
    normalized = score / max_score * float(subject["max_score"])
    entry = {
        "recorded_at": now_iso(),
        "raw_score": float(score),
        "raw_max_score": float(max_score),
        "normalized_score": round(normalized, 2),
        "minutes": int(minutes),
    }
    subject["current_score"] = round(normalized, 2)
    subject.setdefault("score_history", []).append(entry)
    atomic_write_json(root / "subjects.json", subjects)
    append_jsonl(
        root / "ledger.jsonl",
        {"type": "checkpoint", "subject_id": subject["id"], **entry},
    )
    response = make_plan(raw_workspace, "checkpoint")
    response["command"] = "checkpoint"
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
    )
    atomic_write_json(root / "sources.json", sources)
    atomic_write_json(root / "question_bank.json", questions)
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


def drill(raw_workspace: str, subject_name: str, topic_name: str | None = None) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subjects = read_json(root / "subjects.json")
    subject = _find_subject(subjects, subject_name)
    topics = read_json(root / "topics.json")
    topic = _find_topic(topics, subject["id"], topic_name) if topic_name else None
    questions = read_json(root / "question_bank.json")
    candidates = [item for item in questions if item.get("subject_id") == subject["id"]]
    if topic:
        candidates = [item for item in candidates if item.get("topic_id") == topic["id"]]
    if not candidates:
        unassigned = sum(1 for item in questions if not item.get("subject_id"))
        recovery = "先用 ingest --subject 绑定该科目的来源材料。"
        if unassigned:
            recovery += f" 当前还有 {unassigned} 道旧版未绑定来源题，可重新 ingest 其材料完成绑定。"
        raise EmeraldError("no_source_questions", f"{subject_name} 暂无可用来源题。", recovery)
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

    selected = sorted(candidates, key=order)[0]
    selected["presented_count"] = int(selected.get("presented_count", 0)) + 1
    selected["last_presented_at"] = now_iso()
    atomic_write_json(root / "question_bank.json", questions)
    sources = read_json(root / "sources.json")
    source = next((item for item in sources if item["id"] == selected["source_id"]), None)
    public_question = {
        key: selected.get(key)
        for key in ("id", "text", "subject_id", "topic_id", "locator", "source_grounded")
    }
    public_source = None
    if source:
        public_source = {
            "id": source["id"],
            "name": source["name"],
            "path": source["path"],
            "evidence_level": source["evidence_level"],
            "classification_confidence": source.get("classification_confidence", "high"),
            "match_note": source.get("match_note"),
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
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if result not in QUESTION_RESULTS:
        raise EmeraldError(
            "invalid_question_result",
            f"不支持答题结果：{result}",
            f"请选择：{', '.join(sorted(QUESTION_RESULTS))}。",
        )
    if minutes < 0 or minutes > 24 * 60:
        raise EmeraldError("invalid_minutes", "实际分钟必须在 0–1440 之间。", "核对用时后重试。")
    if error_type is not None and error_type not in ERROR_TYPES:
        raise EmeraldError(
            "invalid_error_type",
            f"不支持错因：{error_type}",
            f"请选择：{', '.join(sorted(ERROR_TYPES))}。",
        )
    questions = read_json(root / "question_bank.json")
    question = next((item for item in questions if item["id"] == question_id), None)
    if question is None:
        raise EmeraldError("question_not_found", f"未找到 question-id：{question_id}", "运行 drill 获取当前来源题。")
    attempt = {
        "recorded_at": now_iso(),
        "result": result,
        "minutes": minutes,
        "error_type": error_type,
        "note": note,
    }
    question.setdefault("attempts", []).append(attempt)
    atomic_write_json(root / "question_bank.json", questions)
    topics = read_json(root / "topics.json")
    topic = next((item for item in topics if item["id"] == question.get("topic_id")), None)
    if topic:
        observed = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}[result]
        topic["mastery"] = round(float(topic.get("mastery", 0.0)) * 0.7 + observed * 0.3, 4)
        topic["confidence"] = round(min(1.0, float(topic.get("confidence", 0.5)) + 0.05), 4)
        topic["evidence_count"] = int(topic.get("evidence_count", 0)) + 1
        topic["last_evidence_at"] = attempt["recorded_at"]
        atomic_write_json(root / "topics.json", topics)
    row = {
        "type": "question-attempt",
        "recorded_at": attempt["recorded_at"],
        "question_id": question_id,
        "subject_id": question.get("subject_id"),
        "topic_id": question.get("topic_id"),
        "actual_minutes": minutes,
        "result": result,
        "error_type": error_type,
        "note": note,
    }
    append_jsonl(root / "ledger.jsonl", row)
    if result in {"partial", "wrong"}:
        append_jsonl(
            root / "mistakes.jsonl",
            {
                "recorded_at": attempt["recorded_at"],
                "question_id": question_id,
                "subject_id": question.get("subject_id"),
                "topic_id": question.get("topic_id"),
                "error_type": error_type or "knowledge_gap",
                "note": note,
            },
        )
    queue = read_json(root / "review_queue.json")
    queue = update_review_item(
        queue,
        {
            "id": question_id,
            "review_key": f"question:{question_id}",
            "subject_id": question.get("subject_id"),
            "title": f"重做来源题 {question_id}",
        },
        "complete" if result == "correct" else "wrong",
    )
    atomic_write_json(root / "review_queue.json", queue)
    updated = [
        f"{STATE_DIR}/question_bank.json",
        f"{STATE_DIR}/ledger.jsonl",
        f"{STATE_DIR}/review_queue.json",
    ]
    if topic:
        updated.append(f"{STATE_DIR}/topics.json")
    if result in {"partial", "wrong"}:
        updated.append(f"{STATE_DIR}/mistakes.jsonl")
    next_action = (
        "先说出决定性步骤，再做一题近迁移。"
        if result == "correct"
        else "定位第一个关键错因，补最小解释，然后独立重做或做近迁移题。"
    )
    return _response(
        "attempt",
        workspace,
        updated_files=updated,
        summary=f"已记录来源题结果：{result}。",
        next_action=next_action,
        topic=topic,
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


def weekly_review(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    replanned = make_plan(raw_workspace, "weekly-review")
    plan = replanned["plan"]
    today_value = date.today()
    start = today_value - timedelta(days=6)
    ledger = read_jsonl(root / "ledger.jsonl")
    mistakes = read_jsonl(root / "mistakes.jsonl")

    def in_period(row: dict[str, Any]) -> bool:
        try:
            return start <= datetime.fromisoformat(row["recorded_at"]).date() <= today_value
        except (KeyError, ValueError):
            return False

    weekly_ledger = [row for row in ledger if in_period(row)]
    weekly_mistakes = [row for row in mistakes if in_period(row)]
    task_rows = [row for row in weekly_ledger if row.get("type") == "task"]
    adherence = None
    if task_rows:
        adherence = sum(1 for row in task_rows if row.get("result") == "complete") / len(task_rows)
    error_counts: dict[str, int] = {}
    for row in weekly_mistakes:
        key = row.get("error_type") or "knowledge_gap"
        error_counts[key] = error_counts.get(key, 0) + 1
    evidence_events = sum(1 for row in weekly_ledger if row.get("type") in {"checkpoint", "question-attempt"})
    if adherence is not None and adherence < 0.60:
        decision = "执行率低于 60%：不补旧计划；下周缩小单次任务，保留主攻并删除低价值任务。"
    elif evidence_events == 0:
        decision = "本周缺少闭卷或限时证据：下周减少输入型学习，先安排一次可判定检查点。"
    else:
        decision = "保留当前主攻，用错因和限时结果继续校准；不因单次情绪波动改动全局。"
    focus = read_json(root / "focus.json", {})
    next_action = focus.get("if_then") or "为今日第一任务运行 focus，设定时间、地点和 5 分钟启动动作。"
    review_payload = {
        "schema_version": 2,
        "generated_at": now_iso(),
        "period": {"start": start.isoformat(), "end": today_value.isoformat()},
        "adherence": adherence,
        "planned_minutes": sum(int(row.get("planned_minutes") or 0) for row in task_rows),
        "actual_minutes": sum(int(row.get("actual_minutes") or 0) for row in weekly_ledger),
        "evidence_events": evidence_events,
        "error_counts": error_counts,
        "next_main_subject": plan["main_subject_name"],
        "next_main_topic": plan.get("main_topic_name"),
        "decision": decision,
        "next_action": next_action,
    }
    atomic_write_text(root / "weekly.md", weekly_markdown(review_payload))
    return _response(
        "weekly",
        workspace,
        updated_files=list(dict.fromkeys([*replanned["updated_files"], f"{STATE_DIR}/weekly.md"])),
        summary=f"周复盘完成；下周主攻 {plan['main_subject_name']}。",
        next_action=next_action,
        warnings=replanned.get("warnings", []),
        weekly=review_payload,
        plan=plan,
    )


def review(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    queue = read_json(root / "review_queue.json")
    due = due_reviews(queue)
    return _response(
        "review",
        workspace,
        summary=f"当前有 {len(due)} 个到期复习项。",
        next_action=due[0]["label"] if due else "没有到期项；执行今日主攻任务。",
        due=due,
    )


def status(raw_workspace: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    plan = read_json(root / "plan.json", {})
    queue = read_json(root / "review_queue.json")
    ledger = read_jsonl(root / "ledger.jsonl")
    sources = read_json(root / "sources.json")
    topics = read_json(root / "topics.json")
    focus = read_json(root / "focus.json", {})
    phase = determine_phase(profile["exam_date"])
    adherence = _adherence(ledger)
    warnings = []
    if adherence is not None and adherence < 0.60:
        warnings.append("近 7 天执行率低于 60%；建议缩小任务并运行 replan，不做人格归因。")
    return _response(
        "status",
        workspace,
        summary=f"距考试 {phase['days_remaining']} 天；{len(subjects)} 门科目；{len(due_reviews(queue))} 个到期复习项。",
        next_action=plan.get("tasks", [{}])[0].get("title") if plan.get("tasks") else "添加科目并运行 plan。",
        warnings=warnings,
        profile=profile,
        phase=phase,
        subjects=subjects,
        main_subject=plan.get("main_subject_name"),
        main_topic=plan.get("main_topic_name"),
        adherence_7d=adherence,
        due_review_count=len(due_reviews(queue)),
        source_count=len(sources),
        topic_count=len(topics),
        focus=focus or None,
        ledger_count=len(ledger),
    )
