# tests/test_cli_search_endpoint.py
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
        self._data = data or {"symbols": []}
        self.text = text

    def json(self):
        return self._data


def test_cmd_search_calls_expected_url(monkeypatch):
    # prevent real Redis connections
    monkeypatch.setattr(cli, "redis_client", DummyRedis())

    called = {}

    def fake_get(url, *a, **k):
        called["url"] = url
        symbols = [{"name": "Foo", "location": "file:line", "commit": "abc123"}]
        return FakeResp(200, {"symbols": symbols})

    monkeypatch.setattr(requests, "get", fake_get)

    ns = cli.build_parser().parse_args(["search", "Foo"])
    cli.cmd_search(ns)
    assert called["url"].startswith("http://example.local:8000/")
    assert "/search/Foo" in called["url"]
