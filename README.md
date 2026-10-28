
# 度朔·服务端

度朔山、度灵欢，引入鬼门关。

> _上古之人，有神荼、鬱壘者，昆弟二人，性能執鬼，居東海度朔山上，立桃樹下，簡閱百鬼。_
> —— 汉·王充《論衡·亂龍》

**度朔**是一个用以通过监控数字活动来进行生死判断的一个系统。

> 若我在某一刻停止了一切数字生活，这样的情况达到一定的时间，则我便已死亡。若我死亡，我的亡语将被执行。

## 架构设计

**_本仓库内为度朔系统的服务端代码。_**

我们使用 Python 语言进行开发，并使用 FastAPI 框架运行 Web 服务、使用 SQLite 数据库进行数据存储。

服务端为纯后端服务，不提供任何前端页面。

## 功能特性

- 启动后开始死亡判定倒计时。
- 接收客户端数字活动并重置倒计时。
- 提供服务端状态查询。
- 支持修改除服务端口外的运行配置。
- 倒计时结束时执行配置的最终任务。
- 提供配对窗口、二维码和桌面端配置码。
- 支持客户端之间通过短报文缓存进行通信。

## 项目结构

```text
src/
├── main.py
└── dushuoserver/
    ├── __main__.py
    ├── main.py
    ├── app.py
    ├── config.py
    ├── database.py
    ├── runtime.py
    ├── schemas.py
    ├── services.py
    └── service/
        └── routers_*.py
```

## 快速开始

安装运行时依赖：

```bash
uv sync
```

安装测试依赖：

```bash
uv sync --extra test
```

也可以通过 pip 安装本项目，并使用命令行入口启动：

```bash
pip install .
dushuoserver --host 0.0.0.0 --port 8000
```

启动服务：

```bash
python -m dushuoserver
```

也可以直接使用 Uvicorn：

```bash
uvicorn dushuoserver.app:app --app-dir src --host 0.0.0.0 --port 8000
```

### 命令行参数

`dushuoserver` / `python src/main.py` 支持常见服务端启动参数：

| 参数 | 说明 |
| --- | --- |
| `--host` | 监听地址，默认 `0.0.0.0` |
| `--port` | 监听端口；未指定时使用默认配置中的 `port` |
| `--workers` | Uvicorn 工作进程数，默认 `1` |
| `--reload` | 开启开发模式热重载 |
| `--log-level` | 日志级别 |
| `--no-access-log` | 关闭访问日志 |
| `--config` / `--default-config` | 默认配置 TOML 文件路径 |
| `--database` / `--db-path` | SQLite 数据库文件路径 |

示例：

```bash
dushuoserver --host 127.0.0.1 --port 8080 --database ./data/dushuo.db
dushuoserver --config ./my_config.toml --reload
```

默认监听 `0.0.0.0:8000`，数据库文件为当前工作目录下的 `dushuo.db`。

默认配置位于 `src/dushuoserver/default_config.toml`，格式为 TOML。服务启动时会将其中的默认值写入数据库；客户端只能修改允许修改的配置项，服务端口不可修改。如果通过 `--config` 指定配置文件，则使用该文件作为默认配置来源。

## 测试

```bash
uv run pytest
python -m compileall src
```

## 接口文档

详见 `docs/API-Reference.md`。

## 安全说明

`final_task` 会通过 shell 执行，请仅配置可信脚本。服务端端口不可由客户端修改。
