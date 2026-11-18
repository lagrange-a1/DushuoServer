"""配对路由。"""

import time

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse

from ..runtime import state
from ..schemas import PairRequest
from ..services import (
    pairing_payload,
    pairing_qr_html,
    register_client,
    reopen_pairing_window,
    require_signature,
    verify_pairing_code,
)

router = APIRouter(tags=["pairing"])


@router.get("/", response_class=HTMLResponse)
def pairing_page() -> str:
    """返回配对页面。仅在配对窗口内可用。"""
    if state.pairing_key is None:
        raise HTTPException(status_code=410, detail="配对窗口已关闭")

    payload = pairing_payload()
    qr_html = pairing_qr_html()

    return """
    <html>
      <head><meta charset="utf-8"><title>度朔配对</title></head>
      <body>
        <h1>度朔服务端配对</h1>
        {qr_html}
        <p>服务端地址：{host}</p>
        <p>配对码：{pairing_code}</p>
        <p>桌面端配置码：{config_code}</p>
      </body>
    </html>
    """.format(
        qr_html=qr_html,
        host=payload["host"],
        pairing_code=payload["pairing_code"],
        config_code=payload["config_code"],
    )


@router.get("/api/pairing")
def pairing_info() -> dict:
    """返回配对信息与窗口剩余时间。仅在配对窗口内可用。"""
    if state.pairing_key is None:
        raise HTTPException(status_code=410, detail="配对窗口已关闭")

    payload = pairing_payload()
    return {
        **payload,
        "window_remaining_seconds": max(
            0, int(state.pairing_key_expires_at - time.time())
        ),
    }


@router.post("/api/pair", status_code=201)
def pair(response: Response, body: PairRequest) -> dict:
    """处理客户端配对请求，登记客户端公钥。

    全新的客户端返回 201；更换公钥或公钥已登记时返回 200，
    处置结果由响应中的 `action` 标示。
    """
    verify_pairing_code(body.pairing_code)

    action = register_client(body.client_id, body.public_key)
    if action != "created":
        response.status_code = 200

    return {
        "paired": True,
        "action": action,
        "client_id": body.client_id,
    }


@router.post("/api/pairing/reopen")
def reopen_pairing(client_id: str = Depends(require_signature)) -> dict:
    """由已配对的客户端重新开放配对窗口。"""
    reopen_pairing_window()

    payload = pairing_payload()
    return {
        "reopened_by": client_id,
        **payload,
        "window_remaining_seconds": max(
            0, int(state.pairing_key_expires_at - time.time())
        ),
    }
