"""配对路由。"""

import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..database import get_config
from ..runtime import state
from ..services import pairing_open, pairing_payload, pairing_qr_html, require_key

router = APIRouter(tags=["pairing"])


@router.get("/", response_class=HTMLResponse)
def pairing_page() -> str:
    """返回配对页面。仅在配对窗口内可用。"""
    if not pairing_open():
        raise HTTPException(status_code=410, detail="配对窗口已关闭")

    payload = pairing_payload()
    qr_html = pairing_qr_html()

    return f"""
    <html>
      <head><meta charset="utf-8"><title>度朔配对</title></head>
      <body>
        <h1>度朔服务端配对</h1>
        {qr_html}
        <p>桌面端配置码：{payload['config_code']}</p>
        <p>配对密钥：{payload['key']}</p>
      </body>
    </html>
    """


@router.get("/api/pairing")
def pairing_info(request: Request) -> dict:
    """返回服务端地址、配对密钥、配置码和窗口剩余时间。"""
    require_key(request)

    if not pairing_open():
        raise HTTPException(status_code=410, detail="配对窗口已关闭")

    cfg = get_config()
    payload = pairing_payload()
    return {
        **payload,
        "window_remaining_seconds": max(
            0, state["started_at"] + cfg["pairing_window_seconds"] - time.time()
        ),
    }
