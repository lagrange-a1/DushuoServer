
# 度朔 系统接口一览

所有业务接口均需要配对密钥。密钥可通过 HTTP 头 `X-Pairing-Key` 或查询参数 `key` 传递。

## 通用

- `GET /health`：健康检查。

## 配对

- `GET /`：配对页面。仅在配对窗口内可用。
- `GET /api/pairing`：获取服务端地址、配对密钥、桌面端配置码和配对 URI。

## 活动上报

- `POST /api/activity`

请求体：

```json
{
  "client_id": "客户端标识",
  "activity": "数字活动描述",
  "timestamp": 1700000000
}
```

上报成功后会重置死亡判定倒计时。

## 状态

- `GET /api/status`：返回当前状态、倒计时剩余时间、最近活动时间、配对窗口状态和配置。

## 配置

- `GET /api/config`：读取全部配置。
- `PUT /api/config`：修改可修改配置项。

可修改字段：

- `activity_retention_seconds`
- `countdown_seconds`
- `final_task`
- `pairing_window_seconds`
- `message_cache_seconds`

`port` 不可由客户端修改。

## 短报文

- `POST /api/message`

请求体：

```json
{
  "device_id": "设备标识",
  "content": "消息内容"
}
```

语义：

- `content` 为空：获取当前缓存消息；若无消息则返回空。
- `content` 不为空且缓存中无消息：设置消息内容。
- `content` 不为空且缓存中存在消息：删除缓存消息，不设置新内容。

## 启动


默认监听 `0.0.0.0:8000`。


