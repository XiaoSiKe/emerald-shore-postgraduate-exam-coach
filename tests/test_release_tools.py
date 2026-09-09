import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseToolTests(unittest.TestCase):
    def test_primary_documentation_is_chinese_and_skill_first(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("# 🌊 青岸计划·考研冲刺教练", readme)
        self.assertIn("一万年太久，只争朝夕！", readme)
        self.assertIn("这是一个 **Agent Skill**", readme)
        self.assertIn("不是独立 App", readme)
        self.assertIn("## 🧩 八大系统", readme)
        self.assertIn("cxs885187-create/--skill", readme)
        self.assertIn("references/coach-orchestration.md", readme)

    def test_cli_help_is_chinese_and_identifiers_stay_stable(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "emerald.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("考研突击冲刺 Agent Skill 的本地证据引擎", result.stdout)
        self.assertIn("subject", result.stdout)
        self.assertIn("topic", result.stdout)
        self.assertIn("profile", result.stdout)
        self.assertIn("routine", result.stdout)

    def test_skill_validator(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_skill.py"), str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_static_eval(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_static_eval.py")],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["score"], 90)
        self.assertEqual(payload["failures"], [])

    def test_release_has_one_root_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skill.zip"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/build_release.py"), str(destination), "--check"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(destination.with_suffix(".zip.sha256").exists())
            with zipfile.ZipFile(destination) as archive:
                roots = {name.split("/", 1)[0] for name in archive.namelist()}
                self.assertEqual(roots, {"emerald-shore-postgraduate-exam-coach"})
                self.assertIn("emerald-shore-postgraduate-exam-coach/SKILL.md", archive.namelist())
                self.assertIn(
                    "emerald-shore-postgraduate-exam-coach/references/coach-orchestration.md",
                    archive.namelist(),
                )
                self.assertIn(
                    "emerald-shore-postgraduate-exam-coach/references/campus-life-system.md",
                    archive.namelist(),
                )
                self.assertIn(
                    "emerald-shore-postgraduate-exam-coach/references/course-evidence-system.md",
                    archive.namelist(),
                )
                self.assertFalse(any("tests/" in name or "eval/" in name for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
