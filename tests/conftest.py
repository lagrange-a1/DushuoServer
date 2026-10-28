"""测试夹具。"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dushuoserver import config, runtime


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """为每个测试提供独立的数据库文件和运行时状态。"""
    db_path = tmp_path / "dushuo.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    runtime.state["pairing_key"] = "test-pairing-key"
    runtime.state["started_at"] = time.time()
    runtime.state["deadline"] = time.time() + 86400
    runtime.state["triggered"] = False
    runtime.state["last_activity_at"] = None

    yield

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client():
    """创建测试客户端。"""
    from dushuoserver.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """返回配对密钥请求头。"""
    return {"X-Pairing-Key": "test-pairing-key"}
