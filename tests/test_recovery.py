import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from emerald_shore import service
from emerald_shore.errors import EmeraldError
from emerald_shore.state import append_jsonl, read_jsonl


class RecoveryTests(unittest.TestCase):
    def test_recent_plan_survives_corrupt_view_and_keeps_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = str(Path(tmp) / "study")
            service.init(work, (date.today() + timedelta(days=30)).isoformat(), 3, "测试")
            for name in ("数学", "英语"):
                service.add_subject(work, name, 150, 70, 120, "calculation", None)
            plan = service.make_plan(work, "replan", 20, True)["plan"]
            service.log_task(work, plan["tasks"][0]["id"], 12, "complete", None, "闭卷")
            root = Path(work) / ".emerald-shore"
            ledger = (root / "ledger.jsonl").read_bytes()
            bad = b'{"plan_date":'
            (root / "plan.json").write_bytes(bad)
            result = service.recover(work)
            self.assertTrue(result["recovery"]["used_today_snapshot"])
            self.assertEqual((root / result["recovery"]["preserved_plan"]).read_bytes(), bad)
            self.assertEqual(result["plan"]["day_context"]["available_minutes_override"], 20)
            self.assertEqual(len(result["plan"]["tasks"]), 1)
            self.assertEqual(service.today(work)["plan"]["tasks"][0]["status"], "complete")
            self.assertEqual((root / "ledger.jsonl").read_bytes(), ledger)

    def test_truncated_ledger_requires_compatible_backup_and_retains_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = str(Path(tmp) / "study")
            service.init(work, (date.today() + timedelta(days=30)).isoformat(), 2, "测试")
            root = Path(work) / ".emerald-shore"
            ledger = root / "ledger.jsonl"
            good = b'{"id":"one"}\n{"id":"two"}\n'
            broken = good + b'{"id":'
            ledger.write_bytes(broken)
            with self.assertRaises(EmeraldError):
                append_jsonl(ledger, {"id": "third"})
            backup = Path(tmp) / "trusted.jsonl"
            backup.write_bytes(b'{"id":"one"}\n')
            with self.assertRaises(EmeraldError) as error:
                service.recover(work, str(backup))
            self.assertEqual(error.exception.code, "ledger_backup_conflict")
            self.assertEqual(ledger.read_bytes(), broken)
            backup.write_bytes(good)
            result = service.recover(work, str(backup))
            self.assertEqual(result["restored_records"], 2)
            self.assertEqual(ledger.read_bytes(), good)
            saved = Path(work) / result["updated_files"][0]
            self.assertEqual(saved.read_bytes(), broken)
            self.assertEqual(service.recover(work, str(backup))["updated_files"], [])

    def test_append_to_complete_legacy_line_without_final_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ledger.jsonl"
            target.write_text(json.dumps({"id": "old"}))
            append_jsonl(target, {"id": "new"})
            self.assertEqual([item["id"] for item in read_jsonl(target)], ["old", "new"])
