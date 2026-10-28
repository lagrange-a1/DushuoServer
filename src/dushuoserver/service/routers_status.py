"""状态查询路由。"""

import time

from fastapi import APIRouter, Request

from ..database import get_config
from ..runtime import state
from ..services import require_key

router = APIRouter(tags=["status"])


@router.get("/api/status")
def status(request: Request) -> dict:
    """返回服务端当前状态。"""
    require_key(request)

    cfg = get_config()
    now = time.time()

    return {
        "status": "dead" if state["triggered"] else "alive",
        "countdown_remaining_seconds": max(0, state["deadline"] - now),
        "last_activity_at": state["last_activity_at"],
        "pairing_window_open": now
        < state["started_at"] + cfg["pairing_window_seconds"],
        "pairing_window_remaining_seconds": max(
            0, state["started_at"] + cfg["pairing_window_seconds"] - now
        ),
        "config": cfg,
    }
