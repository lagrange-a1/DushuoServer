"""度朔服务端业务服务。"""

import base64
import hashlib
import json
import secrets
import subprocess
import time
import qrcode
from typing import Optional
from io import BytesIO

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from fastapi import HTTPException, Request

from .logger import logger
from .config import config
from .database import get_client_public_key, upsert_client
from .runtime import state

# 允许客户端登记的公钥类型。
SupportedPublicKey = (
    rsa.RSAPublicKey | ed25519.Ed25519PublicKey | ec.EllipticCurvePublicKey
)


def canonical_request_data(
    method: str, path: str, client_id: str, timestamp: int, body: bytes
) -> bytes:
    """生成请求的规范化字节串，客户端须使用私钥对其签名。

    签名内容依次为请求方法、请求路径、客户端标识、时间戳与请求体的
    SHA-256 摘要，以换行符连接；查询参数不参与签名。
    """
    return "\n".join(
        [
            method.upper(),
            path,
            client_id,
            str(timestamp),
            hashlib.sha256(body).hexdigest(),
        ]
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


async def require_signature(request: Request) -> str:
    """校验签名请求头，通过校验时返回客户端标识。

    签名凭证置于 `X-Client-Id`、`X-Timestamp` 与 `X-Signature` 三个请求头中，
    因此 `GET`、`DELETE` 一类不带请求体的接口同样能够完成鉴权。
    """
    client_id = request.headers.get("X-Client-Id")
    timestamp_text = request.headers.get("X-Timestamp")
    signature_text = request.headers.get("X-Signature")

    if not client_id or not timestamp_text or not signature_text:
        logger.warning("请求`{}`缺少签名请求头".format(request.url.path))
        raise HTTPException(status_code=401, detail="缺少签名请求头")

    try:
        timestamp = int(timestamp_text)
    except ValueError:
        logger.warning("客户端`{}`的签名时间戳`{}`不是整数".format(client_id, timestamp_text))
        raise HTTPException(status_code=401, detail="签名时间戳不是整数")

    if abs(time.time() - timestamp) > config.runtime.signature_time_tolerance:
        logger.warning("客户端`{}`的请求时间戳超出允许偏差".format(client_id))
        raise HTTPException(status_code=401, detail="请求时间戳超出允许偏差")

    pem_text = get_client_public_key(client_id)
    if pem_text is None:
        logger.warning("客户端`{}`尚未配对".format(client_id))
        raise HTTPException(status_code=401, detail="客户端尚未配对")

    try:
        signature = base64.b64decode(signature_text, validate=True)
    except Exception:
        logger.warning("客户端`{}`的签名不是有效的 Base64 数据".format(client_id))
        raise HTTPException(status_code=401, detail="签名不是有效的 Base64 数据")

    body = await request.body()
    data = canonical_request_data(
        request.method, request.url.path, client_id, timestamp, body
    )

    try:
        verify_signature(load_public_key(pem_text), data, signature)
    except InvalidSignature:
        logger.warning("客户端`{}`请求`{}`的签名验证失败".format(client_id, request.url.path))
        raise HTTPException(status_code=401, detail="签名验证失败")

    return client_id


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
