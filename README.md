# 度朔·服务端

度朔山、度灵欢，引入鬼门关。

> _上古之人，有神荼、鬱壘者，昆弟二人，性能執鬼，居東海度朔山上，立桃樹下，簡閱百鬼。_
> —— 汉·王充《論衡·亂龍》

**度朔**是一个用以通过监控数字活动来进行生死判断的系统。

> 若我在某一刻停止了一切数字生活，这样的情况达到一定的时间，则我便已死亡。若我死亡，我的亡语将被执行。

本仓库为度朔系统的**服务端**，提供纯后端 HTTP API，不包含前端页面。

## 功能特性

- 启动后开始死亡判定倒计时。
- 接收客户端数字活动并重置倒计时。
- 提供服务端状态查询。
- 支持修改除服务端口外的运行配置。
- 倒计时结束时执行配置的最终任务。
- 提供配对窗口、二维码和桌面端配置码。
- 支持客户端之间通过短报文缓存进行通信。

## 技术栈

- Python 3.10+
- FastAPI
- Uvicorn
- SQLite
- Pydantic
- pytest / FastAPI TestClient

## 项目结构

```text
src/
└── dushuoserver/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── config.py
    ├── database.py
    ├── main.py
    ├── runtime.py
    ├── schemas.py
    ├── services.py
    ├── default_config.toml
    └── service/
        └── routers_*.py
tests/
docs/
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

## 命令行参数

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
| `--activity-retention-seconds` | 覆盖数字活动保留时间 |
| `--countdown-seconds` | 覆盖死亡判定倒计时时间 |
| `--final-task` | 覆盖最终任务脚本 |
| `--pairing-window-seconds` | 覆盖配对窗口时间 |
| `--message-cache-seconds` | 覆盖短报文缓存时间 |

示例：

```bash
dushuoserver --host 127.0.0.1 --port 8080 --database ./data/dushuo.db
dushuoserver --config ./my_config.toml --reload
```

默认监听 `0.0.0.0:8000`，数据库文件为当前工作目录下的 `dushuo.db`。

默认配置位于 `src/dushuoserver/default_config.toml`。服务启动时会将默认值写入数据库；客户端只能修改允许修改的配置项，服务端口不可修改。如果通过 `--config` 指定配置文件，则使用该文件作为默认配置来源。

## 配置

可由客户端修改的配置项：

- `activity_retention_seconds`
- `countdown_seconds`
- `final_task`
- `pairing_window_seconds`
- `message_cache_seconds`

固定配置项：

- `port`

## API

详见 `docs/API-Reference.md`。所有业务接口均需要配对密钥，可通过 HTTP 头 `X-Pairing-Key` 或查询参数 `key` 传递。`/health` 与配对页面除外。

主要接口：

- `GET /health`：健康检查。
- `GET /`：配对页面，仅在配对窗口内可用。
- `GET /api/pairing`：获取配对信息。
- `POST /api/activity`：上报数字活动。
- `GET /api/status`：查询服务状态。
- `GET /api/config`：读取配置。
- `PUT /api/config`：修改可修改配置。
- `POST /api/message`：短报文获取、设置与删除。

## 测试

```bash
uv run pytest
python -m compileall src
```

测试使用独立的临时 SQLite 数据库，不会修改项目根目录下的 `dushuo.db`。

## 开发

代码格式化：

```bash
black src tests
```

新增接口后，请同步更新 `docs/API-Reference.md`。提交前至少运行 `uv run pytest` 与 `python -m compileall src`。

## 安全说明

- `final_task` 会通过 shell 执行，请仅配置可信脚本。
- 配对密钥在每次进程启动时重新生成。
- 服务端口不可由客户端修改。
- 配对密钥应妥善保管，所有业务接口均需要配对密钥。
