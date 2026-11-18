"""配置管理路由。"""

from fastapi import APIRouter, HTTPException

from ..logger import logger
from ..config import config
from ..database import set_config_value
from ..runtime import state
from ..schemas import ConfigUpdateRequest, SignedRequest
from ..services import parse_payload, verify_signed_request

router = APIRouter(tags=["config"])

# 必须为正整数的配置项。
POSITIVE_INTEGER_KEYS = {
    key
    for key in config.runtime.model_fields_set
    if isinstance(getattr(config.runtime, key), int)
}


@router.post("/api/config")
def read_config(body: SignedRequest) -> dict:
    """读取当前配置。"""
    verify_signed_request(body)

    return config.model_dump(mode="json")


@router.put("/api/config")
def update_config(body: SignedRequest) -> dict:
    """修改允许客户端修改的运行时配置项。"""
    verify_signed_request(body)
    updates = parse_payload(body, ConfigUpdateRequest).model_dump(exclude_none=True)

    for key, value in updates.items():
        if key in POSITIVE_INTEGER_KEYS and value <= 0:
            raise HTTPException(
                status_code=400, detail="配置项`{}`必须为正整数".format(key)
            )

        try:
            set_config_value(key, value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    if "death_countdown" in updates and not state.triggered:
        state.update_deadline()

    logger.info("配置更新请求已处理：{}".format(sorted(updates)))
    return config.model_dump(mode="json")
