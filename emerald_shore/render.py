"""面向学生的 Markdown 仪表盘、今日单与周复盘。"""

from __future__ import annotations

from typing import Any


def today_markdown(plan: dict[str, Any], subjects: list[dict[str, Any]]) -> str:
    subject_names = {item["id"]: item["name"] for item in subjects}
    day_context = plan.get("day_context") or {}
    day_label = "周末" if day_context.get("day_type") == "weekend" else "工作日"
    lines = [
        f"# 今日行动单 · {plan['plan_date']}",
        "",
        f"阶段：**{plan['phase']['label']}**（距考试 {plan['phase']['days_remaining']} 天）",
        f"可安排时间：**{plan['daily_capacity_minutes']} 分钟**（已预留缓冲）",
        f"校园节律：**{day_label}** · 原始可用 {day_context.get('available_hours', '未设置')} 小时",
        f"本周主攻：**{plan['main_subject_name']}**",
        f"主攻专题：**{plan.get('main_topic_name') or '待诊断'}**",
        "",
        "## 按顺序完成",
        "",
    ]
    if day_context.get("preferred_place"):
        lines.insert(6, f"建议地点：**{day_context['preferred_place']}**")
    if day_context.get("fixed_commitments"):
        lines.insert(7, f"固定安排（规划时避让）：{'；'.join(day_context['fixed_commitments'])}")
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
    lines.extend(["", "完成后用 `emerald.py log` 记录实际时间与结果。", ""])
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
        f"- 目标院校：{profile.get('target_school') or '尚未设置'}",
        f"- 目标专业：{profile.get('target_major') or '尚未设置'}",
        f"- 考试日期：{profile['exam_date']}",
        f"- 当前阶段：{plan.get('phase', {}).get('label', '尚未生成计划')}",
        f"- 本周主攻：{plan.get('main_subject_name', '尚未确定')}",
        f"- 主攻专题：{plan.get('main_topic_name') or '待诊断'}",
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


def weekly_markdown(review: dict[str, Any]) -> str:
    adherence = review.get("adherence")
    adherence_text = "暂无记录" if adherence is None else f"{adherence * 100:.0f}%"
    errors = review.get("error_counts", {})
    error_text = "、".join(f"{key} {value}" for key, value in sorted(errors.items())) or "无记录"
    efficiency = review.get("efficiency") or {}
    lines = [
        f"# 周复盘 · {review['period']['start']}—{review['period']['end']}",
        "",
        f"- 执行率：{adherence_text}",
        f"- 计划分钟：{review['planned_minutes']}",
        f"- 实际分钟：{review['actual_minutes']}",
        f"- 可验证训练次数：{review['evidence_events']}",
        f"- 错因分布：{error_text}",
        f"- 效率诊断：{efficiency.get('diagnosis_label', '暂无评估')}",
        f"- 下周主要矛盾：{review['next_main_subject']}",
        f"- 下周主攻专题：{review.get('next_main_topic') or '先做诊断'}",
        "",
        "## 调整决定",
        "",
        review["decision"],
        "",
        "## 下一步",
        "",
        review["next_action"],
        "",
    ]
    return "\n".join(lines)


def efficiency_markdown(report: dict[str, Any]) -> str:
    execution = report["execution"]
    evidence = report["evidence"]
    outcomes = report["outcomes"]
    errors = report["errors"]
    rate = execution.get("completion_rate")
    rate_text = "暂无记录" if rate is None else f"{rate * 100:.0f}%"
    correct_rate = outcomes.get("correct_rate")
    correct_text = "暂无记录" if correct_rate is None else f"{correct_rate * 100:.0f}%"
    recurring = "、".join(errors.get("recurring_types") or []) or "暂无重复错因"
    lines = [
        f"# 考研效率评估 · 最近 {report['days']} 天",
        "",
        "> 不给总分。效率不是‘坐了多久’，而是有限时间有没有换来可验证进步。",
        "",
        "| 维度 | 观察值 |",
        "|---|---|",
        f"| 执行 | {execution['completed_tasks']}/{execution['task_records']} 项完成；执行率 {rate_text} |",
        f"| 时间 | 计划 {execution['planned_minutes']} 分钟；任务记录 {execution['actual_task_minutes']} 分钟 |",
        f"| 有效证据 | {evidence['verified_events']} 次闭卷/来源题/检查点 |",
        f"| 独立答题 | {outcomes['attempts']} 次；正确率 {correct_text} |",
        f"| 错因复发 | {recurring} |",
        f"| 检查点 | {report['checkpoints']['count']} 次；可比较趋势 {len(report['checkpoints']['changes'])} 门 |",
        "",
        f"**当前诊断：** {report['diagnosis_label']}",
        "",
        report["explanation"],
        "",
        "**下一步：** " + report["next_action"],
        "",
    ]
    return "\n".join(lines)
