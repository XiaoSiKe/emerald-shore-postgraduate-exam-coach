"""学习工作区状态、schema 迁移、校验与原子写入。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .errors import EmeraldError

SCHEMA_VERSION = 2
STATE_DIR = ".emerald-shore"
LEGACY_STATE_DIR = ".qingan"

JSON_DEFAULTS = {
    "subjects.json": [],
    "topics.json": [],
    "plan.json": {},
    "focus.json": {},
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
        raise EmeraldError(
            "state_file_missing",
            f"状态文件不存在：{path.name}",
            "重新运行 init，或从备份恢复该文件。",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EmeraldError(
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
            raise EmeraldError(
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
        legacy = workspace / LEGACY_STATE_DIR
        if legacy.is_dir():
            raise EmeraldError(
                "legacy_workspace",
                f"发现 V0.1 工作区：{legacy}",
                "运行 emerald.py migrate WORKSPACE；旧目录会保留为只读回退副本。",
            )
        raise EmeraldError(
            "not_initialized",
            f"{workspace} 尚未初始化青岸计划。",
            "先运行 emerald.py init WORKSPACE --exam-date DATE --daily-hours HOURS。",
        )
    profile = read_json(root / "profile.json")
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise EmeraldError(
            "unsupported_schema",
            f"不支持 schema_version={profile.get('schema_version')}。",
            "使用与该工作区匹配的版本，或先按迁移文档升级。",
        )
    return workspace, root


def initialize_workspace(
    raw_workspace: str | os.PathLike[str],
    exam_date: str,
    daily_hours: float,
    target: str = "全国硕士研究生招生考试初试",
) -> tuple[Path, list[str]]:
    workspace = workspace_path(raw_workspace)
    try:
        parsed_date = date.fromisoformat(exam_date)
    except ValueError as exc:
        raise EmeraldError(
            "invalid_exam_date",
            "考试日期必须使用 YYYY-MM-DD。",
            "例如：--exam-date 2026-12-20。",
        ) from exc
    if parsed_date <= date.today():
        raise EmeraldError(
            "exam_date_not_future",
            "考试日期必须晚于今天。",
            "核对考试年份和日期后重新运行 init。",
        )
    if daily_hours <= 0 or daily_hours > 24:
        raise EmeraldError(
            "invalid_daily_hours",
            "每日可用小时必须大于 0 且不超过 24。",
            "请填写现实可持续的每日学习小时数。",
        )
    root = state_path(workspace)
    if root.exists():
        raise EmeraldError(
            "already_initialized",
            f"{workspace} 已存在青岸计划状态。",
            "使用 status 查看，或先备份并移走 .emerald-shore 后重新初始化。",
        )
    workspace.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=".emerald-shore-init-", dir=str(workspace)))
    profile = {
        "schema_version": SCHEMA_VERSION,
        "product_id": "emerald-shore-postgraduate-exam-coach",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "exam_date": parsed_date.isoformat(),
        "daily_hours": round(float(daily_hours), 2),
        "target": target.strip() or "全国硕士研究生招生考试初试",
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


def migrate_legacy_workspace(raw_workspace: str | os.PathLike[str]) -> tuple[Path, list[str]]:
    workspace = workspace_path(raw_workspace)
    legacy = workspace / LEGACY_STATE_DIR
    root = state_path(workspace)
    if root.exists():
        raise EmeraldError(
            "already_migrated",
            f"{root} 已存在。",
            "使用 status 查看新工作区；不要重复迁移。",
        )
    if not legacy.is_dir():
        raise EmeraldError(
            "legacy_workspace_missing",
            f"没有找到 {legacy}。",
            "旧用户应指定包含 .qingan 的学习工作区；新用户直接运行 init。",
        )
    legacy_profile = read_json(legacy / "profile.json")
    if legacy_profile.get("schema_version") != 1:
        raise EmeraldError(
            "unsupported_legacy_schema",
            f"只支持从 schema 1 迁移，当前为 {legacy_profile.get('schema_version')}。",
            "保留旧目录并提交脱敏后的 profile.json 版本信息。",
        )
    workspace.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=".emerald-shore-migrate-", dir=str(workspace)))
    try:
        shutil.copytree(legacy, temp_root, dirs_exist_ok=True)
        profile = read_json(temp_root / "profile.json")
        profile.update(
            {
                "schema_version": SCHEMA_VERSION,
                "product_id": "emerald-shore-postgraduate-exam-coach",
                "migrated_from": LEGACY_STATE_DIR,
                "migrated_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        atomic_write_json(temp_root / "profile.json", profile)
        for name, value in JSON_DEFAULTS.items():
            if not (temp_root / name).exists():
                atomic_write_json(temp_root / name, value)
        plan_path = temp_root / "plan.json"
        plan = read_json(plan_path, {})
        if plan:
            plan["schema_version"] = SCHEMA_VERSION
            atomic_write_json(plan_path, plan)
        sources_path = temp_root / "sources.json"
        sources = read_json(sources_path, [])
        for source in sources:
            derived = source.get("derived_path")
            if derived:
                source["derived_path"] = str(root / "materials" / Path(derived).name)
        atomic_write_json(sources_path, sources)
        for name in JSONL_FILES:
            if not (temp_root / name).exists():
                atomic_write_text(temp_root / name, "")
        (temp_root / "materials").mkdir(exist_ok=True)
        os.replace(temp_root, root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    created = [STATE_DIR, f"preserved:{LEGACY_STATE_DIR}"]
    return workspace, created


def update_profile(root: Path, changes: dict[str, Any]) -> dict[str, Any]:
    profile = read_json(root / "profile.json")
    profile.update(changes)
    profile["updated_at"] = now_iso()
    atomic_write_json(root / "profile.json", profile)
    return profile


def ensure_unique_subject(subjects: Iterable[dict[str, Any]], name: str) -> None:
    if any(item.get("name", "").casefold() == name.casefold() for item in subjects):
        raise EmeraldError(
            "duplicate_subject",
            f"科目已存在：{name}",
            "换一个科目名，或使用 checkpoint 更新已有科目的成绩。",
        )
