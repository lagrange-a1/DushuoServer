"""度朔服务端启动入口。"""

from dushuoserver.app import app

import uvicorn

if __name__ == "__main__":
    # 默认监听所有网卡的 8000 端口，并开启开发模式热重载。
    uvicorn.run("dushuoserver.app:app", host="0.0.0.0", port=8000, reload=True)
