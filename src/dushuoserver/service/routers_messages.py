"""短报文路由。"""

import time

from fastapi import APIRouter

from ..config import config
from ..logger import logger
from ..database import (
    cleanup_messages,
    delete_message,
    get_latest_message,
    has_fetched_message,
    insert_message,
    mark_message_fetched,
)
from ..schemas import MessageRequest, SignedRequest
from ..services import parse_payload, verify_signed_request

router = APIRouter(tags=["messages"])


@router.post("/api/message")
def message(body: SignedRequest) -> dict:
    """处理短报文的获取、设置与删除。"""
    verify_signed_request(body)
    msg_request = parse_payload(body, MessageRequest)

    cleanup_messages(config.runtime.message_cache_duration)

    msg = get_latest_message()

    # 内容不为空时，按短报文协议设置或删除消息。
    if msg_request.content:
        # 若客户端已经获取当前消息，则不进行写入或删除操作。
        if msg is not None and has_fetched_message(body.client_id, msg["id"]):
            return {
                "action": "already_fetched",
                "message": msg["content"],
            }

        if msg is None:
            insert_message(msg_request.content, time.time())
            logger.debug("客户端`{}`设置了新的短报文".format(body.client_id))
            return {"action": "set", "message": msg_request.content}

        delete_message(msg["id"])
        logger.debug("客户端`{}`删除了当前短报文".format(body.client_id))
        return {"action": "deleted", "message": None}

    # 内容为空时，获取当前消息。
    if msg is None:
        return {"action": "empty", "message": None}

    already_fetched = has_fetched_message(body.client_id, msg["id"])

    if not already_fetched:
        mark_message_fetched(body.client_id, msg["id"], time.time())

    return {
        "action": "fetched",
        "message": msg["content"],
        "already_fetched": already_fetched,
    }
