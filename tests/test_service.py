"""服务端接口自动化测试。"""

import json
import time

from fastapi.testclient import TestClient

from client_tools import generate_keypair, request_signed, sign_request_headers
from dushuoserver import runtime
from dushuoserver.config import config


def expire_pairing_window() -> None:
    """使当前配对窗口立刻过期。"""
    runtime.state._State__pairing_key_expire_at = -1


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pairing_page_available(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "度朔服务端配对" in response.text


def test_pairing_page_closed_after_window(client: TestClient) -> None:
    expire_pairing_window()

    assert client.get("/").status_code == 410
    assert client.get("/api/pairing").status_code == 410


def test_pairing_info_contains_code(client: TestClient) -> None:
    response = client.get("/api/pairing")
    assert response.status_code == 200
    body = response.json()
    assert body["pairing_code"] == runtime.state.pairing_key
    assert body["window_remaining_seconds"] > 0


def test_pair_rejects_wrong_code(client: TestClient) -> None:
    _, public_pem = generate_keypair()
    response = client.post(
        "/api/pair",
        json={
            "pairing_code": "wrong-code",
            "client_id": "alice",
            "public_key": public_pem.decode(),
        },
    )
    assert response.status_code == 403


def test_pair_rejects_broken_public_key(client: TestClient) -> None:
    response = client.post(
        "/api/pair",
        json={
            "pairing_code": runtime.state.pairing_key,
            "client_id": "alice",
            "public_key": "not a pem key",
        },
    )
    assert response.status_code == 400


def test_signed_request_requires_headers(client: TestClient) -> None:
    assert client.get("/api/status").status_code == 401


def test_signed_request_requires_pairing(client: TestClient) -> None:
    private_pem, _ = generate_keypair()

    response = request_signed(client, "GET", "/api/status", "alice", private_pem)
    assert response.status_code == 401


def test_signed_request_rejects_stale_timestamp(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    response = request_signed(
        client,
        "GET",
        "/api/status",
        "alice",
        private_pem,
        timestamp=int(time.time()) - 3600,
    )
    assert response.status_code == 401


def test_signed_request_rejects_unregistered_key(client: TestClient, pair) -> None:
    pair("alice")
    other_pem, _ = generate_keypair()

    response = request_signed(client, "GET", "/api/status", "alice", other_pem)
    assert response.status_code == 401


def test_signed_request_rejects_tampered_body(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    headers = sign_request_headers(
        "alice",
        private_pem,
        "POST",
        "/api/activity",
        json.dumps({"activity": "打字"}, ensure_ascii=False).encode("utf-8"),
    )
    headers["Content-Type"] = "application/json"

    response = client.post(
        "/api/activity",
        content='{"activity": "篡改"}'.encode("utf-8"),
        headers=headers,
    )
    assert response.status_code == 401


def test_signature_is_bound_to_method_and_path(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    # 针对 /api/status 生成的签名不能被挪用到 /api/config。
    headers = sign_request_headers("alice", private_pem, "GET", "/api/status")
    assert client.get("/api/config", headers=headers).status_code == 401


def test_pairing_replaces_public_key(client: TestClient, pair) -> None:
    old_pem = pair("alice")
    new_pem = pair("alice")

    assert (
        request_signed(client, "GET", "/api/status", "alice", old_pem).status_code == 401
    )
    assert (
        request_signed(client, "GET", "/api/status", "alice", new_pem).status_code == 200
    )


def test_activity_report_resets_deadline(client: TestClient, pair) -> None:
    private_pem = pair("alice")
    runtime.state.deadline = int(time.time()) + 10

    response = request_signed(
        client, "POST", "/api/activity", "alice", private_pem, {"activity": "打字"}
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["countdown_reset"] is True
    assert (
        runtime.state.deadline
        >= int(time.time()) + config.runtime.death_countdown - 2
    )
    assert runtime.state.last_activity_at is not None


def test_activity_rejects_invalid_body(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    response = request_signed(
        client, "POST", "/api/activity", "alice", private_pem, {"activity": 123}
    )
    assert response.status_code == 422


def test_status(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    response = request_signed(client, "GET", "/api/status", "alice", private_pem)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "alive"
    assert result["countdown_remaining_seconds"] > 0
    assert result["pairing_window_open"] is True
    assert "runtime" in result["config"]


def test_config_read_and_update(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    response = request_signed(client, "GET", "/api/config", "alice", private_pem)
    assert response.status_code == 200

    response = request_signed(
        client, "PUT", "/api/config", "alice", private_pem, {"death_countdown": 60}
    )

    assert response.status_code == 200
    assert response.json()["runtime"]["death_countdown"] == 60
    assert config.runtime.death_countdown == 60

    result = request_signed(client, "GET", "/api/status", "alice", private_pem).json()
    # update_deadline 以 0.5 秒向上取整，故留出一秒余量。
    assert result["countdown_remaining_seconds"] < 61


def test_config_update_rejects_non_positive(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    response = request_signed(
        client, "PUT", "/api/config", "alice", private_pem, {"death_countdown": 0}
    )
    assert response.status_code == 400


def test_message_send_fetch_and_delete(client: TestClient, pair) -> None:
    alice_pem = pair("alice")
    bob_pem = pair("bob")

    # 缓存为空时获取短报文返回 404。
    assert (
        request_signed(client, "GET", "/api/message", "alice", alice_pem).status_code
        == 404
    )

    # 发送新的短报文。
    response = request_signed(
        client, "POST", "/api/message", "alice", alice_pem, {"content": "你好，度朔"}
    )
    assert response.status_code == 201
    assert response.json()["message"] == "你好，度朔"

    # 已存在短报文时不允许直接覆盖。
    response = request_signed(
        client, "POST", "/api/message", "alice", alice_pem, {"content": "新消息"}
    )
    assert response.status_code == 409

    # alice 首次获取该短报文。
    response = request_signed(client, "GET", "/api/message", "alice", alice_pem)
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "你好，度朔"
    assert result["created_at"] > 0
    assert result["already_fetched"] is False

    # alice 再次获取时被告知已读取过。
    response = request_signed(client, "GET", "/api/message", "alice", alice_pem)
    assert response.json()["already_fetched"] is True

    # bob 首次获取同一条短报文。
    response = request_signed(client, "GET", "/api/message", "bob", bob_pem)
    assert response.json()["already_fetched"] is False

    # bob 删除当前短报文，成功时无响应体。
    response = request_signed(client, "DELETE", "/api/message", "bob", bob_pem)
    assert response.status_code == 204
    assert response.content == b""

    # 删除后缓存为空。
    assert (
        request_signed(client, "GET", "/api/message", "alice", alice_pem).status_code
        == 404
    )
    assert (
        request_signed(client, "DELETE", "/api/message", "alice", alice_pem).status_code
        == 404
    )


def test_message_rejects_empty_content(client: TestClient, pair) -> None:
    alice_pem = pair("alice")

    response = request_signed(
        client, "POST", "/api/message", "alice", alice_pem, {"content": ""}
    )
    assert response.status_code == 422


def test_reopen_pairing_window_requires_pairing(client: TestClient) -> None:
    private_pem, _ = generate_keypair()

    response = request_signed(
        client, "POST", "/api/pairing/reopen", "alice", private_pem
    )
    assert response.status_code == 401


def test_reopen_pairing_window(client: TestClient, pair) -> None:
    private_pem = pair("alice")
    old_code = runtime.state.pairing_key

    response = request_signed(client, "POST", "/api/pairing/reopen", "alice", private_pem)

    assert response.status_code == 200
    result = response.json()
    assert result["reopened_by"] == "alice"
    assert result["pairing_code"] == runtime.state.pairing_key
    assert result["pairing_code"] != old_code
    assert result["window_remaining_seconds"] > 0

    # 重新开放窗口不影响已配对客户端的签名鉴权。
    assert (
        request_signed(client, "GET", "/api/status", "alice", private_pem).status_code
        == 200
    )


def test_reopened_window_accepts_new_client(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    # 关闭当前窗口后无法再配对。
    expire_pairing_window()
    assert client.get("/api/pairing").status_code == 410

    response = request_signed(client, "POST", "/api/pairing/reopen", "alice", private_pem)
    assert response.status_code == 200
    assert client.get("/api/pairing").status_code == 200

    # 新客户端使用重新开放的配对码完成配对。
    assert pair("bob") is not None