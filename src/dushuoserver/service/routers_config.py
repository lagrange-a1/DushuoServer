"""配置管理路由。"""

import time

from fastapi import APIRouter, HTTPException, Request

import logging

from ..config import IMMUTABLE_CONFIG_KEYS, MUTABLE_CONFIG_KEYS

logger = logging.getLogger(__name__)
from ..database import get_config, set_config_value
from ..runtime import state
from ..schemas import ConfigUpdateRequest
from ..services import require_key

router = APIRouter(tags=["config"])


@router.get("/api/config")
def read_config(request: Request) -> dict:
    """读取当前配置。"""
    require_key(request)
    return get_config()


@router.put("/api/config")
def update_config(request: Request, body: ConfigUpdateRequest) -> dict:
    """修改允许客户端修改的配置项。"""
    require_key(request)

    updates = body.model_dump(exclude_none=True)

    if any(key in IMMUTABLE_CONFIG_KEYS for key in updates):
        raise HTTPException(status_code=400, detail=f"所提交的配置项不可由客户端修改")

    for key, value in updates.items():
        if key not in MUTABLE_CONFIG_KEYS:
            raise HTTPException(status_code=400, detail=f"不支持修改配置项：{key}")

        if key in {
            "activity_retention_seconds",
            "countdown_seconds",
            "pairing_window_seconds",
            "message_cache_seconds",
        }:
            if not isinstance(value, int) or value <= 0:
                raise HTTPException(
                    status_code=400, detail=f"配置项 {key} 必须为正整数"
                )

        set_config_value(key, value)

    if "countdown_seconds" in updates and not state["triggered"]:
        cfg = get_config()
        state["deadline"] = time.time() + cfg["countdown_seconds"]

    logger.info("配置更新请求已处理: %s", sorted(updates))
    return get_config()
