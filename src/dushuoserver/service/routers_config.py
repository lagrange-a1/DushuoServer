"""配置管理路由。"""

import time

from fastapi import APIRouter, HTTPException, Request

from ..config import MUTABLE_CONFIG_KEYS
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

    if body.port is not None:
        raise HTTPException(status_code=400, detail="服务开放端口不可由客户端修改")

    updates = body.model_dump(exclude_none=True)
    updates.pop("port", None)

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

    return get_config()
