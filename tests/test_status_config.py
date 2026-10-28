"""状态与配置测试。"""

from fastapi.testclient import TestClient


def test_status_returns_config(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/status", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"alive", "dead"}
    assert "countdown_remaining_seconds" in body
    assert body["config"]["port"] == 8000


def test_config_read_and_update(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/config", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["countdown_seconds"] == 86400

    response = client.put(
        "/api/config",
        headers=auth_headers,
        json={"countdown_seconds": 120, "final_task": "echo ok"},
    )
    assert response.status_code == 200
    assert response.json()["countdown_seconds"] == 120
    assert response.json()["final_task"] == "echo ok"


def test_config_rejects_port_update(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.put("/api/config", headers=auth_headers, json={"port": 9000})
    assert response.status_code == 400


def test_config_rejects_invalid_seconds(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.put(
        "/api/config",
        headers=auth_headers,
        json={"countdown_seconds": 0},
    )
    assert response.status_code == 400