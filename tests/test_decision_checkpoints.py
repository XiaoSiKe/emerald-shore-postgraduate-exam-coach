import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


ENGINE = Path(__file__).resolve().parents[1] / "emerald.py"


class DecisionCheckpointCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.study = self.directory / "学 习"
        self.state = self.study / ".emerald-shore"
        exam = (date.today() + timedelta(days=60)).isoformat()
        self.call("init", "--exam-date", exam, "--daily-hours", "4")
        for name in ("数学", "英语", "政治"):
            self.call("subject", "add", "--name", name, "--max-score", "150",
                      "--baseline", "60", "--target", "100", "--kind", "calculation")

    def call(self, command, *args):
        if command in {"subject", "profile"}:
            command_args = [command, args[0], str(self.study), *args[1:]]
        else:
            command_args = [command, str(self.study), *args]
        result = subprocess.run([sys.executable, str(ENGINE), *command_args],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_today_reports_task_and_accepts_temporary_rest(self):
        plan = self.call("replan", "--available-minutes", "4")["plan"]
        self.assertEqual([task["planned_minutes"] for task in plan["tasks"]], [1, 1, 1])
        self.call("log", "--task-id", plan["tasks"][0]["id"], "--minutes", "1", "--result", "complete")
        today = self.call("today")
        self.assertEqual(today["plan"]["tasks"][0]["status"], "complete")
        self.assertEqual(today["next_action"], today["plan"]["tasks"][1]["title"])
        rest = self.call("replan", "--available-minutes", "0")
        self.assertEqual(rest["plan"]["tasks"], [])
        self.assertEqual(self.call("replan")["plan"]["daily_capacity_minutes"], 0)
        previous = rest["plan"]
        previous["plan_date"] = (date.today() - timedelta(days=1)).isoformat()
        (self.state / "plan.json").write_text(json.dumps(previous), encoding="utf-8")
        self.assertEqual(self.call("today")["plan"]["daily_capacity_minutes"], 204)

    def test_only_comparable_full_length_checkpoints_affect_trend(self):
        def check(score, maximum, minutes, *flags):
            return self.call("checkpoint", "--subject", "数学", "--score", str(score),
                             "--max-score", str(maximum), "--minutes", str(minutes), *flags)

        check(72, 150, 120, "--series", "A")
        check(30, 30, 20)
        check(120, 150, 25, "--scope", "partial")
        subjects = json.loads((self.state / "subjects.json").read_text(encoding="utf-8"))
        self.assertEqual(subjects[0]["current_score"], 72)
        check(99, 150, 90, "--series", "A")
        check(84, 150, 120, "--series", "B")
        check(84, 150, 120, "--series", "A")
        trends = self.call("efficiency")["efficiency"]["checkpoints"]["changes"]
        self.assertEqual([(trend["series"], trend["delta_points"]) for trend in trends],
                         [("A", 12)])

    def test_drill_hides_solutions_from_new_and_previous_indexes(self):
        paper = self.directory / "练习.md"
        paper.write_text("第1题 求极限。\n【解析】内嵌答案\n第2题 计算积分。\n"
                         "## 参考答案\n1. 集中答案\n2. 其他答案\n", encoding="utf-8")
        self.call("ingest", str(paper), "--subject", "数学")
        bank_file = self.state / "question_bank.json"
        bank = json.loads(bank_file.read_text(encoding="utf-8"))
        self.assertEqual(len(bank), 2)
        for question in bank:
            self.assertNotIn("答案", question["text"])
            question["text"] += " 参考答案：旧索引里的答案"
        bank_file.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
        for _ in range(2):
            picked = self.call("drill", "--subject", "数学")
            self.assertNotIn("答案", picked["question"]["text"])
            self.assertIsNotNone(picked["source"]["locator"])

    def test_goals_keep_floor_risk_ahead_of_large_subject_gap(self):
        action = self.call("profile", "goals", "--total-target", "280",
                           "--floor", "英语", "75", "--floor", "数学", "55",
                           "--basis", "虚构演练")
        self.assertEqual(action["plan"]["main_subject_name"], "英语")
        for score in ("70", "79"):
            self.call("checkpoint", "--subject", "英语", "--score", score, "--max-score", "150",
                      "--minutes", "120", "--scope", "full", "--series", "同系列")
        plan = self.call("today")["plan"]
        assessment = plan["goal_assessment"]
        self.assertEqual(plan["main_subject_name"], "英语")
        self.assertEqual(assessment["main_basis"], "near-reference-floor")
        english = assessment["subjects"][plan["main_subject_id"]]
        self.assertEqual(english["comparable_scores"], [70.0, 79.0])
        self.assertEqual(assessment["total"]["gap_points"], 81)
        self.call("checkpoint", "--subject", "英语", "--score", "20",
                  "--max-score", "20", "--minutes", "15", "--scope", "partial")
        self.assertEqual(self.call("replan")["plan"]["main_subject_name"], "英语")
        cleared = self.call("profile", "goals", "--remove-floor", "英语", "--clear-total-target")
        self.assertEqual(cleared["plan"]["goal_assessment"]["total"], None)
        self.assertNotEqual(cleared["plan"]["main_subject_name"], "英语")

    def test_fresh_drill_avoids_seen_or_attempted_question(self):
        paper = self.directory / "两道题.md"
        paper.write_text("第1题 求极限。\n第2题 计算积分。", encoding="utf-8")
        self.call("ingest", str(paper), "--subject", "数学")
        first = self.call("drill", "--subject", "数学")["question"]["id"]
        self.call("attempt", "--question-id", first, "--minutes", "5", "--result", "wrong")
        second = self.call("drill", "--subject", "数学", "--fresh")["question"]["id"]
        self.assertNotEqual(second, first)
        empty = subprocess.run([sys.executable, str(ENGINE), "drill", str(self.study),
                                "--subject", "数学", "--fresh"], capture_output=True, encoding="utf-8")
        self.assertNotEqual(empty.returncode, 0)
        self.assertEqual(json.loads(empty.stderr)["code"], "no_fresh_source_questions")
