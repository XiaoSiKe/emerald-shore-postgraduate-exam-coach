"""学生可读的 Markdown 仪表盘与今日行动单。"""

from __future__ import annotations

from typing import Any


def today_markdown(plan: dict[str, Any], subjects: list[dict[str, Any]]) -> str:
    subject_names = {item["id"]: item["name"] for item in subjects}
    lines = [
        f"# 今日行动单 · {plan['plan_date']}",
        "",
        f"阶段：**{plan['phase']['label']}**（距考试 {plan['phase']['days_remaining']} 天）",
        f"可安排时间：**{plan['daily_capacity_minutes']} 分钟**（已预留缓冲）",
        f"本周主攻：**{plan['main_subject_name']}**",
        "",
        "## 按顺序完成",
        "",
    ]
    for task in plan["tasks"]:
        subject = subject_names.get(task.get("subject_id"), "综合复习")
        lines.extend(
            [
                f"{task['order']}. **{task['title']}**",
                f"   - 科目：{subject}",
                f"   - 计划：{task['planned_minutes']} 分钟",
                f"   - 验收：{task['verification']}",
                f"   - task-id：`{task['id']}`",
            ]
        )
    lines.extend(["", "完成后用 `qingan.py log` 记录实际时间与结果。", ""])
    return "\n".join(lines)


def dashboard_markdown(
    profile: dict[str, Any],
    subjects: list[dict[str, Any]],
    plan: dict[str, Any],
    adherence: float | None,
    due_count: int,
    source_count: int,
) -> str:
    adherence_text = "暂无足够记录" if adherence is None else f"{adherence * 100:.0f}%"
    lines = [
        "# 青岸计划仪表盘",
        "",
        f"- 目标：{profile['target']}",
        f"- 考试日期：{profile['exam_date']}",
        f"- 当前阶段：{plan.get('phase', {}).get('label', '尚未生成计划')}",
        f"- 本周主攻：{plan.get('main_subject_name', '尚未确定')}",
        f"- 近 7 天执行率：{adherence_text}",
        f"- 到期复习项：{due_count}",
        f"- 已建库材料：{source_count}",
        "",
        "## 科目差距",
        "",
        "| 科目 | 当前 | 目标 | 差距 | 能力类型 |",
        "|---|---:|---:|---:|---|",
    ]
    for item in subjects:
        current = item.get("current_score", item["baseline"])
        lines.append(
            f"| {item['name']} | {current:g} | {item['target']:g} | {max(0, item['target'] - current):g} | {item['kind']} |"
        )
    lines.append("")
    return "\n".join(lines)
