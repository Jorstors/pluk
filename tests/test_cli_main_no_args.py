# tests/test_cli_main_no_args.py

import os, sys, pytest

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


def test_main_no_args_prints_help_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["plukd"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 1
    captured = capsys.readouterr().out.lower()
    assert "usage:" in captured
