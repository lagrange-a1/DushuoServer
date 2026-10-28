"""度朔服务端请求模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class ActivityRequest(BaseModel):
    """客户端上报数字活动的请求模型。"""

    client_id: str = Field(..., description="客户端标识")
    activity: str = Field("", description="数字活动描述")
    timestamp: Optional[float] = Field(None, description="客户端上报时间戳")


class ConfigUpdateRequest(BaseModel):
    """客户端修改服务配置的请求模型。"""

    activity_retention_seconds: Optional[int] = None
    countdown_seconds: Optional[int] = None
    final_task: Optional[str] = None
    pairing_window_seconds: Optional[int] = None
    message_cache_seconds: Optional[int] = None
    port: Optional[int] = None


class MessageRequest(BaseModel):
    """短报文请求模型。"""

    device_id: str = Field(..., description="设备标识")
    content: Optional[str] = Field(None, description="消息内容；为空表示获取消息")
