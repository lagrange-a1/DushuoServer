# 度朔·服务端（Dushuo Server）开发指南

## 项目概览

**度朔**是一个通过监控数字活动进行生死判断的系统。本仓库为度朔系统的服务端，使用 Python 与 FastAPI 提供 HTTP API，使用 SQLite 保存运行时数据。

服务端负责：

- 启动后开始死亡判定倒计时；
- 接收客户端数字活动并重置倒计时；
- 提供服务端状态查询；
- 允许客户端修改除服务端口外的运行配置；
- 倒计时结束时执行配置的最终任务；
- 提供配对窗口、二维码和桌面端配置码；
- 通过 SQLite 缓存支持客户端之间的短报文通信。

## 技术栈

- Python 3.10+
- FastAPI
- Uvicorn
- SQLite
- Pydantic
- pytest / FastAPI TestClient
- Black

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

主要模块职责：

- `app.py`：FastAPI 应用装配、生命周期管理、全局异常处理。
- `main.py`：命令行参数解析与服务启动。
- `config.py`：默认配置、可修改配置项、数据库路径、配置覆盖项。
- `database.py`：SQLite 连接、表结构初始化、配置与业务数据访问。
- `runtime.py`：运行时状态与后台倒计时循环。
- `services.py`：配对密钥校验、最终任务执行、配对数据与二维码生成。
- `schemas.py`：请求与响应模型。
- `service/routers_*.py`：按功能划分的 HTTP 路由。

## 运行流程

1. 服务启动并初始化 SQLite 数据库。
2. 读取默认配置与命令行覆盖项，写入数据库。
3. 生成本次进程使用的配对密钥。
4. 启动后台倒计时任务。
5. 开放配对窗口，提供二维码与桌面端配置码。
6. 接收客户端活动、状态查询、配置修改和短报文请求。
7. 倒计时结束时执行配置的最终任务。

活动上报会重置倒计时，但仅在最终任务尚未触发时生效。

## 配置说明

默认配置位于 `src/dushuoserver/default_config.toml`。

可由客户端修改的配置项：

- `activity_retention_seconds`
- `countdown_seconds`
- `final_task`
- `pairing_window_seconds`
- `message_cache_seconds`

固定配置项：

- `port`：服务开放端口，不可由客户端修改。

命令行可通过 `--port`、`--activity-retention-seconds`、`--countdown-seconds`、`--final-task`、`--pairing-window-seconds`、`--message-cache-seconds` 等参数覆盖默认配置。

`final_task` 会通过 shell 执行，请仅配置可信脚本。

## 数据库

服务使用 SQLite 保存：

- `config`：运行时可修改配置；
- `activities`：客户端数字活动记录；
- `messages`：短报文缓存；
- `message_fetches`：设备获取短报文的记录。

数据库连接通过 `get_connection()` 上下文管理器创建，确保使用后关闭。测试环境通过修改 `config.DB_PATH` 使用独立临时数据库。

## 常用命令

安装依赖：

```bash
uv sync
```

安装测试依赖：

```bash
uv sync --extra test
```

启动服务：

```bash
python -m dushuoserver
```

或使用安装后的命令：

```bash
dushuoserver --host 0.0.0.0 --port 8000
```

直接使用 Uvicorn：

```bash
uvicorn dushuoserver.app:app --app-dir src --host 0.0.0.0 --port 8000
```

代码格式化：

```bash
black src tests
```

运行测试：

```bash
uv run pytest
```

编译检查：

```bash
python -m compileall src
```

## 开发约定

### 新增功能

- 新增接口时，优先在 `src/dushuoserver/service/routers_*.py` 中添加路由。
- 业务逻辑应放在 `src/dushuoserver/services.py` 或独立服务模块中。
- 数据库访问应集中在 `src/dushuoserver/database.py`。
- 默认配置文件为 `src/dushuoserver/default_config.toml`；`src/dushuoserver/config.py` 负责读取、校验并维护可修改项。
- 请求与响应模型应放在 `src/dushuoserver/schemas.py`。
- 新增或修改接口后，同步更新 `docs/API-Reference.md`。

### 日志

- 各模块使用 `logging.getLogger(__name__)` 获取 logger。
- 避免在高频请求路径输出过多 `info` 日志，调试信息使用 `debug`。
- 异常处理应记录足够上下文，但不泄露敏感信息。

### 类型标注

- 新增函数应提供参数与返回值类型标注。
- 兼容 Python 3.10，必要时使用 `typing.Optional` 等兼容写法。
- 避免无必要的 `Any`，但在 FastAPI/SQLite 等边界处可适度使用。

### 代码风格

1. 使用 Black 风格格式化代码。
2. 使用四空格缩进。
3. 类名使用 `PascalCase`。
4. 变量、函数使用 `snake_case`。
5. 常量使用 `UPPER_CASE`。
6. 文档字符串、注释使用汉语。
7. 提交前至少运行 `uv run pytest` 与 `python -m compileall src`。

文档字符串风格：

```python
class ClassName:
    """
    类描述
    """

    attribute_name = "value"
    """类属性描述"""

    def function_name(self, arg1: int, arg2: str) -> None:
        """
        函数功能描述

        参数
        ====
        arg1 : int
            参数功能描述
        arg2 : str
            可以为多行

        返回
        ====
        None
            无返回值
        """
        pass
```

## 测试

- 自动化测试位于 `tests/`。
- 测试使用 FastAPI `TestClient`。
- 每个测试使用独立临时 SQLite 数据库，不会修改项目根目录下的 `dushuo.db`。
- 手动验证可使用 `GET /health`、`GET /`、`GET /api/status` 等接口。

## 安全说明

- `final_task` 通过 shell 执行，仅应配置可信脚本。
- 配对密钥在每次进程启动时重新生成，通过 `X-Pairing-Key` 请求头或 `key` 查询参数传递。
- 服务端口不可由客户端修改。
- 所有业务接口均需要配对密钥；`/health` 与配对页面除外。
