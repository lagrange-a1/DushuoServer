"""度朔服务端请求模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class PairRequest(BaseModel):
    """客户端配对请求模型。"""

    pairing_code: str = Field(..., min_length=1, description="配对码")
    client_id: str = Field(..., min_length=1, description="客户端标识")
    public_key: str = Field(..., description="客户端公钥（PEM 文本）")


class ActivityRequest(BaseModel):
    """客户端上报数字活动的请求模型。"""

    activity: str = Field("", description="数字活动描述")
    timestamp: Optional[float] = Field(None, description="客户端上报时间戳")


class ConfigUpdateRequest(BaseModel):
    """客户端修改运行时配置的请求模型。"""

    activity_cache_duration: Optional[int] = None
    death_countdown: Optional[int] = None
    execution_task: Optional[str] = None
    message_cache_duration: Optional[int] = None
    pairing_window_time: Optional[int] = None
    signature_time_tolerance: Optional[int] = None


class MessageRequest(BaseModel):
    """客户端发送短报文的请求模型。"""

    content: str = Field(..., min_length=1, description="消息内容")
