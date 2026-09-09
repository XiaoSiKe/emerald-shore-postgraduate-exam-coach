"""工作区状态、校验与原子写入。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .errors import QinganError

SCHEMA_VERSION = 1
STATE_DIR = ".qingan"

JSON_DEFAULTS = {
    "subjects.json": [],
    "plan.json": {},
    "review_queue.json": [],
    "sources.json": [],
    "question_bank.json": [],
}
JSONL_FILES = ("ledger.jsonl", "mistakes.jsonl")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def workspace_path(raw: str | os.PathLike[str]) -> Path:
    return Path(raw).expanduser().resolve()


def state_path(workspace: Path) -> Path:
    return workspace / STATE_DIR


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    line = json.dumps(value, ensure_ascii=False, sort_keys=True)
    atomic_write_text(path, existing + line + "\n")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise QinganError(
            "state_file_missing",
            f"状态文件不存在：{path.name}",
            "重新运行 init，或从备份恢复该文件。",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QinganError(
            "corrupt_state",
            f"状态文件无法解析：{path.name}",
            "不要覆盖原文件；先从备份恢复，或移走损坏文件后重新初始化。",
            {"error": str(exc)},
        ) from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise QinganError(
                "corrupt_state",
                f"状态日志无法解析：{path.name} 第 {line_number} 行",
                "保留损坏日志并从最近备份恢复，或删除该行后重试。",
                {"error": str(exc)},
            ) from exc
    return rows


def require_workspace(raw: str | os.PathLike[str]) -> tuple[Path, Path]:
    workspace = workspace_path(raw)
    root = state_path(workspace)
    if not root.is_dir():
        raise QinganError(
            "not_initialized",
            f"{workspace} 尚未初始化青岸计划。",
            "先运行 qingan.py init WORKSPACE --exam-date DATE --daily-hours HOURS。",
        )
    profile = read_json(root / "profile.json")
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise QinganError(
            "unsupported_schema",
            f"不支持 schema_version={profile.get('schema_version')}。",
            "使用与该工作区匹配的版本，或先按迁移文档升级。",
        )
    return workspace, root


def initialize_workspace(
    raw_workspace: str | os.PathLike[str],
    exam_date: str,
    daily_hours: float,
    target: str = "考研初试",
) -> tuple[Path, list[str]]:
    workspace = workspace_path(raw_workspace)
    try:
        parsed_date = date.fromisoformat(exam_date)
    except ValueError as exc:
        raise QinganError(
            "invalid_exam_date",
            "考试日期必须使用 YYYY-MM-DD。",
            "例如：--exam-date 2026-12-20。",
        ) from exc
    if parsed_date <= date.today():
        raise QinganError(
            "exam_date_not_future",
            "考试日期必须晚于今天。",
            "核对考试年份和日期后重新运行 init。",
        )
    if daily_hours <= 0 or daily_hours > 24:
        raise QinganError(
            "invalid_daily_hours",
            "每日可用小时必须大于 0 且不超过 24。",
            "请填写现实可持续的每日学习小时数。",
        )
    root = state_path(workspace)
    if root.exists():
        raise QinganError(
            "already_initialized",
            f"{workspace} 已存在青岸计划状态。",
            "使用 status 查看，或先备份并移走 .qingan 后重新初始化。",
        )
    workspace.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=".qingan-init-", dir=str(workspace)))
    profile = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "exam_date": parsed_date.isoformat(),
        "daily_hours": round(float(daily_hours), 2),
        "target": target.strip() or "考研初试",
        "buffer_ratio": 0.15,
        "language": "zh-CN",
    }
    try:
        atomic_write_json(temp_root / "profile.json", profile)
        for name, value in JSON_DEFAULTS.items():
            atomic_write_json(temp_root / name, value)
        for name in JSONL_FILES:
            atomic_write_text(temp_root / name, "")
        (temp_root / "materials").mkdir()
        os.replace(temp_root, root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    created = ["profile.json", *JSON_DEFAULTS.keys(), *JSONL_FILES, "materials/"]
    return workspace, created


def update_profile(root: Path, changes: dict[str, Any]) -> dict[str, Any]:
    profile = read_json(root / "profile.json")
    profile.update(changes)
    profile["updated_at"] = now_iso()
    atomic_write_json(root / "profile.json", profile)
    return profile


def ensure_unique_subject(subjects: Iterable[dict[str, Any]], name: str) -> None:
    if any(item.get("name", "").casefold() == name.casefold() for item in subjects):
        raise QinganError(
            "duplicate_subject",
            f"科目已存在：{name}",
            "换一个科目名，或使用 checkpoint 更新已有科目的成绩。",
        )
