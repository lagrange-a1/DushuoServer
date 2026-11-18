"""状态查询路由。"""

import time

from fastapi import APIRouter

from ..config import config
from ..runtime import state
from ..schemas import SignedRequest
from ..services import verify_signed_request

router = APIRouter(tags=["status"])


@router.post("/api/status")
def status(body: SignedRequest) -> dict:
    """返回服务端当前状态。"""
    verify_signed_request(body)

    now = time.time()

    return {
        "status": "dead" if state.triggered else "alive",
        "countdown_remaining_seconds": max(0, state.deadline - now),
        "last_activity_at": state.last_activity_at,
        "pairing_window_open": state.pairing_key is not None,
        "pairing_window_remaining_seconds": max(0, state.pairing_key_expires_at - now),
        "config": config.model_dump(mode="json"),
    }
