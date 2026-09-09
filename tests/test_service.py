import json
import io
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from qingan.errors import QinganError
from qingan.cli import emit_json
from qingan.service import add_subject, checkpoint, init, log_task, make_plan, status
from qingan.state import read_json, read_jsonl

ROOT = Path(__file__).resolve().parents[1]


class ServiceFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "study"
        self.exam_date = (date.today() + timedelta(days=80)).isoformat()
        init(str(self.workspace), self.exam_date, 6, "测试目标")
        add_subject(str(self.workspace), "数学", 150, 60, 110, "calculation", None)
        add_subject(str(self.workspace), "英语", 100, 55, 70, "language", None)
        add_subject(str(self.workspace), "政治", 100, 50, 70, "memory", None)
        add_subject(str(self.workspace), "专业课", 150, 80, 120, "understanding", None)

    def tearDown(self):
        self.temp.cleanup()

    def test_four_subject_flow_and_checkpoint_replan(self):
        first = make_plan(str(self.workspace))
        self.assertEqual(len(first["plan"]["ranked_subjects"]), 4)
        self.assertLessEqual(len(first["plan"]["tasks"]), 3)
        task_ids = [task["id"] for task in first["plan"]["tasks"]]
        second = make_plan(str(self.workspace))
        self.assertEqual(task_ids, [task["id"] for task in second["plan"]["tasks"]])
        result = checkpoint(str(self.workspace), "数学", 90, 150, 180)
        self.assertEqual(result["command"], "checkpoint")
        subjects = read_json(self.workspace / ".qingan/subjects.json")
        math = next(item for item in subjects if item["name"] == "数学")
        self.assertEqual(math["current_score"], 90)
        self.assertEqual(len(math["score_history"]), 1)

    def test_wrong_result_updates_ledgers_and_review(self):
        plan = make_plan(str(self.workspace))["plan"]
        main = next(task for task in plan["tasks"] if task["role"] == "main")
        result = log_task(str(self.workspace), main["id"], 45, "wrong", "reasoning", "方法选择错误")
        self.assertTrue(result["ok"])
        mistakes = read_jsonl(self.workspace / ".qingan/mistakes.jsonl")
        self.assertEqual(mistakes[0]["error_type"], "reasoning")
        queue = read_json(self.workspace / ".qingan/review_queue.json")
        self.assertEqual(queue[0]["status"], "review-needed")
        self.assertEqual(queue[0]["key"], f"subject:{main['subject_id']}")

    def test_combined_review_task_advances_existing_items(self):
        first_plan = make_plan(str(self.workspace))["plan"]
        main = next(task for task in first_plan["tasks"] if task["role"] == "main")
        log_task(str(self.workspace), main["id"], 30, "wrong", "knowledge_gap", "首次错误")
        queue_path = self.workspace / ".qingan/review_queue.json"
        queue = read_json(queue_path)
        queue[0]["next_due"] = date.today().isoformat()
        queue_path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        review_plan = make_plan(str(self.workspace), "replan")["plan"]
        review_task = next(task for task in review_plan["tasks"] if task["role"] == "review")
        log_task(str(self.workspace), review_task["id"], 20, "complete", None, "闭卷通过")
        updated = read_json(queue_path)
        self.assertEqual(len(updated), 1)
        self.assertGreater(updated[0]["next_due"], date.today().isoformat())
        self.assertEqual(updated[0]["last_result"], "complete")

    def test_corrupt_state_is_preserved_and_reported(self):
        profile = self.workspace / ".qingan/profile.json"
        profile.write_text("{broken", encoding="utf-8")
        with self.assertRaises(QinganError) as caught:
            status(str(self.workspace))
        self.assertEqual(caught.exception.code, "corrupt_state")
        self.assertEqual(profile.read_text(encoding="utf-8"), "{broken")

    def test_cli_success_and_error_are_json(self):
        command = [sys.executable, str(ROOT / "qingan.py"), "status", str(self.workspace)]
        success = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertTrue(json.loads(success.stdout)["ok"])
        failure = subprocess.run(
            [sys.executable, str(ROOT / "qingan.py"), "today", str(Path(self.temp.name) / "missing")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(failure.returncode, 2)
        payload = json.loads(failure.stderr)
        self.assertEqual(payload["code"], "not_initialized")
        self.assertIn("recovery", payload)


class ValidationTests(unittest.TestCase):
    def test_json_output_falls_back_for_ascii_stream(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="ascii")
        emit_json({"ok": True, "summary": "青岸计划"}, stream)
        stream.flush()
        payload = json.loads(buffer.getvalue().decode("ascii"))
        self.assertEqual(payload["summary"], "青岸计划")

    def test_invalid_init_values(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(QinganError) as caught:
                init(str(Path(temp) / "bad"), "not-a-date", 4, "目标")
            self.assertEqual(caught.exception.code, "invalid_exam_date")
            with self.assertRaises(QinganError) as caught:
                init(str(Path(temp) / "bad2"), (date.today() + timedelta(days=4)).isoformat(), -1, "目标")
            self.assertEqual(caught.exception.code, "invalid_daily_hours")


if __name__ == "__main__":
    unittest.main()
