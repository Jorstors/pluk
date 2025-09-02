# tests/test_cli_no_args.py

import os
import argparse

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


def test_lifecycle_commands_are_noops():
    ns = argparse.Namespace()
    # Should not raise
    assert cli.cmd_start(ns) is None
    assert cli.cmd_status(ns) is None
    assert cli.cmd_cleanup(ns) is None
