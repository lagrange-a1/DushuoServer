"""短报文路由。"""

import time

from fastapi import APIRouter, Request

from ..database import (
    cleanup_messages,
    delete_message,
    get_config,
    get_latest_message,
    has_fetched_message,
    insert_message,
    mark_message_fetched,
)
from ..schemas import MessageRequest
from ..services import require_key

router = APIRouter(tags=["messages"])


@router.post("/api/message")
def message(request: Request, body: MessageRequest) -> dict:
    """处理短报文的获取、设置与删除。"""
    require_key(request)
    cfg = get_config()
    cleanup_messages(cfg["message_cache_seconds"])

    msg = get_latest_message()

    # 内容不为空时，按短报文协议设置或删除消息。
    if body.content:
        # 若设备已经获取当前消息，则不进行写入或删除操作。
        if msg is not None and has_fetched_message(body.device_id, msg["id"]):
            return {
                "action": "already_fetched",
                "message": msg["content"],
            }

        if msg is None:
            insert_message(body.content, time.time())
            return {"action": "set", "message": body.content}

        delete_message(msg["id"])
        return {"action": "deleted", "message": None}

    # 内容为空时，获取当前消息。
    if msg is None:
        return {"action": "empty", "message": None}

    already_fetched = has_fetched_message(body.device_id, msg["id"])

    if not already_fetched:
        mark_message_fetched(body.device_id, msg["id"], time.time())

    return {
        "action": "fetched",
        "message": msg["content"],
        "already_fetched": already_fetched,
    }
