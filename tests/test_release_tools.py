import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseToolTests(unittest.TestCase):
    def test_skill_validator(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_skill.py"), str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_static_eval(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_static_eval.py")],
            check=False,
            capture_output=True,
            text=True,
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
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(destination.with_suffix(".zip.sha256").exists())
            with zipfile.ZipFile(destination) as archive:
                roots = {name.split("/", 1)[0] for name in archive.namelist()}
                self.assertEqual(roots, {"qingan-kaoyan-coach"})
                self.assertIn("qingan-kaoyan-coach/SKILL.md", archive.namelist())
                self.assertFalse(any("tests/" in name or "eval/" in name for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
