"""数字活动上报测试。"""

import time

from fastapi.testclient import TestClient


def test_report_activity_resets_countdown(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/activity",
        headers=auth_headers,
        json={"client_id": "client-1", "activity": "typing", "timestamp": 1700000000},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["countdown_reset"] is True
    assert body["deadline"] >= 1700000000

    status = client.get("/api/status", headers=auth_headers).json()
    assert status["last_activity_at"] == 1700000000


def test_report_activity_requires_key(client: TestClient) -> None:
    response = client.post(
        "/api/activity",
        json={"client_id": "client-1", "activity": "typing"},
    )
    assert response.status_code == 403
