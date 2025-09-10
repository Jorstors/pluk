# tests/test_cli_impact_endpoint.py
import os
import requests

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("PLUK_API_URL", "http://example.local:8000")

from pluk import cli


class DummyRedis:
    def get(self, *a, **k):
        return None

    def set(self, *a, **k):
        return True

    def exists(self, *a, **k):
        return False


class FakeResp:
    def __init__(self, code=200, data=None, text=""):
        self.status_code = code
        self._data = data or {"symbol_references": []}
        self.text = text

    def json(self):
        return self._data


def test_cmd_impact_calls_expected_url(monkeypatch):
    # prevent real Redis connections
    monkeypatch.setattr(cli, "redis_client", DummyRedis())

    called = {}

    def fake_get(url, *a, **k):
        called["url"] = url
        symbol_references = [
            {
                "file": "file1.py",
                "line": 10,
                "container": "MyClass",
                "container_kind": "class",
            },
            {
                "file": "file2.py",
                "line": 20,
                "container": "my_function",
                "container_kind": "function",
            },
        ]
        return FakeResp(200, {"symbol_references": symbol_references})

    monkeypatch.setattr(requests, "get", fake_get)

    ns = cli.build_parser().parse_args(["impact", "Foo"])
    cli.cmd_impact(ns)
    assert called["url"].startswith("http://example.local:8000/")
    assert "/impact/Foo" in called["url"]
