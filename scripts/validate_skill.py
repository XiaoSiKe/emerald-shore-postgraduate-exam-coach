#!/usr/bin/env python3
"""在不依赖第三方包的情况下校验可移植 Agent Skill。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_NAME = "emerald-shore-postgraduate-exam-coach"


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md 必须以 YAML frontmatter 开头")
    try:
        _, raw, _ = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter 没有闭合") from exc
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
        "emerald.py",
        "emerald_shore/__init__.py",
        "README.md",
        "README.zh-CN.md",
        "references/coach-orchestration.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "sources.lock.json",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"缺少必需文件：{relative}")
    skill_path = root / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        try:
            metadata = frontmatter(text)
            name = metadata.get("name", "")
            description = metadata.get("description", "")
            if not NAME_RE.fullmatch(name) or len(name) > 64:
                errors.append("frontmatter name 必须不超过 64 个小写字母、数字或连字符")
            if name != EXPECTED_NAME:
                errors.append(f"frontmatter name 必须为 {EXPECTED_NAME}")
            if not description:
                errors.append("frontmatter description 为必填项")
        except ValueError as exc:
            errors.append(str(exc))
        if "references/coach-orchestration.md" not in text:
            errors.append("SKILL.md 没有路由到教练编排协议")
    openai_yaml = root / "agents/openai.yaml"
    if openai_yaml.exists():
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        for marker in ("display_name:", "short_description:", "default_prompt:", "$emerald-shore-postgraduate-exam-coach"):
            if marker not in yaml_text:
                errors.append(f"agents/openai.yaml 缺少 {marker}")
    for relative in ("SKILL.md", "README.md", "README.zh-CN.md", "agents/openai.yaml"):
        path = root / relative
        if path.exists():
            val = path.read_text(encoding="utf-8")
            if "qingan-kaoyan" in val.casefold() or "python qingan.py" in val.casefold():
                errors.append(f"{relative} 中仍有旧拼音公开标识")
    for relative in ("README.md", "CONTRIBUTING.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"):
        path = root / relative
        if path.exists() and not re.search(r"[\u4e00-\u9fff]", path.read_text(encoding="utf-8")):
            errors.append(f"{relative} 应以中文作为用户可见主语言")
    readme_path = root / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        for marker in ("这是一个 **Agent Skill**", "不是独立 App", "references/coach-orchestration.md"):
            if marker not in readme_text:
                errors.append(f"README.md 缺少 Skill 定位标记：{marker}")
    for markdown in root.rglob("*.md"):
        if any(part in {".git", "dist"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        if "TODO" in text or "PLACEHOLDER" in text:
            errors.append(f"{markdown.relative_to(root)} 中存在未完成占位符")
        for target in LINK_RE.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (markdown.parent / target).resolve().exists():
                errors.append(f"{markdown.relative_to(root)} 中存在失效本地链接：{target}")
    lock_path = root / "sources.lock.json"
    if lock_path.exists():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            for source in lock.get("sources", []):
                if not COMMIT_RE.fullmatch(source.get("commit", "")):
                    errors.append(f"{source.get('repo')} 的 commit 无效")
                if source.get("license") is None and source.get("policy") != "concept-only-no-copy":
                    errors.append(f"无许可证来源缺少禁止复制策略：{source.get('repo')}")
        except json.JSONDecodeError as exc:
            errors.append(f"sources.lock.json 无效：{exc}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        return 1
    print("Skill 校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
