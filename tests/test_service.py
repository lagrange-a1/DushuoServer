"""服务端接口自动化测试。"""

import time

from fastapi.testclient import TestClient

from client_tools import build_signed_body, generate_keypair
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


def test_signed_request_requires_pairing(client: TestClient) -> None:
    private_pem, _ = generate_keypair()

    body = build_signed_body("alice", private_pem, {})
    response = client.post("/api/status", json=body)
    assert response.status_code == 403


def test_signed_request_rejects_bad_signature(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body("alice", private_pem, {})
    body["payload"] = {"tampered": True}

    response = client.post("/api/status", json=body)
    assert response.status_code == 403


def test_signed_request_rejects_stale_timestamp(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body(
        "alice", private_pem, {}, timestamp=int(time.time()) - 3600
    )
    response = client.post("/api/status", json=body)
    assert response.status_code == 403


def test_pairing_replaces_public_key(client: TestClient, pair) -> None:
    old_pem = pair("alice")
    new_pem = pair("alice")

    old_body = build_signed_body("alice", old_pem, {})
    assert client.post("/api/status", json=old_body).status_code == 403

    new_body = build_signed_body("alice", new_pem, {})
    assert client.post("/api/status", json=new_body).status_code == 200


def test_reopen_pairing_window_requires_pairing(client: TestClient) -> None:
    private_pem, _ = generate_keypair()

    body = build_signed_body("alice", private_pem, {})
    response = client.post("/api/pairing/reopen", json=body)
    assert response.status_code == 403


def test_reopen_pairing_window(client: TestClient, pair) -> None:
    private_pem = pair("alice")
    old_code = runtime.state.pairing_key

    body = build_signed_body("alice", private_pem, {})
    response = client.post("/api/pairing/reopen", json=body)

    assert response.status_code == 200
    result = response.json()
    assert result["reopened_by"] == "alice"
    assert result["pairing_code"] == runtime.state.pairing_key
    assert result["pairing_code"] != old_code
    assert result["window_remaining_seconds"] > 0

    # 重新开放窗口不影响已配对的客户端。
    body = build_signed_body("alice", private_pem, {})
    assert client.post("/api/status", json=body).status_code == 200


def test_reopened_window_accepts_new_client(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    # 关闭当前窗口后无法再配对。
    expire_pairing_window()
    assert client.get("/api/pairing").status_code == 410

    body = build_signed_body("alice", private_pem, {})
    assert client.post("/api/pairing/reopen", json=body).status_code == 200
    assert client.get("/api/pairing").status_code == 200

    # 新客户端使用重新开放的配对码完成配对。
    assert pair("bob") is not None


def test_activity_report_resets_deadline(client: TestClient, pair) -> None:
    private_pem = pair("alice")
    runtime.state.deadline = int(time.time()) + 10

    body = build_signed_body("alice", private_pem, {"activity": "打字"})
    response = client.post("/api/activity", json=body)

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["countdown_reset"] is True
    assert (
        runtime.state.deadline
        >= int(time.time()) + config.runtime.death_countdown - 2
    )
    assert runtime.state.last_activity_at is not None


def test_activity_rejects_invalid_payload(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body("alice", private_pem, {"activity": 123})
    response = client.post("/api/activity", json=body)

    assert response.status_code == 422


def test_status(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body("alice", private_pem, {})
    response = client.post("/api/status", json=body)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "alive"
    assert result["countdown_remaining_seconds"] > 0
    assert result["pairing_window_open"] is True
    assert "runtime" in result["config"]


def test_config_read_and_update(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body("alice", private_pem, {})
    assert client.post("/api/config", json=body).status_code == 200

    body = build_signed_body("alice", private_pem, {"death_countdown": 60})
    response = client.put("/api/config", json=body)

    assert response.status_code == 200
    assert response.json()["runtime"]["death_countdown"] == 60
    assert config.runtime.death_countdown == 60

    body = build_signed_body("alice", private_pem, {})
    result = client.post("/api/status", json=body).json()
    # update_deadline 以 0.5 秒向上取整，允许 60.5 秒左右的余量。
    assert result["countdown_remaining_seconds"] < 61


def test_config_update_rejects_non_positive(client: TestClient, pair) -> None:
    private_pem = pair("alice")

    body = build_signed_body("alice", private_pem, {"death_countdown": 0})
    response = client.put("/api/config", json=body)

    assert response.status_code == 400


def test_message_flow(client: TestClient, pair) -> None:
    alice_pem = pair("alice")
    bob_pem = pair("bob")

    # 缓存为空时设置新消息。
    body = build_signed_body("alice", alice_pem, {"content": "你好，度朔"})
    response = client.post("/api/message", json=body)
    assert response.json()["action"] == "set"

    # 内容为空时获取消息。
    body = build_signed_body("alice", alice_pem, {"content": None})
    response = client.post("/api/message", json=body)
    assert response.json() == {
        "action": "fetched",
        "message": "你好，度朔",
        "already_fetched": False,
    }

    # 再次获取同一条消息。
    body = build_signed_body("alice", alice_pem, {"content": None})
    response = client.post("/api/message", json=body)
    assert response.json()["action"] == "fetched"
    assert response.json()["already_fetched"] is True

    # 已获取过当前消息的客户端不能覆盖或删除。
    body = build_signed_body("alice", alice_pem, {"content": "新消息"})
    response = client.post("/api/message", json=body)
    assert response.json()["action"] == "already_fetched"

    # 未获取过当前消息的客户端发送内容将删除当前消息。
    body = build_signed_body("bob", bob_pem, {"content": "新消息"})
    response = client.post("/api/message", json=body)
    assert response.json() == {"action": "deleted", "message": None}

    # 删除后缓存为空。
    body = build_signed_body("bob", bob_pem, {"content": None})
    response = client.post("/api/message", json=body)
    assert response.json() == {"action": "empty", "message": None}
