# tests/test_cli_required_args.py

import os, pytest

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


@pytest.mark.parametrize("cmd", ["search", "define", "impact", "init", "diff"])
def test_symbol_required(cmd):
    p = cli.build_parser()
    with pytest.raises(SystemExit) as e:
        p.parse_args([cmd])  # missing <symbol>
    assert e.value.code == 2
