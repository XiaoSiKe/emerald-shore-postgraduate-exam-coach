import unittest
from datetime import date, timedelta

from emerald_shore.errors import EmeraldError
from emerald_shore.planner import build_plan, determine_phase, due_reviews, rank_subjects, update_review_item


def subject(identifier, name, maximum, baseline, target, kind="memory", hours=None):
    return {
        "id": identifier,
        "name": name,
        "max_score": maximum,
        "baseline": baseline,
        "current_score": baseline,
        "target": target,
        "kind": kind,
        "estimated_hours": hours,
        "score_history": [],
    }


class PhaseTests(unittest.TestCase):
    def test_phase_boundaries(self):
        today = date(2026, 1, 1)
        expected = {
            1: "final",
            14: "final",
            15: "past-paper",
            45: "past-paper",
            46: "strengthening",
            90: "strengthening",
            91: "foundation",
            121: "foundation",
        }
        for days, code in expected.items():
            with self.subTest(days=days):
                actual = determine_phase((today + timedelta(days=days)).isoformat(), today)
                self.assertEqual(actual["code"], code)

    def test_past_exam_date_is_rejected(self):
        with self.assertRaises(EmeraldError) as caught:
            determine_phase("2026-01-01", date(2026, 1, 1))
        self.assertEqual(caught.exception.code, "exam_date_not_future")


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 1, 1)
        self.profile = {
            "exam_date": "2026-04-11",
            "daily_hours": 6,
            "buffer_ratio": 0.15,
        }
        self.subjects = [
            subject("math", "数学", 150, 60, 110, "calculation"),
            subject("english", "英语", 100, 55, 70, "language"),
            subject("politics", "政治", 100, 50, 70, "memory"),
            subject("major", "专业课", 150, 80, 120, "understanding"),
        ]

    def test_plan_never_exceeds_capacity_or_three_tasks(self):
        plan = build_plan(self.profile, self.subjects, [], [], "test", self.today)
        self.assertLessEqual(len(plan["tasks"]), 3)
        self.assertEqual(sum(task["planned_minutes"] for task in plan["tasks"]), 306)
        self.assertTrue(all(task["planned_minutes"] > 0 for task in plan["tasks"]))
        self.assertEqual(plan["main_subject_name"], "数学")

    def test_plan_ids_are_idempotent(self):
        first = build_plan(self.profile, self.subjects, [], [], "manual", self.today)
        second = build_plan(self.profile, self.subjects, [], [], "replan", self.today)
        self.assertEqual([task["id"] for task in first["tasks"]], [task["id"] for task in second["tasks"]])

    def test_campus_routine_changes_weekday_and_weekend_capacity(self):
        profile = {
            **self.profile,
            "routine": {
                "weekday_hours": 4,
                "weekend_hours": 8,
                "sleep_floor_hours": 7,
                "preferred_place": "图书馆三楼",
                "fixed_commitments": ["周三实验课", "周五社团值班"],
            },
        }
        weekday = build_plan(profile, self.subjects, [], [], "test", date(2026, 1, 1))
        weekend = build_plan(profile, self.subjects, [], [], "test", date(2026, 1, 3))
        self.assertEqual(weekday["daily_capacity_minutes"], 204)
        self.assertEqual(weekend["daily_capacity_minutes"], 408)
        self.assertEqual(weekday["day_context"]["day_type"], "weekday")
        self.assertEqual(weekend["day_context"]["day_type"], "weekend")
        self.assertEqual(weekday["day_context"]["preferred_place"], "图书馆三楼")
        self.assertEqual(weekday["day_context"]["fixed_commitments"], ["周三实验课", "周五社团值班"])

    def test_low_sleep_floor_warns_without_increasing_capacity(self):
        profile = {**self.profile, "routine": {"weekday_hours": 4, "sleep_floor_hours": 5}}
        plan = build_plan(profile, self.subjects, [], [], "test", self.today)
        self.assertEqual(plan["daily_capacity_minutes"], 204)
        self.assertTrue(any("睡眠底线低于 6 小时" in warning for warning in plan["warnings"]))

    def test_due_review_comes_first(self):
        queue = [{"key": "subject:math", "subject_id": "math", "label": "数学", "next_due": "2026-01-01"}]
        plan = build_plan(self.profile, self.subjects, [], queue, "test", self.today)
        self.assertEqual(plan["tasks"][0]["role"], "review")
        self.assertIn("subject:math", plan["tasks"][0]["review_keys"])

    def test_tiny_capacity_never_generates_negative_minutes(self):
        profile = {**self.profile, "daily_hours": 0.01}
        queue = [{"key": "subject:math", "subject_id": "math", "label": "数学", "next_due": "2026-01-01"}]
        plan = build_plan(profile, self.subjects, [], queue, "test", self.today)
        self.assertEqual(sum(task["planned_minutes"] for task in plan["tasks"]), 1)
        self.assertTrue(all(task["planned_minutes"] > 0 for task in plan["tasks"]))

    def test_cost_used_only_when_all_subjects_have_it(self):
        mixed = [dict(self.subjects[0], estimated_hours=100), self.subjects[1]]
        ranked = rank_subjects(mixed, [])
        self.assertTrue(all(item["priority_basis"] == "partial-no-time-cost" for item in ranked))
        complete = [dict(self.subjects[0], estimated_hours=100), dict(self.subjects[1], estimated_hours=50)]
        ranked = rank_subjects(complete, [])
        self.assertTrue(all(item["priority_basis"] == "quantitative" for item in ranked))

    def test_review_queue_reuses_subject_key_and_changes_interval(self):
        task = {"id": "daily", "subject_id": "math", "title": "数学主攻"}
        queue = update_review_item([], task, "complete", self.today)
        self.assertEqual(queue[0]["key"], "subject:math")
        self.assertEqual(queue[0]["next_due"], "2026-01-02")
        queue = update_review_item(queue, task, "complete", date(2026, 1, 2))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["next_due"], "2026-01-05")
        queue = update_review_item(queue, task, "wrong", date(2026, 1, 5))
        self.assertEqual(queue[0]["status"], "review-needed")
        self.assertEqual(queue[0]["next_due"], "2026-01-06")

    def test_due_reviews_ignore_invalid_rows(self):
        queue = [{"next_due": "bad"}, {"next_due": "2025-12-31", "key": "due"}]
        self.assertEqual([item["key"] for item in due_reviews(queue, self.today)], ["due"])


if __name__ == "__main__":
    unittest.main()
