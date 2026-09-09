"""提供稳定 JSON 输出的命令行接口。"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .errors import EmeraldError
from .service import (
    add_subject,
    add_topic,
    checkpoint,
    drill,
    ingest,
    init,
    log_task,
    make_plan,
    migrate,
    record_attempt,
    review,
    set_focus,
    status,
    today,
    update_topic,
    weekly_review,
)


def configure_utf8_stdio() -> None:
    """让中文帮助和 JSON 在 Windows 管道与终端中稳定输出。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def emit_json(payload, stream) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        text = json.dumps(payload, ensure_ascii=True, indent=2)
    print(text, file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emerald.py",
        description="青岸计划 · 考研突击冲刺 Agent Skill 的本地证据引擎",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化学习工作区")
    init_parser.add_argument("workspace")
    init_parser.add_argument("--exam-date", required=True)
    init_parser.add_argument("--daily-hours", required=True, type=float)
    init_parser.add_argument("--target", default="全国硕士研究生招生考试初试")

    migrate_parser = subparsers.add_parser("migrate", help="从 V0.1 .qingan 工作区无损迁移")
    migrate_parser.add_argument("workspace")

    subject_parser = subparsers.add_parser("subject", help="管理科目")
    subject_sub = subject_parser.add_subparsers(dest="subject_command", required=True)
    subject_add = subject_sub.add_parser("add", help="添加科目")
    subject_add.add_argument("workspace")
    subject_add.add_argument("--name", required=True)
    subject_add.add_argument("--max-score", required=True, type=float)
    subject_add.add_argument("--baseline", required=True, type=float)
    subject_add.add_argument("--target", required=True, type=float)
    subject_add.add_argument(
        "--kind",
        required=True,
        choices=("memory", "understanding", "calculation", "writing", "language", "timed"),
    )
    subject_add.add_argument("--estimated-hours", type=float)

    topic_parser = subparsers.add_parser("topic", help="管理科目内的高价值专题")
    topic_sub = topic_parser.add_subparsers(dest="topic_command", required=True)
    topic_add = topic_sub.add_parser("add", help="添加专题得分地图项")
    topic_add.add_argument("workspace")
    topic_add.add_argument("--subject", required=True)
    topic_add.add_argument("--name", required=True)
    topic_add.add_argument("--weight", required=True, type=float)
    topic_add.add_argument("--mastery", required=True, type=float)
    topic_add.add_argument("--confidence", default=0.5, type=float)
    topic_add.add_argument("--estimated-hours", type=float)
    topic_update = topic_sub.add_parser("update", help="更新专题权重、掌握度或证据置信度")
    topic_update.add_argument("workspace")
    topic_update.add_argument("--subject", required=True)
    topic_update.add_argument("--name", required=True)
    topic_update.add_argument("--weight", type=float)
    topic_update.add_argument("--mastery", type=float)
    topic_update.add_argument("--confidence", type=float)
    topic_update.add_argument("--estimated-hours", type=float)

    ingest_parser = subparsers.add_parser("ingest", help="本地材料建库")
    ingest_parser.add_argument("workspace")
    ingest_parser.add_argument("inputs", nargs="+")
    ingest_parser.add_argument(
        "--evidence-level",
        default="user_material",
        choices=("user_material", "past_paper", "official", "external_aid"),
    )
    ingest_parser.add_argument("--subject")
    ingest_parser.add_argument("--topic")

    for name in ("plan", "today", "replan", "review", "weekly", "status"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("workspace")

    drill_parser = subparsers.add_parser("drill", help="选择一道不泄露答案的来源题")
    drill_parser.add_argument("workspace")
    drill_parser.add_argument("--subject", required=True)
    drill_parser.add_argument("--topic")

    attempt_parser = subparsers.add_parser("attempt", help="记录一道来源题的独立作答结果")
    attempt_parser.add_argument("workspace")
    attempt_parser.add_argument("--question-id", required=True)
    attempt_parser.add_argument("--result", required=True, choices=("correct", "partial", "wrong"))
    attempt_parser.add_argument("--minutes", required=True, type=int)
    attempt_parser.add_argument(
        "--error-type",
        choices=("knowledge_gap", "reasoning", "procedure", "careless", "time_pressure"),
    )
    attempt_parser.add_argument("--note")

    focus_parser = subparsers.add_parser("focus", help="把今日任务变成 if–then 启动协议")
    focus_parser.add_argument("workspace")
    focus_parser.add_argument("--task-id", required=True)
    focus_parser.add_argument("--when", required=True)
    focus_parser.add_argument("--where", required=True)
    focus_parser.add_argument("--obstacle")

    log_parser = subparsers.add_parser("log", help="记录任务结果")
    log_parser.add_argument("workspace")
    log_parser.add_argument("--task-id", required=True)
    log_parser.add_argument("--minutes", required=True, type=int)
    log_parser.add_argument("--result", required=True, choices=("complete", "partial", "wrong", "skipped"))
    log_parser.add_argument(
        "--error-type",
        choices=("knowledge_gap", "reasoning", "procedure", "careless", "time_pressure"),
    )
    log_parser.add_argument("--note")

    checkpoint_parser = subparsers.add_parser("checkpoint", help="记录限时测验并重排")
    checkpoint_parser.add_argument("workspace")
    checkpoint_parser.add_argument("--subject", required=True)
    checkpoint_parser.add_argument("--score", required=True, type=float)
    checkpoint_parser.add_argument("--max-score", required=True, type=float)
    checkpoint_parser.add_argument("--minutes", required=True, type=int)
    return parser


def dispatch(args: argparse.Namespace):
    if args.command == "init":
        return init(args.workspace, args.exam_date, args.daily_hours, args.target)
    if args.command == "migrate":
        return migrate(args.workspace)
    if args.command == "subject" and args.subject_command == "add":
        return add_subject(
            args.workspace,
            args.name,
            args.max_score,
            args.baseline,
            args.target,
            args.kind,
            args.estimated_hours,
        )
    if args.command == "topic" and args.topic_command == "add":
        return add_topic(
            args.workspace,
            args.subject,
            args.name,
            args.weight,
            args.mastery,
            args.confidence,
            args.estimated_hours,
        )
    if args.command == "topic" and args.topic_command == "update":
        return update_topic(
            args.workspace,
            args.subject,
            args.name,
            args.weight,
            args.mastery,
            args.confidence,
            args.estimated_hours,
        )
    if args.command == "ingest":
        return ingest(args.workspace, args.inputs, args.evidence_level, args.subject, args.topic)
    if args.command == "plan":
        return make_plan(args.workspace, "manual")
    if args.command == "today":
        return today(args.workspace)
    if args.command == "replan":
        return make_plan(args.workspace, "replan")
    if args.command == "log":
        return log_task(args.workspace, args.task_id, args.minutes, args.result, args.error_type, args.note)
    if args.command == "drill":
        return drill(args.workspace, args.subject, args.topic)
    if args.command == "attempt":
        return record_attempt(
            args.workspace,
            args.question_id,
            args.result,
            args.minutes,
            args.error_type,
            args.note,
        )
    if args.command == "focus":
        return set_focus(args.workspace, args.task_id, args.when, args.where, args.obstacle)
    if args.command == "checkpoint":
        return checkpoint(args.workspace, args.subject, args.score, args.max_score, args.minutes)
    if args.command == "review":
        return review(args.workspace)
    if args.command == "weekly":
        return weekly_review(args.workspace)
    if args.command == "status":
        return status(args.workspace)
    raise EmeraldError("unknown_command", "未知命令。", "运行 emerald.py --help。")


def main(argv=None) -> int:
    configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = dispatch(args)
        emit_json(payload, sys.stdout)
        return 0
    except EmeraldError as exc:
        emit_json(exc.as_dict(), sys.stderr)
        return 2
    except Exception as exc:  # 防止 Agent 调用方收到非结构化回溯
        payload = EmeraldError(
            "internal_error",
            "发生未预期错误。",
            "保留工作区并提交错误信息；不要删除原始材料。",
            {"error": str(exc)},
        ).as_dict()
        emit_json(payload, sys.stderr)
        return 3
