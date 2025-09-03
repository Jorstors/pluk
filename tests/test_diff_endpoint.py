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


def test_cmd_define_calls_expected_url(monkeypatch):
    # prevent real Redis connections
    monkeypatch.setattr(cli, "redis_client", DummyRedis())

    called = {}

    def fake_get(url, *a, **k):
        called["url"] = url
        symbol_info = {
            "file": "some/file/path",
            "line": 10,
            "end_line": 12,
            "name": "Foo",
            "kind": "function",
            "language": "python",
            "signature": "(arg1, arg2)",
            "scope": "SomeClass",
            "scope_kind": "class",
        }

        return FakeResp(200, {"symbol": symbol_info})

    monkeypatch.setattr(requests, "get", fake_get)

    ns = cli.build_parser().parse_args(["define", "Foo"])
    cli.cmd_define(ns)
    assert called["url"].startswith("http://example.local:8000/")
    assert "/define/Foo" in called["url"]
