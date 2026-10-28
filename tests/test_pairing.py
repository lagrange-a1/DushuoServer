"""配对测试。"""

import time

from fastapi.testclient import TestClient

from dushuoserver import runtime


def test_pairing_page_available(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "度朔服务端配对" in response.text


def test_pairing_info_requires_key(client: TestClient) -> None:
    response = client.get("/api/pairing")
    assert response.status_code == 403


def test_pairing_info_available(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/pairing", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "config_code" in body
    assert "pairing_uri" in body


def test_pairing_window_closed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    runtime.state["started_at"] = time.time() - 10000

    response = client.get("/")
    assert response.status_code == 410

    response = client.get("/api/pairing", headers=auth_headers)
    assert response.status_code == 410
