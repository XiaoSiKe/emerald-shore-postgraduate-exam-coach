from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from emerald_shore import service
from emerald_shore.errors import EmeraldError
from emerald_shore.state import atomic_write_json


class RecallEvidenceTests(unittest.TestCase):
    def test_assisted_and_early_attempts_preserve_due_and_require_transfer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = str(root / "study")
            today = date.today()
            service.init(workspace, (today + timedelta(days=30)).isoformat(), 2, "演练")
            service.add_subject(workspace, "数学", 150, 70, 105, "calculation", None)
            service.add_topic(workspace, "数学", "共轭", 3, .4, .7, None)
            for index in range(2):
                paper = root / f"source-{index}.md"
                paper.write_text(f"第1题 求变式 {index} 的极限。", encoding="utf-8")
                service.ingest(workspace, [str(paper)], "user_material", "数学", "共轭")
            first = service.drill(workspace, "数学", fresh=True)["question"]["id"]
            self.assertEqual(service.drill(workspace, "数学", question_id=first)["question"]["id"], first)

            initial = service.record_attempt(workspace, first, "wrong", 2, "reasoning", None)
            due = initial["review_item"]["next_due"]
            for _ in range(3):
                practice = service.record_attempt(workspace, first, "correct", 1, None, None, "assisted")
                self.assertEqual(practice["topic"]["mastery"], .28)
                self.assertEqual(practice["review_item"]["next_due"], due)
            repeated = service.record_attempt(workspace, first, "correct", 1, None, None)
            self.assertEqual(repeated["evidence_basis"], "same-day-repeat")
            second = service.drill(workspace, "数学", fresh=True)["question"]["id"]
            transfer = service.record_attempt(workspace, second, "correct", 2, None, None)
            self.assertEqual(transfer["topic"]["mastery"], .496)
            self.assertEqual(transfer["mastery_evidence"]["qualified_attempts"], 2)
            self.assertEqual(transfer["mastery_evidence"]["status"], "needs_more_evidence")
            today_items = service.review(workspace, due)["due"]
            self.assertEqual(len(today_items), 2)
            self.assertEqual(next(row for row in today_items if row["key"] == f"question:{first}")["status"], "review-needed")

            tomorrow = today + timedelta(days=1)
            with patch("emerald_shore.service.date", wraps=date) as clock:
                clock.today.return_value = tomorrow
                for qid in (first, second):
                    final = service.record_attempt(workspace, qid, "correct", 3, None, None)
                    self.assertEqual(final["evidence_basis"], "spaced-independent")
            self.assertEqual(final["mastery_evidence"]["status"], "stable")
            further = today + timedelta(days=2)
            with patch("emerald_shore.service.date", wraps=date) as clock:
                clock.today.return_value = further
                early = service.record_attempt(workspace, second, "correct", 1, None, None)
                self.assertEqual(early["evidence_basis"], "early-repeat")
                self.assertEqual(early["review_item"]["next_due"], final["review_item"]["next_due"])

            with patch("emerald_shore.service.date", wraps=date) as clock:
                clock.today.return_value = further
                lapse = service.record_attempt(workspace, first, "wrong", 1, "reasoning", None)
            self.assertEqual(lapse["mastery_evidence"]["open_question_errors"], 1)
            self.assertEqual(lapse["mastery_evidence"]["status"], "needs_more_evidence")


    def test_review_reads_bank_once_and_keeps_topic_evidence_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = str(Path(temp) / "study")
            service.init(workspace, (date.today() + timedelta(days=30)).isoformat(), 2, "演练")
            service.add_subject(workspace, "数学", 150, 70, 105, "calculation", None)
            first = service.add_topic(workspace, "数学", "共轭", 3, .4, .7, None)["topic"]
            second = service.add_topic(workspace, "数学", "求导", 3, .4, .7, None)["topic"]
            state = Path(workspace) / ".emerald-shore"
            atomic_write_json(state / "question_bank.json", [
                {"id": "q1", "topic_id": first["id"], "source_id": "legacy", "attempts": [
                    {"evidence_basis": "first-independent", "result": "correct"},
                ]},
                {"id": "q2", "topic_id": second["id"], "source_id": "legacy", "attempts": [
                    {"evidence_basis": "assisted-practice", "result": "correct"},
                ]},
            ])
            with patch("emerald_shore.service.read_json", wraps=service.read_json) as reads:
                result = service.review(workspace)
            bank_reads = [call for call in reads.call_args_list if call.args[0].name == "question_bank.json"]
            self.assertEqual(len(bank_reads), 1)
            evidence = {row["topic"]: row for row in result["topic_evidence"]}
            self.assertEqual(evidence["共轭"]["qualified_attempts"], 1)
            self.assertEqual(evidence["求导"]["qualified_attempts"], 0)
            self.assertEqual(evidence["求导"]["practice_only_attempts"], 1)


    def test_targeted_drill_sanitizes_only_the_selected_stem(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = str(Path(temp) / "study")
            service.init(workspace, (date.today() + timedelta(days=30)).isoformat(), 2, "演练")
            subject = service.add_subject(workspace, "数学", 150, 70, 105, "calculation", None)["subject"]
            state = Path(workspace) / ".emerald-shore"
            atomic_write_json(state / "sources.json", [
                {"id": "source", "name": "来源材料", "path": "paper.md", "evidence_level": "user_material"},
            ])
            rows = [
                {"id": f"q{i}", "source_id": "source", "subject_id": subject["id"],
                 "text": f"试题{i}。\n参考答案：保密"}
                for i in range(4)
            ]
            bank = state / "question_bank.json"
            atomic_write_json(bank, rows)
            with patch("emerald_shore.service.question_stem", wraps=service.question_stem) as stem:
                selected = service.drill(workspace, "数学", question_id="q2")
            stem.assert_called_once_with(rows[2]["text"])
            self.assertEqual(selected["question"]["text"], "试题2。")
            saved = service.read_json(bank)
            self.assertEqual(saved[2]["presented_count"], 1)
            self.assertEqual([saved[i] for i in (0, 1, 3)], [rows[i] for i in (0, 1, 3)])
