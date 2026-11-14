"""度朔服务端命令行启动入口。"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import uvicorn

from .config import config


def build_parser() -> argparse.ArgumentParser:
    """构建服务端命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="dushuoserver",
        description="度朔服务端：通过监控数字活动进行生死判断。",
        argument_default=argparse.SUPPRESS,
        add_help=False,
        suggest_on_error=True,
        color=True,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示帮助信息并退出",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="显示版本信息并退出",
    )
    parser.add_argument(
        "-l",
        "--licence",
        "--license",
        action="store_true",
        help="显示软件授权信息并打印至日志文件后退出",
    )

    starter_argumets = parser.add_argument_group(
        "启动参数",
        "在服务端启动时须配置的参数，无法在客户端修改。",
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
        "-a",
        "--addr",
        "--address",
        "--host-address",
        dest="host",
        type=str,
        default=None,
        help="监听地址",
    )
    starter_argumets.add_argument(
        "-p",
        "--port",
        "--host-port",
        dest="port",
        type=int,
        default=None,
        help="监听端口",
    )
    starter_argumets.add_argument(
        "--log-level",
        default=None,
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="日志级别",
    )
    starter_argumets.add_argument(
        "-d",
        "--database",
        "--db-path",
        dest="database_path",
        type=Path,
        default=None,
        help="SQLite 数据库文件路径",
    )

    starter_argumets.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Uvicorn 工作进程数",
    )
    starter_argumets.add_argument(
        "--hot-reload",
        dest="hot_reload",
        action="store_true",
        default=None,
        help="开启 Uvicorn 开发模式热重载",
    )
    starter_argumets.add_argument(
        "--no-access-log",
        action="store_true",
        default=None,
        help="关闭 Uvicorn 访问日志",
    )

    # 可运行时修改的配置项，可通过命令行覆盖默认配置文件。

    runtime_argumets = parser.add_argument_group(
        "运行时参数",
        "可运行时修改的配置项，可通过客户端修改，不应在配置文件中出现。",
    )

    runtime_argumets.add_argument(
        "--live-activity-duration",
        "--activity-cache-duration",
        dest="seconds",
        type=int,
        default=None,
        help="数字活动缓存时间（秒）",
    )
    runtime_argumets.add_argument(
        "--countdown-seconds",
        "--death-countdown",
        dest="countdown",
        type=int,
        default=None,
        help="倒计时延续时间（秒）",
    )
    runtime_argumets.add_argument(
        "--execution-task",
        dest="command",
        type=str,
        default=None,
        help="最终任务执行命令",
    )
    runtime_argumets.add_argument(
        "--message-cache-duration",
        type=int,
        default=None,
        help="短报文消息缓存时间（秒）",
    )
    runtime_argumets.add_argument(
        "--pairing-window-time",
        type=int,
        default=None,
        help="配对链接的有效窗口时长（秒）",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """解析命令行参数并启动服务"""

    args = build_parser().parse_args(argv)

    if args.licence:
        from .license_show import main as license_show

        license_show()
        return

    global config

    # 数据库 > 命令行传参 > 配置文件 > 默认参数

    if args.config_path is not None:
        config = config.load_config(args.config_path)

    overrides = config.model_dump(mode="python")

    if args.host is not None:
        overrides["host_address"] = args.host
    if args.port is not None:
        overrides["host_port"] = args.port

    true_log_level = None
    if args.log_level is not None:
        overrides["log_level"] = true_log_level = args.log_level
        if "TRACE" in true_log_level.upper():
            true_log_level = "TRACE"

    if args.database_path is not None:
        overrides["db_path"] = args.database_path
    if args.hot_reload is not None:
        overrides["uvicron"]["hot_reload"] = args.hot_reload
    if args.workers is not None:
        if overrides["uvicron"]["hot_reload"]:
            overrides["uvicron"]["workers"] = 1
        else:
            overrides["uvicron"]["workers"] = args.workers
    if args.no_access_log is not None:
        overrides["uvicron"]["access_log"] = not args.no_access_log
    if args.seconds is not None:
        overrides["runtime"]["activity_cache_duration"] = args.seconds
    if args.countdown is not None:
        overrides["runtime"]["death_countdown"] = args.countdown
    if args.command is not None:
        overrides["runtime"]["execution_task"] = args.command
    if args.message_cache_duration is not None:
        overrides["runtime"]["message_cache_duration"] = args.message_cache_duration
    if args.pairing_window_time is not None:
        overrides["runtime"]["pairing_window_time"] = args.pairing_window_time

    config = config.model_validate(overrides)
    true_log_level = true_log_level or config.log_level

    from .logger import logger

    logger.set_print_level = config.log_level

    logger.debug(
        "获得完整参数为：```\n{}\n```，即将启动服务".format(config.dump_as_toml())
    )

    uvicorn.run(
        "dushuoserver.app:app",
        host=config.host_address,
        port=config.host_port,
        reload=config.uvicron.hot_reload,
        workers=config.uvicron.workers,
        log_level=true_log_level,
        access_log=config.uvicron.access_log,
    )

    logger.info("服务已启动")


if __name__ == "__main__":
    main()
