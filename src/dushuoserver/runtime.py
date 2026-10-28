"""度朔服务端运行时状态与倒计时。"""

import asyncio
import secrets
import time
from typing import Any, Callable, Coroutine

from .config import DEFAULT_CONFIG
from .database import get_config

# 服务运行时状态。配对密钥在每次启动时重新生成。
state: dict[str, Any] = {
    "pairing_key": secrets.token_urlsafe(32),
    "started_at": time.time(),
    "deadline": time.time() + DEFAULT_CONFIG["countdown_seconds"],
    "triggered": False,
    "last_activity_at": None,
}


async def countdown_loop(execute_final_task: Callable[[], None]) -> None:
    """
    后台倒计时循环。

    当倒计时结束且尚未触发最终任务时，执行最终任务。
    """
    while True:
        await asyncio.sleep(1)

        if state["triggered"]:
            continue

        if time.time() >= state["deadline"]:
            state["triggered"] = True
            await asyncio.to_thread(execute_final_task)
