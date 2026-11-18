"""状态查询路由。"""

import time

from fastapi import APIRouter, Depends

from ..config import config
from ..runtime import state
from ..services import require_signature

router = APIRouter(tags=["status"])


@router.get("/api/status")
def status(client_id: str = Depends(require_signature)) -> dict:
    """返回服务端当前状态。"""
    now = time.time()

    return {
        "status": "dead" if state.triggered else "alive",
        "countdown_remaining_seconds": max(0, state.deadline - now),
        "last_activity_at": state.last_activity_at,
        "pairing_window_open": state.pairing_key is not None,
        "pairing_window_remaining_seconds": max(0, state.pairing_key_expires_at - now),
        "cliend_id": client_id,
    }
