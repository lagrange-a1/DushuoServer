"""度朔服务端应用装配。"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .logger import logger
from . import __appname__, __version__

logger.info("载入系统内容")

from .database import get_config, init_database
from .runtime import countdown_loop, state
from .services import execute_final_task
from .service.routers_health import router as health_router
from .service.routers_pairing import router as pairing_router
from .service.routers_activity import router as activity_router
from .service.routers_status import router as status_router
from .service.routers_config import router as config_router
from .service.routers_messages import router as messages_router

logger.info("载入网络服务端及路由模块")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：初始化数据库并启动倒计时。"""
    logger.info("正在初始化数据库")
    init_database()

    cfg = get_config()
    state["deadline"] = time.time() + cfg["countdown_seconds"]
    task = asyncio.create_task(countdown_loop(execute_final_task))
    logger.info("服务启动完成，死亡判定倒计时已启动")

    try:
        yield
    finally:
        task.cancel()
        logger.info("服务正在关闭")


app = FastAPI(
    title=__appname__,
    description="度朔系统之服务端，提供度朔中心调度功能",
    version=__version__,
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
    logger.error("发生未捕获异常 `{}` `{}`".format(request.method, request.url.path))
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )
