"""度朔服务端配置定义。"""

from pathlib import Path
from typing import Any
from sys import version_info

if version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib # pyright: ignore[reportMissingImports]

# SQLite 数据库文件路径。服务默认在当前工作目录创建该文件。
DB_PATH = Path("dushuo.db")

# 默认配置文件。服务启动时从该文件读取默认配置。
DEFAULT_CONFIG_PATH = Path(__file__).with_name("default_config.toml")

# 内置回退配置，避免配置文件缺失或损坏时服务无法启动。
_FALLBACK_DEFAULT_CONFIG: dict[str, Any] = {
    "port": 8000,
    "activity_retention_seconds": 86400,
    "countdown_seconds": 86400,
    "final_task": "",
    "pairing_window_seconds": 300,
    "message_cache_seconds": 3600,
}


def load_default_config(path: str | Path | None = None) -> dict[str, Any]:
    """读取 TOML 格式的默认配置。

    参数
    ====
    path : str | Path | None
        配置文件路径；为空时使用 DEFAULT_CONFIG_PATH。

    返回
    ====
    dict[str, Any]
        合并内置回退值后的配置字典。
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    fallback = dict(_FALLBACK_DEFAULT_CONFIG)

    try:
        with config_path.open("rb") as config_file:
            loaded = tomllib.load(config_file)
    except (OSError, ValueError, TypeError):
        return fallback

    if not isinstance(loaded, dict):
        return fallback

    result = dict(fallback)
    result.update(loaded)
    return result


def set_db_path(path: str | Path) -> None:
    """设置 SQLite 数据库文件路径。"""
    global DB_PATH
    DB_PATH = Path(path)


def set_default_config_path(path: str | Path) -> None:
    """设置并重新加载默认配置文件路径。"""
    global DEFAULT_CONFIG_PATH, DEFAULT_CONFIG
    DEFAULT_CONFIG_PATH = Path(path)
    DEFAULT_CONFIG = load_default_config(DEFAULT_CONFIG_PATH)


# 启动时由命令行参数覆盖的配置项。空表示未覆盖。
CONFIG_OVERRIDES: dict[str, Any] = {}

# 服务启动时写入数据库的默认配置。
DEFAULT_CONFIG: dict[str, Any] = load_default_config()

# 允许客户端修改的配置项。
MUTABLE_CONFIG_KEYS = {
    "activity_retention_seconds",
    "countdown_seconds",
    "final_task",
    "pairing_window_seconds",
    "message_cache_seconds",
}

# 由服务端固定的配置项，客户端不得修改。
IMMUTABLE_CONFIG_KEYS = {"port"}

# 最终任务执行时的最大等待时间，单位为秒。
FINAL_TASK_TIMEOUT_SECONDS = 300
