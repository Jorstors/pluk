# tests/test_api_health.py
import os

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
from pluk.api import app
from fastapi.testclient import TestClient


def test_health_ok_status():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
