"""稳定 JSON 输出的命令行界面。"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .errors import QinganError
from .service import add_subject, checkpoint, ingest, init, log_task, make_plan, review, status, today


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qingan.py", description="青岸计划·考研冲刺教练本地效率引擎")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化学习工作区")
    init_parser.add_argument("workspace")
    init_parser.add_argument("--exam-date", required=True)
    init_parser.add_argument("--daily-hours", required=True, type=float)
    init_parser.add_argument("--target", default="考研初试")

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

    ingest_parser = subparsers.add_parser("ingest", help="本地材料建库")
    ingest_parser.add_argument("workspace")
    ingest_parser.add_argument("inputs", nargs="+")
    ingest_parser.add_argument(
        "--evidence-level",
        default="user_material",
        choices=("user_material", "past_paper", "official", "external_aid"),
    )

    for name in ("plan", "today", "replan", "review", "status"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("workspace")

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
    if args.command == "ingest":
        return ingest(args.workspace, args.inputs, args.evidence_level)
    if args.command == "plan":
        return make_plan(args.workspace, "manual")
    if args.command == "today":
        return today(args.workspace)
    if args.command == "replan":
        return make_plan(args.workspace, "replan")
    if args.command == "log":
        return log_task(args.workspace, args.task_id, args.minutes, args.result, args.error_type, args.note)
    if args.command == "checkpoint":
        return checkpoint(args.workspace, args.subject, args.score, args.max_score, args.minutes)
    if args.command == "review":
        return review(args.workspace)
    if args.command == "status":
        return status(args.workspace)
    raise QinganError("unknown_command", "未知命令。", "运行 qingan.py --help。")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = dispatch(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except QinganError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except Exception as exc:  # 防止 Agent 调用方收到非结构化回溯
        payload = QinganError(
            "internal_error",
            "发生未预期错误。",
            "保留工作区并提交错误信息；不要删除原始材料。",
            {"error": str(exc)},
        ).as_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
