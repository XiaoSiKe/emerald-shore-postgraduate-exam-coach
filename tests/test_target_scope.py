import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from emerald_shore import service
from emerald_shore.errors import EmeraldError
from emerald_shore.state import read_json


class SchoolScopeTests(unittest.TestCase):
    def test_retarget_851_keeps_history_and_blocks_old_topics_scores_and_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = str(root / "study")
            exam = (date.today() + timedelta(days=30)).isoformat()
            service.init(workspace, exam, 2, "演练", "青崖", "人工智能", 2027)
            service.add_subject(workspace, "专业课", 150, 78, 115, "understanding", None, "851", True)
            service.add_topic(workspace, "专业课", "树与图", 4, .5, .8, None)
            first = root / "tree.md"
            first.write_text("第1题 二叉树层序如何遍历？", encoding="utf-8")
            service.ingest(workspace, [str(first)], "target_school_open", "专业课", "树与图", "high", "青崖851")
            start = service.drill(workspace, "专业课")["question"]["id"]
            service.record_attempt(workspace, start, "wrong", 3, "reasoning", None)
            self.assertEqual(service.make_plan(workspace)["plan"]["main_topic_name"], "树与图")

            service.set_profile_context(workspace, None, "松岭", "人工智能", 2027)
            status = service.status(workspace)
            self.assertIsNone(status["subjects"][0]["current_score"])
            self.assertIsNone(service.today(workspace)["plan"]["main_topic_name"])
            self.assertIn("短测", service.today(workspace)["plan"]["tasks"][0]["title"])
            with self.assertRaises(EmeraldError) as missing:
                service.drill(workspace, "专业课")
            self.assertEqual(missing.exception.code, "no_source_questions")
            with self.assertRaises(EmeraldError) as out_of_scope:
                service.record_attempt(workspace, start, "correct", 2, None, None)
            self.assertEqual(out_of_scope.exception.code, "inactive_target_question")

            service.add_topic(workspace, "专业课", "事务", 3, 0, .5, None)
            second = root / "transaction.md"
            second.write_text("第1题 解释事务原子性。", encoding="utf-8")
            service.ingest(workspace, [str(second)], "target_school_open", "专业课", "事务", "high", "松岭851")
            self.assertEqual(service.make_plan(workspace)["plan"]["main_topic_name"], "事务")
            for _ in range(2):
                self.assertEqual(service.drill(workspace, "专业课")["source"]["target_scope"]["school"], "松岭")
            service.checkpoint(workspace, "专业课", 62, 150, 120)
            self.assertEqual(service.status(workspace)["subjects"][0]["current_score"], 62)
            service.set_profile_context(workspace, None, "青崖", "人工智能", 2027)
            self.assertEqual(service.status(workspace)["subjects"][0]["current_score"], 78)
            all_sources = read_json(Path(workspace) / ".emerald-shore" / "sources.json")
            self.assertEqual(len(all_sources), 2)
