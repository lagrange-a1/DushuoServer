"""度朔服务端命令行启动入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from . import config


def build_parser() -> argparse.ArgumentParser:
    """构建服务端命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="dushuoserver",
        description="度朔服务端：通过监控数字活动进行生死判断。",
    )

    starter_argumets = parser.add_argument_group(
        "启动参数",
        "在服务端启动时须配置的参数，无法在客户端修改。",
    )

    starter_argumets.add_argument(
        "-a",
        "--host",
        "--addr",
        "--address",
        default="0.0.0.0",
        help="监听地址",
    )
    starter_argumets.add_argument(
        "-p",
        "--port",
        type=int,
        default=18470,
        help="监听端口",
    )

    starter_argumets.add_argument(
        "-c",
        "--config",
        "--default-config",
        dest="config_path",
        type=Path,
        default=None,
        help="配置文件路径，若配置文件中有与命令行参数冲突的参数，将使用命令行参数覆盖。",
    )

    starter_argumets.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Uvicorn 工作进程数",
    )
    starter_argumets.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="开启开发模式热重载",
    )

    starter_argumets.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="日志级别",
    )
    starter_argumets.add_argument(
        "--no-access-log",
        action="store_true",
        help="关闭 Uvicorn 访问日志",
    )

    starter_argumets.add_argument(
        "--database",
        "--db-path",
        dest="database_path",
        type=Path,
        default=None,
        help="SQLite 数据库文件路径",
    )

    # 可运行时修改的配置项，可通过命令行覆盖默认配置文件。

    runtime_argumets = parser.add_argument_group(
        "运行时参数",
        "可运行时修改的配置项，可通过客户端修改，不应在配置文件中出现。",
    )

    runtime_argumets.add_argument(
        "--activity-retention-seconds", type=int, default=None
    )
    runtime_argumets.add_argument("--countdown-seconds", type=int, default=None)
    runtime_argumets.add_argument("--final-task", type=str, default=None)
    runtime_argumets.add_argument("--pairing-window-seconds", type=int, default=None)
    runtime_argumets.add_argument("--message-cache-seconds", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    """解析命令行参数并启动服务。"""
    args = build_parser().parse_args(argv)

    if args.config_path is not None:
        config.set_default_config_path(args.config_path)

    if args.database_path is not None:
        config.set_db_path(args.database_path)

    overrides: dict[str, object] = {}
    if args.port is not None:
        config.DEFAULT_CONFIG["port"] = args.port
    if args.activity_retention_seconds is not None:
        overrides["activity_retention_seconds"] = args.activity_retention_seconds
    if args.countdown_seconds is not None:
        overrides["countdown_seconds"] = args.countdown_seconds
    if args.final_task is not None:
        overrides["final_task"] = args.final_task
    if args.pairing_window_seconds is not None:
        overrides["pairing_window_seconds"] = args.pairing_window_seconds
    if args.message_cache_seconds is not None:
        overrides["message_cache_seconds"] = args.message_cache_seconds

    config.CONFIG_OVERRIDES = overrides
    config.DEFAULT_CONFIG.update(overrides)

    port = int(config.DEFAULT_CONFIG.get("port", 8000))

    workers = args.workers
    if args.reload and workers != 1:
        workers = 1

    uvicorn.run(
        "dushuoserver.app:app",
        host=args.host,
        port=port,
        reload=args.reload,
        workers=workers,
        log_level=args.log_level,
        access_log=not args.no_access_log,
    )

    from .logger import logger
    from TrimLog.logger_constants import WEIGHT_ORDER

    if (trimlog_log_level := args.log_level.upper()) not in WEIGHT_ORDER:
        trimlog_log_level = "DEBUG"
    logger.set_print_level = trimlog_log_level


if __name__ == "__main__":
    main()
