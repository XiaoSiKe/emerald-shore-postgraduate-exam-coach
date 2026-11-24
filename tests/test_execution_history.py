from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from emerald_shore import service
from emerald_shore.execution import execution_window, save_day_plan


class ExecutionHistoryTests(unittest.TestCase):
    def test_completed_days_include_unlogged_latest_plan_but_not_cancelled_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            today = date(2027, 3, 1)
            yesterday = today - timedelta(days=1)
            task = lambda name: {"id": name, "planned_minutes": 12}
            save_day_plan(root, {"plan_date": yesterday.isoformat(), "tasks": [task("a"), task("cancelled")]})
            save_day_plan(root, {"plan_date": yesterday.isoformat(), "tasks": [task("a"), task("b")]})
            save_day_plan(root, {"plan_date": today.isoformat(), "tasks": [task("c"), task("d")]})
            log = lambda day, name, result, minutes: {
                "type": "task", "plan_date": day.isoformat(), "task_id": name,
                "planned_minutes": 12, "actual_minutes": minutes, "result": result,
            }
            ledger = [
                log(yesterday, "a", "partial", 7), log(yesterday, "a", "complete", 13),
                log(today, "c", "complete", 11),
            ]
            result = execution_window(root, ledger, yesterday, today, {}, [])
            self.assertEqual(result["closed_days"]["tasks"], 2)
            self.assertEqual(result["closed_days"]["unlogged"], 1)
            self.assertEqual(result["today"]["pending"], 1)
            self.assertEqual(result["planned_tasks"], 3)
            self.assertEqual(result["actual_task_minutes"], 24)

    def test_main_only_survives_weekly_and_resets_next_date(self):
        with tempfile.TemporaryDirectory() as workspace:
            exam = (date.today() + timedelta(days=60)).isoformat()
            service.init(workspace, exam, 2, "演练")
            for name in ("数学", "英语"):
                service.add_subject(workspace, name, 100, 50, 80, "calculation", None)
            plan = service.make_plan(workspace, "replan", 20, True)["plan"]
            self.assertEqual([task["role"] for task in plan["tasks"]], ["main"])
            self.assertEqual(plan["tasks"][0]["planned_minutes"], 17)
            service.log_task(workspace, plan["tasks"][0]["id"], 12, "complete", None, "闭卷")
            with patch("emerald_shore.service.read_jsonl", wraps=service.read_jsonl) as read:
                weekly = service.weekly_review(workspace)
            self.assertCountEqual(
                [call.args[0].name for call in read.call_args_list],
                ["ledger.jsonl", "mistakes.jsonl"],
            )
            self.assertEqual(weekly["weekly"]["execution"]["today"]["completed"], 1)
            self.assertEqual(weekly["plan"]["tasks"][0]["status"], "complete")
            with patch("emerald_shore.service.date", wraps=date) as clock:
                clock.today.return_value = date.today() + timedelta(days=1)
                self.assertFalse(service.today(workspace)["plan"]["day_context"]["main_only"])
