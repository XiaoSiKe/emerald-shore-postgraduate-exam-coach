"""CLI 用例编排。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import QinganError
from .materials import ingest_files, iter_material_files
from .planner import KINDS, build_plan, determine_phase, due_reviews, update_review_item
from .render import dashboard_markdown, today_markdown
from .state import (
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    ensure_unique_subject,
    initialize_workspace,
    now_iso,
    read_json,
    read_jsonl,
    require_workspace,
)

ERROR_TYPES = {"knowledge_gap", "reasoning", "procedure", "careless", "time_pressure"}
RESULTS = {"complete", "partial", "wrong", "skipped"}
EVIDENCE_LEVELS = {"user_material", "past_paper", "official", "external_aid"}


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


def init(raw_workspace: str, exam_date: str, daily_hours: float, target: str) -> dict[str, Any]:
    workspace, created = initialize_workspace(raw_workspace, exam_date, daily_hours, target)
    return _response(
        "init",
        workspace,
        updated_files=[f".qingan/{name}" for name in created],
        summary="青岸计划工作区已初始化。",
        next_action="使用 subject add 添加科目与分数基线。",
    )


def add_subject(
    raw_workspace: str,
    name: str,
    max_score: float,
    baseline: float,
    target: float,
    kind: str,
    estimated_hours: float | None,
) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    name = name.strip()
    if not name:
        raise QinganError("invalid_subject", "科目名不能为空。", "提供真实科目名后重试。")
    if kind not in KINDS:
        raise QinganError(
            "invalid_subject_kind",
            f"不支持能力类型：{kind}",
            f"请选择：{', '.join(sorted(KINDS))}。",
        )
    if max_score <= 0 or baseline < 0 or target < 0 or baseline > max_score or target > max_score:
        raise QinganError(
            "invalid_score",
            "分数必须满足 0 ≤ 当前分、目标分 ≤ 满分。",
            "核对满分、当前分和目标分后重试。",
        )
    if target < baseline:
        raise QinganError(
            "target_below_baseline",
            "目标分不能低于当前基线。",
            "提高目标分，或用最近一次 checkpoint 更新基线。",
        )
    if estimated_hours is not None and estimated_hours <= 0:
        raise QinganError("invalid_estimated_hours", "预计达标小时必须大于 0。", "移除该参数或填写正数。")
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
        "estimated_hours": float(estimated_hours) if estimated_hours is not None else None,
        "score_history": [],
        "created_at": now_iso(),
    }
    subjects.append(item)
    atomic_write_json(root / "subjects.json", subjects)
    return _response(
        "subject add",
        workspace,
        updated_files=[".qingan/subjects.json"],
        summary=f"已添加科目：{name}。",
        next_action="继续添加科目；全部添加后运行 plan。",
        subject=item,
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
    return [".qingan/plan.json", ".qingan/today.md", ".qingan/dashboard.md"]


def make_plan(raw_workspace: str, reason: str = "manual") -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    mistakes = read_jsonl(root / "mistakes.jsonl")
    queue = read_json(root / "review_queue.json")
    plan = build_plan(profile, subjects, mistakes, queue, reason)
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
        raise QinganError("invalid_minutes", "实际分钟必须在 0–1440 之间。", "核对学习时长后重试。")
    if result not in RESULTS:
        raise QinganError("invalid_result", f"不支持结果：{result}", f"请选择：{', '.join(sorted(RESULTS))}。")
    if error_type is not None and error_type not in ERROR_TYPES:
        raise QinganError(
            "invalid_error_type",
            f"不支持错因：{error_type}",
            f"请选择：{', '.join(sorted(ERROR_TYPES))}。",
        )
    plan = read_json(root / "plan.json", {})
    task = next((item for item in plan.get("tasks", []) if item.get("id") == task_id), None)
    if task is None:
        raise QinganError(
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
        updated_files=[".qingan/ledger.jsonl", ".qingan/review_queue.json", ".qingan/dashboard.md"]
        + ([".qingan/mistakes.jsonl"] if result in {"partial", "wrong"} else []),
        summary=f"已记录任务结果：{result}，实际 {minutes} 分钟。",
        next_action="运行 review 查看到期复习，或继续今日下一项任务。",
    )


def checkpoint(raw_workspace: str, subject_name: str, score: float, max_score: float, minutes: int) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    subjects = read_json(root / "subjects.json")
    subject = next((item for item in subjects if item["name"].casefold() == subject_name.casefold()), None)
    if subject is None:
        raise QinganError("subject_not_found", f"未找到科目：{subject_name}", "先使用 subject add 添加该科目。")
    if max_score <= 0 or score < 0 or score > max_score or minutes <= 0:
        raise QinganError(
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
    response["updated_files"] = list(dict.fromkeys([".qingan/subjects.json", ".qingan/ledger.jsonl", *response["updated_files"]]))
    return response


def ingest(raw_workspace: str, inputs: list[str], evidence_level: str) -> dict[str, Any]:
    workspace, root = require_workspace(raw_workspace)
    if evidence_level not in EVIDENCE_LEVELS:
        raise QinganError(
            "invalid_evidence_level",
            f"不支持证据等级：{evidence_level}",
            f"请选择：{', '.join(sorted(EVIDENCE_LEVELS))}。",
        )
    files = iter_material_files(inputs, root)
    if not files:
        raise QinganError(
            "no_supported_materials",
            "没有找到支持的材料文件。",
            "提供 PDF、DOCX、PPTX、TXT、Markdown 或 HTML 文件。",
        )
    sources = read_json(root / "sources.json")
    questions = read_json(root / "question_bank.json")
    sources, questions, added, warnings = ingest_files(files, root, sources, questions, evidence_level)
    atomic_write_json(root / "sources.json", sources)
    atomic_write_json(root / "question_bank.json", questions)
    profile = read_json(root / "profile.json")
    subjects = read_json(root / "subjects.json")
    plan = read_json(root / "plan.json", {})
    if plan:
        _write_views(root, profile, subjects, plan)
    return _response(
        "ingest",
        workspace,
        updated_files=[".qingan/sources.json", ".qingan/question_bank.json", ".qingan/materials/"],
        summary=f"已建库 {len(added)} 个新材料，提取 {sum(item['question_count'] for item in added)} 道来源题。",
        next_action="核对材料警告；随后运行 plan 或开始一次来源可追溯的闭卷训练。",
        warnings=warnings,
        added_sources=added,
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
        adherence_7d=adherence,
        due_review_count=len(due_reviews(queue)),
        source_count=len(sources),
        ledger_count=len(ledger),
    )
