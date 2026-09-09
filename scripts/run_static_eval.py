#!/usr/bin/env python3
"""Check that every published behavior scenario is backed by explicit Skill rules."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cases = json.loads((ROOT / "eval/cases.json").read_text(encoding="utf-8"))
    if len(cases) < 12:
        raise SystemExit("at least 12 behavior cases are required")
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
        "note": "This validates written behavior contracts; it is not a live-model evaluation.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures and score >= 90 and critical_passed == critical_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
