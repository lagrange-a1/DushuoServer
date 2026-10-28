"""度朔服务端配置定义。"""

from pathlib import Path
from typing import Any

# SQLite 数据库文件路径。服务默认在当前工作目录创建该文件。
DB_PATH = Path("dushuo.db")

# 服务启动时写入数据库的默认配置。
DEFAULT_CONFIG: dict[str, Any] = {
    "port": 8000,
    "activity_retention_seconds": 86400,
    "countdown_seconds": 86400,
    "final_task": "",
    "pairing_window_seconds": 300,
    "message_cache_seconds": 3600,
}

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
