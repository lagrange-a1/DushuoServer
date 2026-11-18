"""活动上报路由。"""

import time

from fastapi import APIRouter

from ..logger import logger
from ..config import config
from ..database import cleanup_activities, insert_activity
from ..runtime import state
from ..schemas import ActivityRequest, SignedRequest
from ..services import parse_payload, verify_signed_request

router = APIRouter(tags=["activity"])


@router.post("/api/activity")
def report_activity(body: SignedRequest) -> dict:
    """接收数字活动并重置倒计时。"""
    verify_signed_request(body)
    activity = parse_payload(body, ActivityRequest)

    cleanup_activities(config.runtime.activity_cache_duration)

    now = activity.timestamp or time.time()
    insert_activity(body.client_id, activity.activity, now)

    state.last_activity_at = now

    if not state.triggered:
        state.update_deadline()
        logger.info(
            "收到客户端`{}`在`{}`时的活动`{}`，倒计时已重置".format(
                body.client_id, activity.timestamp, activity.activity
            )
        )

    return {
        "accepted": True,
        "countdown_reset": not state.triggered,
        "deadline": state.deadline,
    }
