#!/usr/bin/env python3
"""Validate the portable Agent Skill package without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        _, raw, _ = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc
    values = {}
    for line in raw.strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def validate(root: Path) -> list[str]:
    errors = []
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "qingan.py",
        "qingan/__init__.py",
        "README.md",
        "README.zh-CN.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "sources.lock.json",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")
    skill_path = root / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        try:
            metadata = frontmatter(text)
            name = metadata.get("name", "")
            description = metadata.get("description", "")
            if not NAME_RE.fullmatch(name) or len(name) > 64:
                errors.append("frontmatter name must be <=64 lowercase letters, digits, and hyphens")
            if not description:
                errors.append("frontmatter description is required")
        except ValueError as exc:
            errors.append(str(exc))
    openai_yaml = root / "agents/openai.yaml"
    if openai_yaml.exists():
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        for marker in ("display_name:", "short_description:", "default_prompt:", "$qingan-kaoyan-coach"):
            if marker not in yaml_text:
                errors.append(f"agents/openai.yaml missing {marker}")
    for markdown in root.rglob("*.md"):
        if any(part in {".git", "dist"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        if "TODO" in text or "PLACEHOLDER" in text:
            errors.append(f"unfinished placeholder in {markdown.relative_to(root)}")
        for target in LINK_RE.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (markdown.parent / target).resolve().exists():
                errors.append(f"broken local link in {markdown.relative_to(root)}: {target}")
    lock_path = root / "sources.lock.json"
    if lock_path.exists():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            for source in lock.get("sources", []):
                if not COMMIT_RE.fullmatch(source.get("commit", "")):
                    errors.append(f"invalid commit for {source.get('repo')}")
                if source.get("license") is None and source.get("policy") != "concept-only-no-copy":
                    errors.append(f"unlicensed source lacks no-copy policy: {source.get('repo')}")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid sources.lock.json: {exc}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Skill validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
