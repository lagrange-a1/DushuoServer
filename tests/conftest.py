"""测试夹具。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from client_tools import generate_keypair
from dushuoserver import runtime
from dushuoserver.config import RuntimeConfig, config


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """为每个测试提供独立的数据库文件与运行时状态。"""
    monkeypatch.setattr(config, "db_path", tmp_path / "dushuo.db")

    config.runtime = RuntimeConfig()

    runtime.state.generate_pairing_key()
    runtime.state.update_deadline()
    runtime.state.triggered = False
    runtime.state.last_activity_at = None

    yield


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端。"""
    from dushuoserver.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def pair(client: TestClient):
    """返回配对辅助函数：传入客户端标识，返回其私钥 PEM。"""

    def _pair(client_id: str) -> bytes:
        private_pem, public_pem = generate_keypair()
        response = client.post(
            "/api/pair",
            json={
                "pairing_code": runtime.state.pairing_key,
                "client_id": client_id,
                "public_key": public_pem.decode(),
            },
        )
        assert response.status_code in (200, 201), response.text
        return private_pem

    return _pair
