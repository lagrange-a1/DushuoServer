"""活动上报路由。"""

import logging
import time

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

from ..database import cleanup_activities, get_config, insert_activity
from ..runtime import state
from ..schemas import ActivityRequest
from ..services import require_key

router = APIRouter(tags=["activity"])


@router.post("/api/activity")
def report_activity(request: Request, body: ActivityRequest) -> dict:
    """接收数字活动并重置倒计时。"""
    require_key(request)
    cfg = get_config()
    cleanup_activities(cfg["activity_retention_seconds"])

    now = body.timestamp or time.time()
    insert_activity(body.client_id, body.activity, now)

    state["last_activity_at"] = now

    if not state["triggered"]:
        state["deadline"] = now + cfg["countdown_seconds"]
        logger.debug("收到客户端 %s 的活动，倒计时已重置", body.client_id)

    return {
        "accepted": True,
        "countdown_reset": True,
        "deadline": state["deadline"],
    }
