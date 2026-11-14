# 度朔·服务端

度朔山、度灵欢，引入鬼门关。

> _上古之人，有神荼、鬱壘者，昆弟二人，性能執鬼，居東海度朔山上，立桃樹下，簡閱百鬼。_
> —— 汉·王充《論衡·亂龍》

**度朔**是一个用以通过监控数字活动来进行生死判断的系统。

> 若我在某一刻停止了一切数字生活，这样的情况达到一定的时间，则我便已死亡。若我死亡，我的亡语将被执行。

本仓库为度朔系统的**服务端**，提供纯后端 HTTP API，不包含前端页面。

## 功能

* 启动后开始倒计时
* 接收客户端数字活动并重置倒计时
* 倒计时结束时执行配置的任务

## 启动

### 安装依赖

1. 使用 uv：

```bash
uv sync # 可通过 `--extra dev` 参数安装开发测试依赖
```

### 启动服务

1. 使用 uv：

```bash
uv run dushuoserver
```

2. 纯 Python：

```bash
python -m dushuoserver
```

3. 也可以直接使用 Uvicorn：

```bash
uvicorn dushuoserver.app:app --app-dir src --host 0.0.0.0 --port 18470
```

4. 也可以通过 pip 安装本项目，并使用命令行入口启动：

```bash
pip install .
dushuoserver --help
```

### 查看参数

在启动指令后增加 `--help` 参数查看参数说明，例如：

```bash
dushuoserver --help
```

## 配置

服务端启动时，读取配置参数的优先级为：**默认配置 < 配置文件 < 命令行参数 < 服务端现有数据库**

其中，数据库仅会存储运行时参数。以下是默认配置文件：

```toml
host_address = "0.0.0.0"    # 服务端地址
host_port    = 18470        # 服务端端口
log_level    = "info"      # 全局日志等级，可以是 DEBUG, INFO, WARNING, ERROR, CRITICAL
db_path      = "dushuodb.sqlite3" # 数据库路径

[uvicron]
    workers    = 1  # uvicorn 工作进程数
    hot_reload  = false  # 是否开启热重载
    access_log = true   # 是否开启访问日志

[runtime]   # 运行时参数可在服务端启动后更改，从配置文件读取之后，也会在数据库中重新读取一遍，优先级为 数据库 > 命令行传参 > 配置文件 > 默认参数
    activity_cache_duration = 86400 # 客户端活动消息的缓存时长（秒）
    death_countdown         = 86400 # 死亡判定倒计时（秒）
    execution_task          = ""    # 最终任务执行命令
    message_cache_duration  = 3600  # 短报文缓存时长（秒）
    pairing_window_time     = 300   # 配对窗口时长（秒）

```

启动服务时，可以在命令行通过 `--config` 参数指定配置文件路径，例如：

```bash
dushuoserver --config /path/to/config.toml
```

执行服务端程序时，可通过 `--help` 查看参数说明。

## API

详见 `docs/API-Reference.md` 。所有业务接口均需要配对密钥，可通过 HTTP 头 `X-Pairing-Key` 或查询参数 `key` 传递。 `/health` 与配对页面除外。
