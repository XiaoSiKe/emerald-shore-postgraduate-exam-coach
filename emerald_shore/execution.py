"""逐日计划快照及已结束、仍开放的任务窗口。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .state import atomic_write_json, read_json
from .target import matches_scope

HISTORY_DIR = "daily-plans"


def task_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("task_id") or row.get("id"),
        row.get("topic_id"),
        tuple(row.get("review_keys") or ()),
    )


def save_day_plan(root: Path, plan: dict[str, Any], *, replace: bool = True) -> str | None:
    stamp = plan.get("plan_date")
    if not stamp:
        return None
    stamp = date.fromisoformat(stamp).isoformat()
    relative = f"{HISTORY_DIR}/{stamp}.json"
    path = root / relative
    if not replace and path.exists():
        return None
    tasks = [
        {key: value for key, value in task.items() if key != "status"}
        for task in plan["tasks"]
    ]
    atomic_write_json(path, {
        "plan_date": stamp, "tasks": tasks, "day_context": plan.get("day_context", {}),
    })
    return relative


def execution_window(
    root: Path,
    ledger: list[dict[str, Any]],
    start: date,
    end: date,
    profile: dict[str, Any],
    subjects: list[dict[str, Any]],
) -> dict[str, Any]:
    by_subject = {row["id"]: row for row in subjects}

    def active(row: dict[str, Any]) -> bool:
        return matches_scope(row, profile, by_subject.get(row.get("subject_id")))

    logs = {}
    for row in ledger:
        if row.get("type") != "task" or not active(row):
            continue
        try:
            day = (
                date.fromisoformat(row["plan_date"]) if row.get("plan_date")
                else datetime.fromisoformat(row["recorded_at"]).astimezone().date()
            )
        except (KeyError, TypeError, ValueError):
            continue
        if start <= day <= end:
            logs[(day, task_identity(row))] = row

    snapshots = {}
    report_tasks = {}
    archived_days = set()
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        snapshot = read_json(root / HISTORY_DIR / f"{day.isoformat()}.json", {})
        if not snapshot:
            continue
        archived_days.add(day)
        for task in snapshot.get("tasks", []):
            if active(task):
                key = (day, task_identity(task))
                snapshots[key] = task
                if day < end:
                    report_tasks[key] = task

    # If a revision removes a task after it happened, its actual log still counts.
    # Replacement tasks with no log do not make today's open denominator larger.
    report_tasks.update(logs)
    finished = {key: row for key, row in report_tasks.items() if key[0] < end}
    active_day = {key: row for key, row in report_tasks.items() if key[0] == end}
    pending = sum(key[0] == end and key not in logs for key in snapshots)
    legacy_dates = {day for day, _ in logs if day not in archived_days}

    def counts(rows: dict[tuple[Any, ...], dict[str, Any]]) -> dict[str, Any]:
        return {
            "tasks": len(rows),
            "completed": sum(row.get("result") == "complete" for row in rows.values()),
            "unlogged": sum(key not in logs for key in rows),
            "planned_minutes": sum(int(row.get("planned_minutes") or 0) for row in rows.values()),
            "actual_minutes": sum(int(row.get("actual_minutes") or 0) for row in rows.values()),
        }

    total = counts(report_tasks)
    return {
        "planned_tasks": total["tasks"],
        "task_records": len(logs),
        "completed_tasks": total["completed"],
        "completion_rate": total["completed"] / total["tasks"] if total["tasks"] else None,
        "planned_minutes": total["planned_minutes"],
        "actual_task_minutes": total["actual_minutes"],
        "closed_days": {
            **counts(finished),
            "days_with_plan": sum(day < end for day in archived_days),
            "logged_only_dates": sorted(day.isoformat() for day in legacy_dates if day < end),
        },
        "today": {**counts(active_day), "pending": pending, "date": end.isoformat()},
    }
