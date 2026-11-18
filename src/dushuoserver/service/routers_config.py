"""配置管理路由。"""

from fastapi import APIRouter, Depends, HTTPException

from ..logger import logger
from ..config import config
from ..database import set_config_value
from ..runtime import state
from ..schemas import ConfigUpdateRequest
from ..services import require_signature

router = APIRouter(tags=["config"])


def positive_integer_keys() -> set[str]:
    """取值为整数的运行时配置项，其值必须为正整数。

    须在运行时求值：配置项在数据库初始化后才被记为已设置的字段。
    """
    return {
        key
        for key in config.runtime.model_fields_set
        if isinstance(getattr(config.runtime, key), int)
    }


@router.get("/api/config")
def read_config(client_id: str = Depends(require_signature)) -> dict:
    """读取当前配置。"""
    return config.model_dump(mode="json")


@router.put("/api/config")
def update_config(
    body: ConfigUpdateRequest, client_id: str = Depends(require_signature)
) -> dict:
    """修改允许客户端修改的运行时配置项。"""
    updates = body.model_dump(exclude_none=True)
    positive_keys = positive_integer_keys()

    for key, value in updates.items():
        if key in positive_keys and value <= 0:
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
