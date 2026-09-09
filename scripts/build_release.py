#!/usr/bin/env python3
"""Build a deterministic, installable Skill ZIP and SHA-256 checksum."""

from __future__ import annotations

import argparse
import hashlib
import re
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = "emerald-shore-postgraduate-exam-coach"
VERSION_MATCH = re.search(
    r'^__version__\s*=\s*"([^"]+)"',
    (ROOT / "emerald_shore/__init__.py").read_text(encoding="utf-8"),
    re.MULTILINE,
)
if VERSION_MATCH is None:
    raise RuntimeError("emerald_shore/__init__.py does not define __version__")
VERSION = VERSION_MATCH.group(1)
TOP_LEVEL = (
    "SKILL.md",
    "agents",
    "references",
    "emerald.py",
    "emerald_shore",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "docs",
    "sources.lock.json",
)
EXCLUDED_NAMES = {"__pycache__", ".DS_Store"}


def release_files():
    files = []
    for relative in TOP_LEVEL:
        path = ROOT / relative
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                child
                for child in path.rglob("*")
                if child.is_file() and not any(part in EXCLUDED_NAMES for part in child.parts) and child.suffix != ".pyc"
            )
    return sorted(set(files), key=lambda path: path.relative_to(ROOT).as_posix())


def build(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files():
            arcname = f"{FOLDER}/{path.relative_to(ROOT).as_posix()}"
            info = zipfile.ZipInfo(arcname, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + ".sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8"
    )
    return digest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default=f"dist/{FOLDER}-v{VERSION}.zip")
    parser.add_argument("--check", action="store_true", help="Build twice and verify byte-for-byte reproducibility")
    args = parser.parse_args(argv)
    destination = (ROOT / args.output).resolve()
    digest = build(destination)
    if args.check:
        with tempfile.TemporaryDirectory(prefix="emerald-shore-release-") as temp:
            second = Path(temp) / destination.name
            second_digest = build(second)
        if digest != second_digest:
            raise SystemExit("release build is not deterministic")
    print(f"{destination} ({len(release_files())} files) sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
