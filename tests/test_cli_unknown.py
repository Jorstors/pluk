# tests/test_cli_unknown.py

import pytest

from pluk import cli


def test_unknown_subcommand():
    p = cli.build_parser()
    with pytest.raises(SystemExit) as e:
        p.parse_args(["invalid"])  # invalid subcommand
    assert e.value.code == 2
