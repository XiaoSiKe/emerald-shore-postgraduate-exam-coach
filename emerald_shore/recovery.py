"""Verify and preserve damaged files before replacing testable state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import EmeraldError
from .state import atomic_write_bytes


def preserve_original(root: Path, name: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    relative = f"recovery/{name}.{digest}.bak"
    path = root / relative
    if path.exists():
        if path.read_bytes() != content:
            raise EmeraldError("recovery_backup_conflict", "恢复备份内容冲突。", "核对备份目录后重试。")
    else:
        atomic_write_bytes(path, content)
    return relative


def ledger_rows(data: bytes, *, allow_truncated_tail: bool = False) -> list[dict[str, Any]]:
    rows = []
    lines = data.split(b"\n")
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            if allow_truncated_tail and index == len(lines) - 1 and not data.endswith(b"\n"):
                break
            raise EmeraldError(
                "invalid_recovery_ledger", f"第 {index + 1} 行无法无损解析。",
                "核对完整备份；中间坏行或带换行的坏行需要人工核对。",
            ) from exc
        if not isinstance(row, dict):
            raise EmeraldError("invalid_recovery_ledger", f"第 {index + 1} 行不是记录对象。", "核对完整备份。")
        rows.append(row)
    return rows


def restore_ledger(root: Path, backup: Path) -> tuple[list[str], int]:
    destination = root / "ledger.jsonl"
    if not backup.is_file() or backup.resolve() == destination.resolve():
        raise EmeraldError("invalid_ledger_backup", "需要独立的、已核验的账本备份。", "提供备份的实际路径。")
    trusted = backup.read_bytes()
    full = ledger_rows(trusted)
    original = destination.read_bytes() if destination.exists() else None
    prefix = ledger_rows(original, allow_truncated_tail=True) if original is not None else []
    if prefix != full[:len(prefix)]:
        raise EmeraldError(
            "ledger_backup_conflict", "备份与现有账本的有效记录不兼容。",
            "提供包含所有可确认记录且顺序相同的完整备份。",
        )
    if original == trusted:
        return [], len(full)
    paths = [preserve_original(root, "ledger.jsonl", original)] if original is not None else []
    atomic_write_bytes(destination, trusted)
    return paths + ["ledger.jsonl"], len(full)
