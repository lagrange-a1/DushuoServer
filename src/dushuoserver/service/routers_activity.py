"""活动上报路由。"""

import time

from fastapi import APIRouter, Depends

from ..logger import logger
from ..config import config
from ..database import cleanup_activities, insert_activity
from ..runtime import state
from ..schemas import ActivityRequest
from ..services import require_signature

router = APIRouter(tags=["activity"])


@router.post("/api/activity")
def report_activity(
    body: ActivityRequest, client_id: str = Depends(require_signature)
) -> dict:
    """接收数字活动并重置倒计时。"""
    cleanup_activities(config.runtime.activity_cache_duration)

    now = body.timestamp or time.time()
    insert_activity(client_id, body.activity, now)

    state.last_activity_at = now

    if not state.triggered:
        state.update_deadline()
        logger.info(
            "收到客户端`{}`在`{}`时的活动`{}`，倒计时已重置".format(
                client_id, body.timestamp, body.activity
            )
        )

    return {
        "accepted": True,
        "countdown_reset": not state.triggered,
        "deadline": state.deadline,
    }
