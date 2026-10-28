"""度朔服务端配置定义。"""

import json
from pathlib import Path
from typing import Any

# SQLite 数据库文件路径。服务默认在当前工作目录创建该文件。
DB_PATH = Path("dushuo.db")

# 默认配置文件。服务启动时从该文件读取默认配置。
DEFAULT_CONFIG_PATH = Path(__file__).with_name("default_config.json")


def _load_default_config() -> dict[str, Any]:
    """读取默认配置文件。

    若文件不存在或内容无效，则回退到内置默认值，避免服务无法启动。
    """
    fallback: dict[str, Any] = {
        "port": 8000,
        "activity_retention_seconds": 86400,
        "countdown_seconds": 86400,
        "final_task": "",
        "pairing_window_seconds": 300,
        "message_cache_seconds": 3600,
    }

    try:
        with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)
    except (OSError, json.JSONDecodeError, TypeError):
        return fallback

    if not isinstance(loaded, dict):
        return fallback

    result = dict(fallback)
    result.update(loaded)
    return result


# 服务启动时写入数据库的默认配置。
DEFAULT_CONFIG: dict[str, Any] = _load_default_config()

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
