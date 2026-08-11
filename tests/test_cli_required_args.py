# tests/test_cli_required_args.py

import pytest

from pluk import cli


@pytest.mark.parametrize("cmd", ["search", "define", "impact"])
def test_symbol_required(cmd):
    p = cli.build_parser()
    with pytest.raises(SystemExit) as e:
        p.parse_args([cmd])  # missing <symbol>
    assert e.value.code == 2


@pytest.mark.parametrize("args", [["diff"], ["diff", "X"], ["diff", "X", "A"]])
def test_diff_requires_symbol_and_both_commits(args):
    p = cli.build_parser()
    with pytest.raises(SystemExit) as e:
        p.parse_args(args)
    assert e.value.code == 2
