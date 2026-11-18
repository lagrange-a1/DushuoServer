
# 度朔服务端 API 参考

度朔服务端提供纯后端 HTTP API，用于客户端配对、数字活动上报、生死状态查询、运行时配置管理以及客户端间短报文通信。

## 通用约定

- 基础地址：`http://<服务端地址>:<端口>`，默认端口 `18470`
- 请求与响应均为 JSON（`Content-Type: application/json`），编码 UTF-8；`GET /` 除外，返回 HTML
- 所有时间戳均为 Unix 时间戳（秒）
- 除 `GET /health`、`GET /`、`GET /api/pairing`、`POST /api/pair` 外，其余接口均须以签名请求头鉴权

## 鉴权

### 总体模型

鉴权分两步：

1. **配对**：在服务端启动或重新开放的窗口时间内，客户端提交配对码与自己的公钥完成配对；
2. **签名**：此后客户端的每个业务请求均由其私钥签名，签名置于请求头中，服务端使用配对时登记的公钥校验。

配对码只在配对窗口内有效；业务请求中不含任何密钥明文，签名与请求方法、路径和请求体绑定。

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

签名凭证放在三个请求头中，因此 `GET`、`DELETE` 一类不带请求体的接口同样能够鉴权：

| 请求头 | 说明 |
| --- | --- |
| `X-Client-Id` | 配对时使用的客户端标识 |
| `X-Timestamp` | 请求发出时的 Unix 时间戳（秒） |
| `X-Signature` | 签名，标准 Base64 编码 |

时间戳与服务端的偏差超过运行时配置 `signature_time_tolerance`（默认 300 秒）时，请求被拒绝。

签名算法由公钥类型决定：

| 公钥类型 | 算法 |
| --- | --- |
| Ed25519 | 纯 Ed25519 签名 |
| RSA | RSASSA-PSS，摘要 SHA-256，MGF1-SHA256，盐长等于摘要长度 |
| ECDSA | ECDSA(SHA-256)，DER 编码签名 |

签名的计算步骤：

1. 构造规范化字节串（各行以换行符连接，客户端与服务端约定一致）：

```python
data = "\n".join(
    [
        method.upper(),                    # 请求方法，如 GET、POST、PUT、DELETE
        path,                              # 请求路径，如 /api/message
        client_id,                         # 与 X-Client-Id 一致
        str(timestamp),                    # 与 X-Timestamp 一致
        hashlib.sha256(body).hexdigest(),  # 请求体原始字节的 SHA-256 十六进制摘要
    ]
).encode("utf-8")                          # 无请求体时 body 为空字节串 b""
```

2. 使用私钥对 `data` 签名；
3. 将签名以标准 Base64 编码，填入 `X-Signature` 请求头。

签名覆盖了请求方法与路径，同一份签名无法被挪用到其他接口；请求体以摘要形式参与签名，任何改动都会使校验失败。查询参数不在签名范围内，业务接口也均不使用查询参数。

完整示例（Python，`cryptography` + `httpx`）：

```python
import base64
import hashlib
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


def signed_headers(method: str, path: str, body: bytes) -> dict:
    """按上文约定生成签名请求头。"""
    timestamp = str(int(time.time()))
    data = "\n".join(
        [method.upper(), path, CLIENT_ID, timestamp, hashlib.sha256(body).hexdigest()]
    ).encode("utf-8")

    return {
        "X-Client-Id": CLIENT_ID,
        "X-Timestamp": timestamp,
        "X-Signature": base64.b64encode(private_key.sign(data)).decode(),
    }


with httpx.Client(base_url=SERVER, timeout=10) as http:
    # 配对：向服务端上传公钥
    pairing_code = http.get("/api/pairing").json()["pairing_code"]
    http.post("/api/pair", json={
        "pairing_code": pairing_code,
        "client_id": CLIENT_ID,
        "public_key": public_pem,
    })

    # 不带请求体的接口
    body = b""
    headers = signed_headers("GET", "/api/status", body)
    print(http.get("/api/status", headers=headers).json())

    # 带 JSON 请求体的接口：先序列化，再对实际发送的字节签名
    payload = {"content": "你好，度朔"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = signed_headers("POST", "/api/message", body)
    headers["Content-Type"] = "application/json"
    print(http.post("/api/message", content=body, headers=headers).status_code)
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
| `GET` | `/api/status` | 签名 | 查询服务状态 |
| `GET` | `/api/config` | 签名 | 读取配置 |
| `PUT` | `/api/config` | 签名 | 修改运行时配置 |
| `GET` | `/api/message` | 签名 | 获取当前短报文 |
| `POST` | `/api/message` | 签名 | 发送新的短报文 |
| `DELETE` | `/api/message` | 签名 | 删除当前短报文 |

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

须签名，无请求体。仅已配对的客户端可以调用，用于重新开放配对窗口：服务端生成新的配对码，并按 `pairing_window_time` 重新计时。窗口是否已经过期均可调用，已过期的窗口会被重新打开。

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

新配对码供后续客户端配对使用；已配对客户端的签名鉴权不受影响。错误：`401` 客户端未配对或签名无效。

### POST /api/activity

请求体：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `activity` | string | 数字活动描述，可省略 |
| `timestamp` | number | 客户端上报时间戳，可省略（缺省为服务端时间） |

响应：

```json
{"accepted": true, "countdown_reset": true, "deadline": 1790000000}
```

服务端存活（未触发最终任务）时，收到活动即重置死亡判定倒计时；已触发后活动仍会被记录，但不再重置，此时 `countdown_reset` 为 `false`。

### GET /api/status

无请求体。响应：

```json
{
  "status": "alive",
  "countdown_remaining_seconds": 86399,
  "last_activity_at": null,
  "pairing_window_open": false,
  "pairing_window_remaining_seconds": 0,
  "config": { "……": "完整配置，同 GET /api/config" }
}
```

`status` 为 `alive` 或 `dead`。

### GET /api/config

无请求体，返回当前完整配置：

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

请求体为需要修改的运行时配置项，全部可选，只提交要修改的字段：

```json
{"death_countdown": 3600, "execution_task": "echo 已死亡"}
```

- 可修改字段：`activity_cache_duration`、`death_countdown`、`execution_task`、
  `message_cache_duration`、`pairing_window_time`、`signature_time_tolerance`
- 时长类字段必须为正整数，否则返回 `400`
- 修改 `death_countdown` 且尚未触发最终任务时，倒计时立即按新值重置
- 成功后返回更新后的完整配置（同 `GET /api/config`）

### GET /api/message

无请求体。返回服务端缓存中的当前短报文，并记录本客户端已读取：

```json
{
  "message": "你好，度朔",
  "created_at": 1790000000.0,
  "already_fetched": false
}
```

`already_fetched` 表示本客户端在本次请求之前是否已读取过该短报文。错误：`404` 当前没有短报文。

### POST /api/message

请求体：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `content` | string | 消息内容，不可为空 |

发送一条新的短报文，成功返回 `201`：

```json
{
  "message": "你好，度朔",
  "created_at": 1790000000.0
}
```

错误：`409` 当前已存在短报文，须先删除后再发送；`422` `content` 缺失或为空。

### DELETE /api/message

无请求体。删除当前短报文，成功返回 `204`，无响应内容。

错误：`404` 当前没有短报文。

短报文的缓存时长由 `message_cache_duration` 控制，超时后自动清除。

## 错误码

| 状态码 | 含义 |
| --- | --- |
| `400` | 参数不合法（公钥无法解析、配置值非正整数等） |
| `401` | 签名鉴权失败（缺少签名请求头、客户端未配对、签名验证失败、时间戳超差） |
| `403` | 配对码不匹配 |
| `404` | 资源不存在（路径不存在、当前没有短报文） |
| `409` | 状态冲突（当前已有短报文时再次发送） |
| `410` | 配对窗口已关闭 |
| `422` | 请求体字段校验失败 |
| `500` | 服务器内部错误 |

## 人工测试客户端

`tests/manual_client.py` 提供交互式命令行客户端，可逐个调用上述接口进行人工验证：

```bash
uv run --extra dev python tests/manual_client.py
```

身份（客户端标识与 Ed25519 私钥）保存在 `tests/.manual_client_profile.json`，删除该文件即可重置身份重新配对。


