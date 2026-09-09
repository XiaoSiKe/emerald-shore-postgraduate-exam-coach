import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from emerald_shore.errors import EmeraldError
from emerald_shore.service import (
    add_subject,
    add_topic,
    checkpoint,
    drill,
    efficiency_report,
    ingest,
    init,
    log_task,
    make_plan,
    record_attempt,
)


class EfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "study"
        init(str(self.workspace), (date.today() + timedelta(days=70)).isoformat(), 5, "考研初试")
        add_subject(str(self.workspace), "数学", 150, 60, 110, "calculation", None)
        add_topic(str(self.workspace), "数学", "微积分", 3, 0.3, 0.8, None)

    def tearDown(self):
        self.temp.cleanup()

    def add_question(self) -> str:
        material = self.root / "paper.md"
        material.write_text("第1题 求极限。", encoding="utf-8")
        ingest(str(self.workspace), [str(material)], "past_paper", "数学", "微积分")
        return drill(str(self.workspace), "数学", "微积分")["question"]["id"]

    def test_insufficient_evidence_does_not_invent_score(self):
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["principle"], "multi-dimensional-no-composite-score")
        self.assertEqual(report["diagnosis"], "insufficient_evidence")
        self.assertNotIn("overall_score", report)
        self.assertTrue((self.workspace / ".emerald-shore/efficiency.md").exists())

    def test_low_execution_is_load_mismatch_not_personality_judgment(self):
        task = make_plan(str(self.workspace))["plan"]["tasks"][0]
        log_task(str(self.workspace), task["id"], 0, "skipped", None, "临时实验课")
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "load_mismatch")
        self.assertIn("不是不够努力", report["explanation"])

    def test_completed_task_without_verified_output_is_input_heavy(self):
        task = make_plan(str(self.workspace))["plan"]["tasks"][0]
        log_task(str(self.workspace), task["id"], 45, "complete", None, "只看了讲义")
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "input_heavy")

    def test_attempt_outcomes_find_accuracy_gap(self):
        question_id = self.add_question()
        for _ in range(3):
            record_attempt(str(self.workspace), question_id, "wrong", 10, "reasoning", "方法选择错误")
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "accuracy_gap")
        self.assertEqual(report["outcomes"]["wrong"], 3)
        self.assertEqual(report["outcomes"]["correct_rate"], 0)

    def test_repeated_error_is_reported_before_checkpoint_gap(self):
        question_id = self.add_question()
        for _ in range(2):
            record_attempt(str(self.workspace), question_id, "partial", 10, "procedure", "步骤不稳定")
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "recurring_error")
        self.assertEqual(report["errors"]["recurring_types"], ["procedure"])

    def test_verified_practice_without_checkpoint_requests_calibration(self):
        question_id = self.add_question()
        record_attempt(str(self.workspace), question_id, "correct", 8, None, "独立完成")
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "checkpoint_missing")

    def test_complete_loop_reports_checkpoint_change_without_composite_score(self):
        task = make_plan(str(self.workspace))["plan"]["tasks"][0]
        log_task(str(self.workspace), task["id"], 45, "complete", None, "闭卷完成")
        question_id = self.add_question()
        record_attempt(str(self.workspace), question_id, "correct", 8, None, "独立完成")
        checkpoint(str(self.workspace), "数学", 75, 150, 120)
        checkpoint(str(self.workspace), "数学", 90, 150, 120)
        report = efficiency_report(str(self.workspace))["efficiency"]
        self.assertEqual(report["diagnosis"], "evidence_loop_stable")
        self.assertEqual(report["checkpoints"]["changes"][0]["delta_points"], 15)
        self.assertNotIn("overall_score", report)

    def test_efficiency_window_is_bounded(self):
        with self.assertRaises(EmeraldError) as caught:
            efficiency_report(str(self.workspace), 0)
        self.assertEqual(caught.exception.code, "invalid_efficiency_window")


if __name__ == "__main__":
    unittest.main()
