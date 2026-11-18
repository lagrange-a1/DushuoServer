"""度朔服务端请求模型。"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PairRequest(BaseModel):
    """客户端配对请求模型。"""

    pairing_code: str = Field(..., min_length=1, description="配对码")
    client_id: str = Field(..., min_length=1, description="客户端标识")
    public_key: str = Field(..., description="客户端公钥（PEM 文本）")


class SignedRequest(BaseModel):
    """带签名的业务请求模型。

    客户端须以私钥对 client_id、timestamp 与 payload 三个字段组成的
    规范化 JSON 串签名，并将签名以 base64 编码填入 signature 字段。
    """

    client_id: str = Field(..., description="客户端标识")
    timestamp: int = Field(..., description="请求发出时的 Unix 时间戳（秒）")
    payload: dict[str, Any] = Field(..., description="业务数据，结构见各接口说明")
    signature: str = Field(..., description="规范化请求的签名（base64）")


class ActivityRequest(BaseModel):
    """客户端上报数字活动的载荷模型。"""

    activity: str = Field("", description="数字活动描述")
    timestamp: Optional[float] = Field(None, description="客户端上报时间戳")


class ConfigUpdateRequest(BaseModel):
    """客户端修改运行时配置的载荷模型。"""

    activity_cache_duration: Optional[int] = None
    death_countdown: Optional[int] = None
    execution_task: Optional[str] = None
    message_cache_duration: Optional[int] = None
    pairing_window_time: Optional[int] = None


class MessageRequest(BaseModel):
    """短报文载荷模型。"""

    content: Optional[str] = Field(None, description="消息内容；为空表示获取消息")
