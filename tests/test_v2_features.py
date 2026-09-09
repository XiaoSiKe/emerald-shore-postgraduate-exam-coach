import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from emerald_shore.errors import EmeraldError
from emerald_shore.planner import build_plan, rank_topics
from emerald_shore.service import (
    add_subject,
    add_topic,
    drill,
    ingest,
    init,
    make_plan,
    migrate,
    record_attempt,
    set_focus,
    set_profile_context,
    set_routine,
    update_topic,
    weekly_review,
)
from emerald_shore.state import read_json


class TopicPlanningTests(unittest.TestCase):
    def test_topic_priority_and_plan_integration(self):
        subjects = [
            {
                "id": "math",
                "name": "数学",
                "max_score": 150,
                "baseline": 60,
                "current_score": 60,
                "target": 110,
                "kind": "calculation",
                "estimated_hours": None,
                "score_history": [],
            }
        ]
        topics = [
            {
                "id": "calculus",
                "subject_id": "math",
                "name": "微积分",
                "weight": 3,
                "mastery": 0.2,
                "confidence": 0.8,
                "estimated_hours": None,
            },
            {
                "id": "algebra",
                "subject_id": "math",
                "name": "线性代数",
                "weight": 2,
                "mastery": 0.8,
                "confidence": 0.8,
                "estimated_hours": None,
            },
        ]
        ranked = rank_topics(topics, [], "math")
        self.assertEqual(ranked[0]["id"], "calculus")
        plan = build_plan(
            {"exam_date": "2026-04-11", "daily_hours": 4, "buffer_ratio": 0.15},
            subjects,
            [],
            [],
            "test",
            date(2026, 1, 1),
            topics,
        )
        self.assertEqual(plan["schema_version"], 2)
        self.assertEqual(plan["main_topic_name"], "微积分")
        self.assertEqual(plan["tasks"][0]["topic_id"], "calculus")


class V2FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "study"
        init(str(self.workspace), (date.today() + timedelta(days=70)).isoformat(), 5, "考研初试")
        add_subject(str(self.workspace), "数学", 150, 60, 110, "calculation", None)
        self.topic = add_topic(str(self.workspace), "数学", "微积分", 3, 0.2, 0.7, None)["topic"]

    def tearDown(self):
        self.temp.cleanup()

    def test_bound_ingest_drill_attempt_and_weekly(self):
        material = self.root / "paper.md"
        material.write_text("第1题 求极限。\n第2题 判断级数收敛性。", encoding="utf-8")
        result = ingest(str(self.workspace), [str(material)], "past_paper", "数学", "微积分")
        self.assertEqual(result["added_sources"][0]["subject_id"], "sub-b79624b8")
        picked = drill(str(self.workspace), "数学", "微积分")
        self.assertNotIn("answer", picked["question"])
        self.assertEqual(picked["source"]["evidence_level"], "past_paper")
        attempted = record_attempt(
            str(self.workspace),
            picked["question"]["id"],
            "wrong",
            12,
            "reasoning",
            "方法识别错误",
        )
        self.assertLess(attempted["topic"]["mastery"], 0.2)
        queue = read_json(self.workspace / ".emerald-shore/review_queue.json")
        self.assertEqual(queue[0]["key"], f"question:{picked['question']['id']}")
        weekly = weekly_review(str(self.workspace))
        self.assertEqual(weekly["weekly"]["evidence_events"], 1)
        self.assertEqual(weekly["weekly"]["error_counts"]["reasoning"], 1)
        self.assertEqual(weekly["weekly"]["efficiency"]["diagnosis"], "checkpoint_missing")
        self.assertTrue((self.workspace / ".emerald-shore/weekly.md").exists())
        self.assertTrue((self.workspace / ".emerald-shore/efficiency.md").exists())

    def test_focus_creates_specific_if_then_plan(self):
        plan = make_plan(str(self.workspace))["plan"]
        task = plan["tasks"][0]
        result = set_focus(
            str(self.workspace),
            task["id"],
            "晚饭后 19:00",
            "图书馆三楼固定座位",
            "想刷手机",
        )
        self.assertIn("如果到了晚饭后 19:00", result["focus"]["if_then"])
        self.assertIn("5 分钟闭卷启动", result["focus"]["if_then"])
        self.assertIn("想刷手机", result["focus"]["coping_plan"])

    def test_campus_routine_supplies_default_focus_place(self):
        routine = set_routine(
            str(self.workspace),
            4,
            8,
            7,
            "图书馆三楼固定座位",
            ["周三下午实验课", "周五晚社团值班"],
        )
        self.assertEqual(routine["routine"]["weekday_hours"], 4)
        plan = make_plan(str(self.workspace))["plan"]
        self.assertEqual(plan["day_context"]["preferred_place"], "图书馆三楼固定座位")
        result = set_focus(
            str(self.workspace),
            plan["tasks"][0]["id"],
            "晚饭后 19:00",
            None,
            "想刷手机",
        )
        self.assertEqual(result["focus"]["where"], "图书馆三楼固定座位")

    def test_target_school_open_source_requires_match_and_keeps_provenance(self):
        set_profile_context(str(self.workspace), None, "示例大学", "计算机科学与技术")
        subject = add_subject(
            str(self.workspace),
            "专业课",
            150,
            70,
            115,
            "understanding",
            None,
            "408",
        )["subject"]
        topic = add_topic(
            str(self.workspace),
            "专业课",
            "数据结构",
            4,
            0.3,
            0.8,
            None,
            "第二章",
        )["topic"]
        material = self.root / "target-school-paper.md"
        material.write_text("第1题 解释时间复杂度。", encoding="utf-8")
        result = ingest(
            str(self.workspace),
            [str(material)],
            "target_school_open",
            "专业课",
            "数据结构",
            "high",
            "示例大学、科目代码 408、公开往年题、2025 年",
        )
        source = result["added_sources"][0]
        self.assertEqual(subject["exam_code"], "408")
        self.assertEqual(topic["chapter"], "第二章")
        self.assertEqual(source["classification_confidence"], "high")
        self.assertIn("科目代码 408", source["match_note"])

    def test_target_school_and_low_confidence_evidence_gates(self):
        material = self.root / "uncertain.md"
        material.write_text("第1题 解释定义。", encoding="utf-8")
        with self.assertRaises(EmeraldError) as caught:
            ingest(
                str(self.workspace),
                [str(material)],
                "user_material",
                "数学",
                None,
                "low",
            )
        self.assertEqual(caught.exception.code, "low_confidence_binding")
        with self.assertRaises(EmeraldError) as caught:
            ingest(
                str(self.workspace),
                [str(material)],
                "target_school_open",
                "数学",
                None,
                "high",
                "院校与科目匹配",
            )
        self.assertEqual(caught.exception.code, "target_school_required")
        set_profile_context(str(self.workspace), None, "示例大学", None)
        with self.assertRaises(EmeraldError) as caught:
            ingest(
                str(self.workspace),
                [str(material)],
                "target_school_open",
                "数学",
            )
        self.assertEqual(caught.exception.code, "target_school_match_required")

    def test_reingest_can_bind_v1_unassigned_questions(self):
        material = self.root / "notes.md"
        material.write_text("第1题 解释定义。", encoding="utf-8")
        ingest(str(self.workspace), [str(material)], "user_material")
        rebound = ingest(str(self.workspace), [str(material)], "user_material", "数学", "微积分")
        self.assertEqual(len(rebound["added_sources"]), 0)
        self.assertEqual(rebound["binding_updates"], 1)
        self.assertIn("另更新 1 个", rebound["summary"])
        questions = read_json(self.workspace / ".emerald-shore/question_bank.json")
        self.assertEqual(questions[0]["subject_id"], "sub-b79624b8")
        self.assertEqual(questions[0]["topic_id"], self.topic["id"])

    def test_topic_update_is_public_and_replannable(self):
        result = update_topic(str(self.workspace), "数学", "微积分", 4, 0.4, 0.9, 30)
        self.assertEqual(result["topic"]["weight"], 4)
        self.assertEqual(result["topic"]["mastery"], 0.4)
        self.assertEqual(result["topic"]["confidence"], 0.9)
        self.assertEqual(result["topic"]["estimated_hours"], 30)

    def test_v1_workspace_migrates_without_deleting_legacy(self):
        legacy_workspace = self.root / "legacy"
        shutil.copytree(self.workspace / ".emerald-shore", legacy_workspace / ".qingan")
        profile_path = legacy_workspace / ".qingan/profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["schema_version"] = 1
        profile.pop("product_id", None)
        profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        for name in ("topics.json", "focus.json"):
            (legacy_workspace / ".qingan" / name).unlink(missing_ok=True)
        result = migrate(str(legacy_workspace))
        self.assertTrue(result["ok"])
        self.assertTrue((legacy_workspace / ".qingan").is_dir())
        self.assertTrue((legacy_workspace / ".emerald-shore").is_dir())
        migrated = read_json(legacy_workspace / ".emerald-shore/profile.json")
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["migrated_from"], ".qingan")
        self.assertEqual(read_json(legacy_workspace / ".emerald-shore/topics.json"), [])

    def test_v03_workspace_without_optional_v04_fields_still_plans(self):
        profile_path = self.workspace / ".emerald-shore/profile.json"
        profile = read_json(profile_path)
        profile.pop("routine", None)
        profile.pop("target_school", None)
        profile.pop("target_major", None)
        profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        result = make_plan(str(self.workspace))
        self.assertTrue(result["ok"])
        self.assertEqual(result["plan"]["day_context"]["capacity_basis"], "profile-daily-hours")
        self.assertEqual(result["plan"]["daily_capacity_minutes"], 255)


if __name__ == "__main__":
    unittest.main()
