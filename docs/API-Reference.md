
# 度朔服务端 API 参考

度朔服务端提供纯后端 HTTP API，用于客户端配对、数字活动上报、生死状态查询、运行时配置管理以及客户端间短报文通信。

## 通用约定

- 基础地址：`http://<服务端地址>:<端口>`，默认端口 `18470`
- 请求与响应均为 JSON（`Content-Type: application/json`），编码 UTF-8；`GET /` 除外，返回 HTML
- 所有时间戳均为 Unix 时间戳（秒）
- 除 `GET /health`、`GET /`、`GET /api/pairing`、`POST /api/pair` 外，其余接口均须签名鉴权

## 鉴权

### 总体模型

鉴权分两步：

1. **配对**：在服务端启动或重新开放的窗口时间内，客户端提交配对码与自己的公钥完成配对；
2. **签名**：此后客户端的每个业务请求均由其私钥签名，服务端使用配对时登记的公钥校验。

配对码只在配对窗口内有效；业务请求中不含任何密钥明文。

### 配对窗口

- 配对码在服务端每次启动时生成，有效期由运行时配置 `pairing_window_time` 控制（默认 300 秒）
- 窗口开放期间，同一个配对码可供多个客户端依次配对，互不影响
- 窗口时长耗尽后，`GET /`、`GET /api/pairing` 与 `POST /api/pair` 均返回 `410`；此时任一已配对的客户端可调用 `POST /api/pairing/reopen` 重新开放窗口，服务端生成新的配对码并重新计时，无须重启服务端
- 获取配对码：
  - `GET /`：配对页面，展示二维码、服务端地址、配对码与桌面端配置码，适合人工查看
  - `GET /api/pairing`：以 JSON 返回同一份配对信息，适合客户端读取，仅在窗口开放时可用
- 二维码内容为 URI `dushuo://pair?{config_code}`，其中 `{config_code}` 是 `{"host": "...", "code": "..."}` 的 URL-safe Base64 编码

### 上传公钥

客户端在本地生成密钥对后调用 `POST /api/pair`：

```json
{
  "pairing_code": "配对码",
  "client_id": "客户端标识，由客户端自行确定",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
}
```

约定：

- `public_key` 须为 PEM（SubjectPublicKeyInfo）格式公钥文本，支持 Ed25519、RSA、ECDSA 三类算法
- `client_id` 配对成功后与公钥绑定；同一 `client_id` 再次配对会替换旧公钥，可用于更换设备密钥
- 窗口内可配对多个客户端，互不影响

### 签名请求

须签名接口的请求体结构：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `client_id` | string | 配对时使用的客户端标识 |
| `timestamp` | int | 请求发出时的 Unix 时间戳（秒），与服务端偏差超过 300 秒将被拒绝 |
| `payload` | object | 业务数据，结构见各接口说明 |
| `signature` | string | 签名，标准 Base64 编码 |

签名算法由公钥类型决定：

| 公钥类型 | 算法 |
| --- | --- |
| Ed25519 | 纯 Ed25519 签名 |
| RSA | RSASSA-PSS，摘要 SHA-256，MGF1-SHA256，盐长等于摘要长度 |
| ECDSA | ECDSA(SHA-256)，DER 编码签名 |

签名的计算步骤：

1. 构造规范化字节串（客户端与服务端约定一致）：

```python
data = json.dumps(
    {"client_id": client_id, "timestamp": timestamp, "payload": payload},
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
```

2. 使用私钥对 `data` 签名；
3. 将签名以标准 Base64 编码，填入 `signature` 字段。

完整示例（Python，`cryptography` + `httpx`）：

```python
import base64
import json
import time

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

SERVER = "http://127.0.0.1:18470"
CLIENT_ID = "my-phone"

private_key = Ed25519PrivateKey.generate()
public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

with httpx.Client(base_url=SERVER, timeout=10) as http:
    # 配对
    pairing_code = http.get("/api/pairing").json()["pairing_code"]
    http.post("/api/pair", json={
        "pairing_code": pairing_code,
        "client_id": CLIENT_ID,
        "public_key": public_pem,
    })

    # 签名请求
    timestamp = int(time.time())
    payload = {"activity": "正在打字"}
    data = json.dumps(
        {"client_id": CLIENT_ID, "timestamp": timestamp, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = base64.b64encode(private_key.sign(data)).decode()

    print(http.post("/api/activity", json={
        "client_id": CLIENT_ID,
        "timestamp": timestamp,
        "payload": payload,
        "signature": signature,
    }).json())
```

## 接口一览

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/health` | 无 | 健康检查 |
| `GET` | `/` | 无 | 配对页面（仅配对窗口内） |
| `GET` | `/api/pairing` | 无 | 配对信息（仅配对窗口内） |
| `POST` | `/api/pair` | 配对码 | 配对并登记公钥 |
| `POST` | `/api/pairing/reopen` | 签名 | 重新开放配对窗口 |
| `POST` | `/api/activity` | 签名 | 上报数字活动 |
| `POST` | `/api/status` | 签名 | 查询服务状态 |
| `POST` | `/api/config` | 签名 | 读取配置 |
| `PUT` | `/api/config` | 签名 | 修改运行时配置 |
| `POST` | `/api/message` | 签名 | 短报文的设置、获取与删除 |

## 接口详情

### GET /health

健康检查，始终可用。

响应：

```json
{"status": "ok"}
```

### GET /

配对页面，返回 HTML。窗口关闭后返回 `410`。页面内容包括二维码（`dushuo://pair?...`）、服务端地址、配对码与桌面端配置码。

### GET /api/pairing

返回配对信息，窗口关闭后返回 `410`：

```json
{
  "host": "127.0.0.1:18470",
  "pairing_code": "（当前配对码）",
  "config_code": "（host 与 code 的 URL-safe Base64 编码）",
  "pairing_uri": "dushuo://pair?...",
  "window_remaining_seconds": 299
}
```

### POST /api/pair

请求体见「上传公钥」。成功响应：

```json
{"paired": true, "client_id": "my-phone"}
```

错误：`403` 配对码不匹配；`410` 配对窗口已关闭；`400` 公钥无法解析或类型不受支持；`422` 字段校验失败。

### POST /api/pairing/reopen

须签名，载荷为空对象 `{}`。仅已配对的客户端可以调用，用于重新开放配对窗口：服务端生成新的配对码，并按 `pairing_window_time` 重新计时。窗口是否已经过期均可调用，已过期的窗口会被重新打开。

响应：

```json
{
  "reopened_by": "my-phone",
  "host": "127.0.0.1:18470",
  "pairing_code": "（新的配对码）",
  "config_code": "（host 与 code 的 URL-safe Base64 编码）",
  "pairing_uri": "dushuo://pair?...",
  "window_remaining_seconds": 300
}
```

新配对码供后续客户端配对使用；已配对客户端的签名鉴权不受影响。错误：`403` 客户端未配对或签名无效。

### POST /api/activity

载荷：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `activity` | string | 数字活动描述，可省略 |
| `timestamp` | number | 客户端上报时间戳，可省略（缺省为服务端时间） |

响应：

```json
{"accepted": true, "countdown_reset": true, "deadline": 1790000000}
```

服务端存活（未触发最终任务）时，收到活动即重置死亡判定倒计时；已触发后活动仍会被记录，但不再重置，此时 `countdown_reset` 为 `false`。

### POST /api/status

载荷为空对象 `{}`。响应：

```json
{
  "status": "alive",
  "countdown_remaining_seconds": 86399,
  "last_activity_at": null,
  "pairing_window_open": false,
  "pairing_window_remaining_seconds": 0,
  "config": { "……": "完整配置，同 POST /api/config" }
}
```

`status` 为 `alive` 或 `dead`。

### POST /api/config

载荷为空对象 `{}`，返回当前完整配置：

```json
{
  "host_address": "0.0.0.0",
  "host_port": 18470,
  "log_level": "INFO",
  "db_path": "dushuodb.sqlite3",
  "uvicron": {"workers": 1, "hot_reload": false, "access_log": true},
  "runtime": {
    "activity_cache_duration": 86400,
    "death_countdown": 86400,
    "execution_task": "",
    "message_cache_duration": 3600,
    "pairing_window_time": 300,
    "signature_time_tolerance": 300
  }
}
```

### PUT /api/config

载荷为需要修改的运行时配置项，全部可选，只提交要修改的字段：

```json
{"death_countdown": 3600, "execution_task": "echo 已死亡"}
```

- 可修改字段：`activity_cache_duration`、`death_countdown`、`execution_task`、
  `message_cache_duration`、`pairing_window_time`、`signature_time_tolerance`
- 时长类字段必须为正整数，否则返回 `400`
- 修改 `death_countdown` 且尚未触发最终任务时，倒计时立即按新值重置
- 成功后返回更新后的完整配置（同 `POST /api/config`）

### POST /api/message

载荷：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `content` | string | 消息内容；为空或省略表示获取消息 |

短报文协议（以「当前消息」指服务端缓存中的最新一条短报文）：

| 请求 `content` | 当前缓存 | 响应 action | 效果 |
| --- | --- | --- | --- |
| 空 | 无 | `empty` | 无消息可取，`message` 为 `null` |
| 空 | 有 | `fetched` | 返回消息，并标记该客户端已获取 |
| 非空 | 无 | `set` | 写入新消息 |
| 非空 | 有，该客户端未获取过 | `deleted` | 删除当前消息，不写入新内容 |
| 非空 | 有，该客户端已获取过 | `already_fetched` | 返回当前消息，不做修改 |

响应示例：

```json
{"action": "fetched", "message": "你好，度朔", "already_fetched": false}
```

消息的缓存时长由 `message_cache_duration` 控制，过期后自动清除。

## 错误码

| 状态码 | 含义 |
| --- | --- |
| `400` | 参数不合法（公钥无法解析、配置值非正整数等） |
| `403` | 鉴权失败（配对码不匹配、客户端未配对、签名错误、时间戳超差） |
| `404` | 路径不存在 |
| `410` | 配对窗口已关闭 |
| `422` | 请求体或载荷字段校验失败 |
| `500` | 服务器内部错误 |

## 人工测试客户端

`tests/manual_client.py` 提供交互式命令行客户端，可逐个调用上述接口进行人工验证：

```bash
uv run --extra dev python tests/manual_client.py
```

身份（客户端标识与 Ed25519 私钥）保存在 `tests/.manual_client_profile.json`，删除该文件即可重置身份重新配对。


