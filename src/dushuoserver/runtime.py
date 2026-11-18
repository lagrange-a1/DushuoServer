"""度朔服务端运行时状态与倒计时。"""

import asyncio
import secrets
import time
from typing import Any, Callable, Coroutine, Optional
from dataclasses import dataclass

from .logger import logger
from .config import config


# 服务运行时状态
@dataclass(init=False, frozen=False, repr=False, eq=False, order=False)
class State:
    """运行时状态。"""

    started_at: float
    deadline: int
    triggered: bool
    last_activity_at: Optional[float]

    def __init__(self, triggered: bool = False) -> None:
        self.triggered = triggered
        self.last_activity_at = None
        self.__pairing_key: Optional[str] = None
        self.__pairing_key_expire_at: int = -1

        super().__init__()

    def __post_init__(self) -> None:
        self.started_at = time.time()
        self.update_deadline()

    @staticmethod
    def safe_integer_time(after: float) -> int:
        """返回一个整数时间戳。"""
        return int(time.time() + 0.5 + after)

    def generate_pairing_key(self):
        """生成配对密钥。"""
        self.__pairing_key = secrets.token_urlsafe(32)
        self.__pairing_key_expire_at = self.safe_integer_time(
            config.runtime.pairing_window_time
        )

    @property
    def pairing_key(self) -> Optional[str]:
        """配对密钥。"""
        if self.__pairing_key_expire_at < time.time():
            self.__pairing_key = None
        return self.__pairing_key

    @property
    def pairing_key_expires_at(self) -> int:
        """配对密钥的过期时间戳；尚未生成过密钥时为 -1。"""
        return self.__pairing_key_expire_at

    def update_deadline(self):
        """更新倒计时。"""
        self.deadline = self.safe_integer_time(config.runtime.death_countdown)


state: State = State(triggered=False)


async def countdown_loop(execute_final_task: Callable[[], None]):
    """
    后台倒计时循环。

    当倒计时结束且尚未触发最终任务时，执行最终任务。
    """
    while True:
        await asyncio.sleep(1)

        if state.triggered:
            continue

        if time.time() >= state.deadline:
            state.triggered = True
            logger.info("死亡判定倒计时结束，开始执行最终任务")
            await asyncio.to_thread(execute_final_task)
