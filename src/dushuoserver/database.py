"""度朔服务端数据库访问层。"""

import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

from .config import config, RuntimeConfig
from .logger import logger


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """创建一个启用行工厂的 SQLite 连接。

    使用上下文管理器确保连接在使用后关闭，避免 Windows 上文件被占用。
    """
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """初始化数据库表结构并写入默认配置。"""
    global config
    logger.info("数据库初始化")
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rtconfig (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                activity TEXT,
                created_at REAL NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_fetches (
                device_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                fetched_at REAL NOT NULL,
                PRIMARY KEY (device_id, message_id)
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                public_key TEXT NOT NULL,
                paired_at REAL NOT NULL
            )
            """)

        conn.commit()

        # 运行时参数确认
        runtime_config_rows = dict(
            conn.execute("SELECT key, value FROM rtconfig").fetchall()
        )

        for key, value in config.runtime.model_dump(mode="json").items():
            if key not in runtime_config_rows:
                conn.execute(
                    "INSERT INTO rtconfig (key, value) VALUES (?, ?)",
                    (key, value),
                )
            # conn.execute(
            #     "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            #     (key, value),
            # )

        conn.commit()

        # 重新读取数据库中的运行时参数，保证内存与数据库一致
        runtime_config_rows = dict(
            conn.execute("SELECT key, value FROM rtconfig").fetchall()
        )

    config.runtime = config.runtime.model_validate(runtime_config_rows)


def set_config_value(key: str, value: Any) -> None:
    global config
    config.runtime.update(key, value)
    """写入或更新一个配置项。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO rtconfig (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, config.runtime.model_dump(mode="json")[key]),
        )
        conn.commit()


def cleanup_activities(retention_seconds: int) -> None:
    """删除超过保留时间的数字活动记录。"""
    cutoff = time.time() - retention_seconds
    with get_connection() as conn:
        conn.execute("DELETE FROM activities WHERE created_at < ?", (cutoff,))
        conn.commit()


def insert_activity(client_id: str, activity: str, created_at: float) -> None:
    """记录一条客户端数字活动。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO activities (client_id, activity, created_at) VALUES (?, ?, ?)",
            (client_id, activity, created_at),
        )
        conn.commit()


def cleanup_messages(cache_seconds: int) -> None:
    """删除过期短报文及其设备获取记录。"""
    cutoff = time.time() - cache_seconds
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
        conn.execute(
            "DELETE FROM message_fetches WHERE message_id NOT IN (SELECT id FROM messages)"
        )
        conn.commit()


def get_latest_message() -> Optional[sqlite3.Row]:
    """获取最新一条短报文。"""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, content, created_at FROM messages ORDER BY id DESC LIMIT 1"
        ).fetchone()


def insert_message(content: str, created_at: float) -> None:
    """插入一条新的短报文。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (content, created_at) VALUES (?, ?)",
            (content, created_at),
        )
        conn.commit()


def delete_message(message_id: int) -> None:
    """删除指定短报文及其设备获取记录。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.execute("DELETE FROM message_fetches WHERE message_id = ?", (message_id,))
        conn.commit()


def has_fetched_message(device_id: str, message_id: int) -> bool:
    """判断设备是否已经获取过指定消息。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM message_fetches WHERE device_id = ? AND message_id = ?",
            (device_id, message_id),
        ).fetchone()
    return row is not None


def mark_message_fetched(device_id: str, message_id: int, fetched_at: float) -> None:
    """记录设备已获取某条消息。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO message_fetches (device_id, message_id, fetched_at) "
            "VALUES (?, ?, ?)",
            (device_id, message_id, fetched_at),
        )
        conn.commit()


def upsert_client(client_id: str, public_key: str) -> None:
    """写入或更新一个客户端的公钥。"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO clients (client_id, public_key, paired_at) VALUES (?, ?, ?) "
            "ON CONFLICT(client_id) DO UPDATE SET public_key = excluded.public_key",
            (client_id, public_key, time.time()),
        )
        conn.commit()


def get_client_public_key(client_id: str) -> Optional[str]:
    """获取一个客户端的公钥；客户端未配对时返回 None。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT public_key FROM clients WHERE client_id = ?",
            (client_id,),
        ).fetchone()
    return None if row is None else row["public_key"]


def get_all_client_public_keys() -> list[tuple[str, str]]:
    """列出全部已登记客户端的标识与公钥。"""
    with get_connection() as conn:
        rows = conn.execute("SELECT client_id, public_key FROM clients").fetchall()
    return [(row["client_id"], row["public_key"]) for row in rows]
