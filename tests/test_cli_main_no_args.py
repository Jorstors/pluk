# tests/test_cli_main_no_args.py

import sys

import pytest

from pluk import cli


def test_main_no_args_prints_help_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["pluk"])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 1
    captured = capsys.readouterr().out.lower()
    assert "usage:" in captured
