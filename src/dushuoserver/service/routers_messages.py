"""短报文路由。"""

import time

from fastapi import APIRouter, Depends, HTTPException, Response

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
from ..schemas import MessageRequest
from ..services import require_signature

router = APIRouter(tags=["messages"])


@router.get("/api/message")
def fetch_message(client_id: str = Depends(require_signature)) -> dict:
    """获取当前短报文，并记录本客户端已读取。"""
    cleanup_messages(config.runtime.message_cache_duration)

    msg = get_latest_message()
    if msg is None:
        raise HTTPException(status_code=404, detail="当前没有短报文")

    already_fetched = has_fetched_message(client_id, msg["id"])

    if not already_fetched:
        mark_message_fetched(client_id, msg["id"], time.time())

    logger.debug("客户端`{}`获取了短报文".format(client_id))
    return {
        "message": msg["content"],
        "created_at": msg["created_at"],
        "already_fetched": already_fetched,
    }


@router.post("/api/message", status_code=201)
def send_message(
    body: MessageRequest, client_id: str = Depends(require_signature)
) -> dict:
    """发送一条新的短报文；当前已存在短报文时须先删除。"""
    cleanup_messages(config.runtime.message_cache_duration)

    if get_latest_message() is not None:
        raise HTTPException(status_code=409, detail="当前已有短报文，请先删除后再发送")

    created_at = time.time()
    insert_message(body.content, created_at)

    logger.debug("客户端`{}`发送了新的短报文".format(client_id))
    return {"message": body.content, "created_at": created_at}


@router.delete("/api/message", status_code=204)
def remove_message(client_id: str = Depends(require_signature)) -> Response:
    """删除当前短报文。"""
    cleanup_messages(config.runtime.message_cache_duration)

    msg = get_latest_message()
    if msg is None:
        raise HTTPException(status_code=404, detail="当前没有短报文")

    delete_message(msg["id"])

    logger.debug("客户端`{}`删除了短报文".format(client_id))
    return Response(status_code=204)
