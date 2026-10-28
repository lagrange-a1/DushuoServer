"""度朔服务端业务服务。"""

import base64
import json
import secrets
import subprocess
import time
from typing import Any, Optional

from fastapi import HTTPException, Request

from .config import FINAL_TASK_TIMEOUT_SECONDS
from .database import get_config
from .runtime import state


def require_key(request: Request) -> None:
    """校验请求中的配对密钥。"""
    supplied = request.headers.get("X-Pairing-Key") or request.query_params.get("key")

    if not supplied or not secrets.compare_digest(supplied, state["pairing_key"]):
        raise HTTPException(status_code=403, detail="配对密钥不匹配")


def execute_final_task() -> None:
    """执行配置中的最终任务脚本。"""
    cfg = get_config()
    script = cfg.get("final_task", "")

    if not script:
        return

    try:
        subprocess.run(
            script,
            shell=True,
            check=False,
            timeout=FINAL_TASK_TIMEOUT_SECONDS,
        )
    except Exception:
        # 最终任务失败时保留服务运行，避免整个服务退出
        pass


def pairing_open() -> bool:
    """判断配对窗口是否仍然开放。"""
    cfg = get_config()
    return time.time() < state["started_at"] + cfg["pairing_window_seconds"]


def pairing_payload() -> dict[str, str]:
    """生成配对数据与桌面端配置码。"""
    cfg = get_config()
    payload = {
        "host": f"127.0.0.1:{cfg['port']}",
        "key": state["pairing_key"],
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return {
        "host": payload["host"],
        "key": payload["key"],
        "config_code": encoded,
        "pairing_uri": f"dushuo://pair?{encoded}",
    }


def pairing_qr_html() -> str:
    """生成配对页面中的二维码 HTML。"""
    encoded = pairing_payload()["config_code"]

    try:
        import qrcode
        from io import BytesIO

        image = qrcode.make(f"dushuo://pair?{encoded}")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        qr_src = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        return f'<img src="{qr_src}" alt="配对二维码" />'
    except Exception:
        return f"<p>配对数据：dushuo://pair?{encoded}</p>"
