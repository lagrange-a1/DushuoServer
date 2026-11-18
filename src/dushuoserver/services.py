"""度朔服务端业务服务。"""

import base64
import json
import secrets
import subprocess
import time
import qrcode
from typing import Any, Optional, TypeVar
from io import BytesIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from .logger import logger
from .config import config
from .database import get_client_public_key, upsert_client
from .runtime import state
from .schemas import SignedRequest

# 允许客户端登记的公钥类型。
SupportedPublicKey = (
    rsa.RSAPublicKey | ed25519.Ed25519PublicKey | ec.EllipticCurvePublicKey
)

T = TypeVar("T", bound=BaseModel)


def canonical_request_data(
    client_id: str, timestamp: int, payload: dict[str, Any]
) -> bytes:
    """生成请求的规范化字节串，客户端须使用私钥对其签名。"""
    return json.dumps(
        {"client_id": client_id, "timestamp": timestamp, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_public_key(pem_text: str) -> SupportedPublicKey:
    """加载 PEM 格式公钥，无法解析或类型不受支持时抛出 400。"""
    try:
        key = serialization.load_pem_public_key(pem_text.encode("utf-8"))
    except Exception:
        logger.warning("无法加载公钥：{}".format(pem_text))
        raise HTTPException(status_code=400, detail="公钥格式无法解析")

    if not isinstance(
        key, (rsa.RSAPublicKey, ed25519.Ed25519PublicKey, ec.EllipticCurvePublicKey)
    ):
        logger.warning("不支持`{}`类型的公钥".format(key))
        raise HTTPException(
            status_code=400, detail="不支持的公钥类型，仅支持 Ed25519、RSA 与 ECDSA"
        )

    return key


def verify_signature(
    public_key: SupportedPublicKey, data: bytes, signature: bytes
) -> None:
    """使用客户端公钥校验签名，校验失败时抛出 InvalidSignature。"""
    if isinstance(public_key, rsa.RSAPublicKey):
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        logger.info("RSA 签名验证成功")
    elif isinstance(public_key, ed25519.Ed25519PublicKey):
        public_key.verify(signature, data)
        logger.info("Ed25519 签名验证成功")
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        logger.info("ECDSA 签名验证成功")
    else:
        logger.warning("不支持`{}`类型的公钥，无法验证签名".format(public_key))
        raise InvalidSignature("签名验证失败：不支持的公钥类型")


def verify_pairing_code(code: str) -> None:
    """校验配对码是否匹配且配对窗口仍然开放。"""
    key = state.pairing_key

    if key is None:
        logger.warning("无法获取配对码，配对窗口已关闭")
        raise HTTPException(status_code=410, detail="配对窗口已关闭")

    if not code or not secrets.compare_digest(code, key):
        logger.warning("传入配对码`{}`与现存配对码`{}`不匹配")
        raise HTTPException(status_code=403, detail="配对码不匹配")


def register_client(client_id: str, public_key: str) -> None:
    """登记客户端公钥，完成配对。"""
    load_public_key(public_key)
    upsert_client(client_id, public_key)
    logger.info("客户端`{}`完成配对".format(client_id))


def reopen_pairing_window() -> None:
    """重新开放配对窗口，生成新的配对码并重新计时。"""
    state.generate_pairing_key()
    logger.info("配对窗口已重新开放")


def verify_signed_request(body: SignedRequest) -> str:
    """校验签名请求，通过校验时返回客户端标识。"""
    if abs(time.time() - body.timestamp) > config.runtime.signature_time_tolerance:
        raise HTTPException(status_code=403, detail="请求时间戳超出允许偏差")

    pem_text = get_client_public_key(body.client_id)
    if pem_text is None:
        raise HTTPException(status_code=403, detail="客户端尚未配对")

    try:
        signature = base64.b64decode(body.signature, validate=True)
    except Exception:
        raise HTTPException(status_code=403, detail="签名不是有效的 Base64 数据")

    data = canonical_request_data(body.client_id, body.timestamp, body.payload)

    try:
        verify_signature(load_public_key(pem_text), data, signature)
    except InvalidSignature:
        raise HTTPException(status_code=403, detail="签名验证失败")

    return body.client_id


def parse_payload(body: SignedRequest, model: type[T]) -> T:
    """将签名请求中的业务数据解析为指定的载荷模型。"""
    try:
        return model.model_validate(body.payload)
    except ValidationError as exc:
        logger.warning(
            "无法解析`{timestamp}`时来自`{client_id}`的、由`{signature}`签名的载荷：\n{payload}".format(
                **body.model_dump(
                    mode="python",
                )
            )
        )
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False))


def execute_final_task():
    """执行配置中的最终任务脚本。"""
    script = config.runtime.execution_task.strip()

    if not script:
        logger.info("未配置最终任务，跳过执行")
        return

    logger.info("开始执行最终任务")
    try:
        subprocess.run(
            script,
            shell=True,
            check=False,
        )
        logger.info("最终任务执行完成")
    except subprocess.TimeoutExpired:
        logger.warning("最终任务执行超时，已终止")
    except Exception:
        logger.error("最终任务执行失败，服务继续运行")


def pairing_payload() -> dict[str, Optional[str]]:
    """生成配对数据与桌面端配置码。"""
    host_address = (
        config.host_address if config.host_address != "0.0.0.0" else "127.0.0.1"
    )
    payload = {
        "host": "{}:{}".format(host_address, config.host_port),
        "code": state.pairing_key,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    logger.info("已生成配对数据：{}".format(payload))
    return {
        "host": payload["host"],
        "pairing_code": payload["code"],
        "config_code": encoded,
        "pairing_uri": "dushuo://pair?{}".format(encoded),
    }


def pairing_qr_html() -> str:
    """生成配对页面中的二维码 HTML。"""
    encoded = pairing_payload()["config_code"]

    try:

        image = qrcode.make("dushuo://pair?{}".format(encoded))
        buffer = BytesIO()
        image.save(buffer, format="PNG")  # pyright: ignore[reportCallIssue]
        qr_src = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        return '<img src="{}" alt="配对二维码" />'.format(qr_src)
    except Exception:
        return "<p>配对数据：dushuo://pair?{}</p>".format(encoded)
