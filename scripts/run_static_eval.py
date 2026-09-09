#!/usr/bin/env python3
"""检查每个公开行为场景是否都有明确的 Skill 规则支撑。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure_utf8_stdio() -> None:
    """让中文评测结果在 Windows 管道与终端中稳定输出。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    configure_utf8_stdio()
    cases = json.loads((ROOT / "eval/cases.json").read_text(encoding="utf-8"))
    if len(cases) < 12:
        raise SystemExit("至少需要 12 个行为场景")
    cache = {}
    passed = 0
    critical_total = 0
    critical_passed = 0
    failures = []
    for case in cases:
        relative = case["reference"]
        if relative not in cache:
            cache[relative] = (ROOT / relative).read_text(encoding="utf-8")
        ok = all(marker in cache[relative] for marker in case["required_markers"])
        passed += int(ok)
        if case.get("critical"):
            critical_total += 1
            critical_passed += int(ok)
        if not ok:
            failures.append(case["id"])
    score = passed / len(cases) * 100
    report = {
        "kind": "static-contract-eval",
        "cases": len(cases),
        "passed": passed,
        "score": round(score, 1),
        "critical": f"{critical_passed}/{critical_total}",
        "failures": failures,
        "note": "这里只验证书面行为契约，不是实时模型评测。",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures and score >= 90 and critical_passed == critical_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
