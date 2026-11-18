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
        """配对密钥；演示模式下配对窗口常开，密钥不因超时而失效。"""
        if not config.demo_mode and self.__pairing_key_expire_at < time.time():
            self.__pairing_key = None
        return self.__pairing_key

    @property
    def pairing_window_remaining_seconds(self) -> Optional[int]:
        """配对窗口的剩余秒数；演示模式下窗口常开，返回 None。"""
        if config.demo_mode:
            return None

        return max(0, self.__pairing_key_expire_at - State.safe_integer_time(0))

    def update_deadline(self):
        """更新倒计时。"""
        self.deadline = self.safe_integer_time(config.runtime.death_countdown)


state: State = State(triggered=False)


async def countdown_loop(execute_final_task: Callable[[], None], interval: float = 1.0):
    """
    后台倒计时循环。

    当倒计时结束且尚未触发最终任务时，执行最终任务。演示模式下不锁定死亡状态：
    最终任务不予执行，倒计时随即重新展开，使服务端能够长期作为演示环境使用。
    `interval` 为轮询间隔（秒），便于测试时加快节奏。
    """
    while True:
        await asyncio.sleep(interval)

        if state.triggered:
            continue

        if time.time() >= state.deadline:
            if config.demo_mode:
                logger.info(
                    "演示模式：死亡判定倒计时结束，最终任务不予执行，倒计时重新展开"
                )
                state.update_deadline()
                continue

            state.triggered = True
            logger.info("死亡判定倒计时结束，开始执行最终任务")
            await asyncio.to_thread(execute_final_task)
