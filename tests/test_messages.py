"""短报文测试。"""

from fastapi.testclient import TestClient


def test_message_set_fetch_and_delete(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/message",
        headers=auth_headers,
        json={"device_id": "device-a", "content": "hello"},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "set"

    response = client.post(
        "/api/message",
        headers=auth_headers,
        json={"device_id": "device-b", "content": None},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "hello"

    response = client.post(
        "/api/message",
        headers=auth_headers,
        json={"device_id": "device-c", "content": "second"},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "deleted"


def test_message_empty_when_no_message(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/message",
        headers=auth_headers,
        json={"device_id": "device-a", "content": None},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "empty"
