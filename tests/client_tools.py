"""度朔测试客户端共用工具：密钥生成与签名请求构造。"""

import base64
import json
import time
from typing import Any, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_keypair() -> tuple[bytes, bytes]:
    """生成一对 Ed25519 密钥，返回（私钥 PEM，公钥 PEM）。"""
    private_key = Ed25519PrivateKey.generate()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def load_private_key(private_pem: bytes) -> Ed25519PrivateKey:
    """从 PEM 文本加载 Ed25519 私钥。"""
    key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("这不是一把 Ed25519 私钥")
    return key


def canonical_request_data(client_id: str, timestamp: int, payload: dict) -> bytes:
    """按服务端约定生成规范化请求字节串。"""
    return json.dumps(
        {"client_id": client_id, "timestamp": timestamp, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_signed_body(
    client_id: str,
    private_pem: bytes,
    payload: dict[str, Any],
    timestamp: Optional[int] = None,
) -> dict[str, Any]:
    """构造一个带签名的业务请求体。"""
    if timestamp is None:
        timestamp = int(time.time())

    signature = load_private_key(private_pem).sign(
        canonical_request_data(client_id, timestamp, payload)
    )

    return {
        "client_id": client_id,
        "timestamp": timestamp,
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }
