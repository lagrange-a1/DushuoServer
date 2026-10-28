"""度朔服务端应用装配。"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .database import get_config, init_database
from .runtime import countdown_loop, state
from .services import execute_final_task
from .service.routers_health import router as health_router
from .service.routers_pairing import router as pairing_router
from .service.routers_activity import router as activity_router
from .service.routers_status import router as status_router
from .service.routers_config import router as config_router
from .service.routers_messages import router as messages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化数据库并启动倒计时。"""
    init_database()

    cfg = get_config()
    state["deadline"] = time.time() + cfg["countdown_seconds"]
    task = asyncio.create_task(countdown_loop(execute_final_task))

    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="度朔服务端",
    description="用于通过监控数字活动进行生死判断的服务端。",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(pairing_router)
app.include_router(activity_router)
app.include_router(status_router)
app.include_router(config_router)
app.include_router(messages_router)


@app.exception_handler(Exception)
def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """统一处理未捕获异常。"""
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )
