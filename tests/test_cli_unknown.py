# tests/test_cli_unknown.py

import os, pytest

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


def test_unknown_subcommand(monkeypatch):
    p = cli.build_parser()
    with pytest.raises(SystemExit) as e:
        p.parse_args(["invalid"])  # invalid subcommand
    assert e.value.code == 2
