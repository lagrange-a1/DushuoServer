"""度朔测试客户端共用工具：密钥生成与签名请求头构造。"""

import base64
import hashlib
import json
import time
from typing import Any, Optional

import httpx
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


def canonical_request_data(
    method: str, path: str, client_id: str, timestamp: int, body: bytes
) -> bytes:
    """按服务端约定生成规范化请求字节串。"""
    return "\n".join(
        [
            method.upper(),
            path,
            client_id,
            str(timestamp),
            hashlib.sha256(body).hexdigest(),
        ]
    ).encode("utf-8")


def sign_request_headers(
    client_id: str,
    private_pem: bytes,
    method: str,
    path: str,
    body: bytes = b"",
    timestamp: Optional[int] = None,
) -> dict[str, str]:
    """生成业务请求所需的三个签名请求头。"""
    if timestamp is None:
        timestamp = int(time.time())

    signature = load_private_key(private_pem).sign(
        canonical_request_data(method, path, client_id, timestamp, body)
    )

    return {
        "X-Client-Id": client_id,
        "X-Timestamp": str(timestamp),
        "X-Signature": base64.b64encode(signature).decode(),
    }


def request_signed(
    http: httpx.Client,
    method: str,
    path: str,
    client_id: str,
    private_pem: bytes,
    json_body: Optional[dict[str, Any]] = None,
    timestamp: Optional[int] = None,
) -> httpx.Response:
    """发送一个带签名的业务请求。

    请求体先自行序列化为字节再签名，以确保签名内容与实际发送的字节完全一致。
    """
    body = (
        b""
        if json_body is None
        else json.dumps(json_body, ensure_ascii=False).encode("utf-8")
    )
    headers = sign_request_headers(
        client_id, private_pem, method, path, body, timestamp
    )

    if not body:
        return http.request(method, path, headers=headers)

    headers["Content-Type"] = "application/json"
    return http.request(method, path, content=body, headers=headers)
