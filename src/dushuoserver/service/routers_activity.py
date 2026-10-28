"""活动上报路由。"""

import time

from fastapi import APIRouter, Request

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
        state["triggered"] = False

    return {
        "accepted": True,
        "countdown_reset": True,
        "deadline": state["deadline"],
    }
