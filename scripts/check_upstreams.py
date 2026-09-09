#!/usr/bin/env python3
"""只读检查上游默认分支变化，不修改仓库。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def latest_commit(repo: str, path: str | None = None) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in repo.split("/"))
    query = "?per_page=1"
    if path:
        query += "&path=" + urllib.parse.quote(path, safe="/")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{encoded}/commits{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "emerald-shore-upstream-check/0.2",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return payload[0]["sha"]


def main() -> int:
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    report = {"checked_from": lock.get("checked_at"), "sources": [], "errors": []}
    for source in lock["sources"]:
        try:
            latest = latest_commit(source["repo"], source.get("path"))
            report["sources"].append(
                {
                    "repo": source["repo"],
                    "locked": source["commit"],
                    "latest": latest,
                    "changed": latest != source["commit"],
                    "policy": source.get("policy", "license-review-required"),
                }
            )
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError) as exc:
            report["errors"].append({"repo": source["repo"], "error": str(exc)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
