# tests/test_cli_dispatch_mapping.py
import os
import pytest

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


def test_subcommand_sets_func_for_each():
    p = cli.build_parser()
    cases = {
        "start": cli.cmd_start,
        "status": cli.cmd_status,
        "cleanup": cli.cmd_cleanup,
        "init": cli.cmd_init,
        "search": cli.cmd_search,
        "define": cli.cmd_define,
        "impact": cli.cmd_impact,
        "diff": cli.cmd_diff,
    }
    args = []
    for sub, fn in cases.items():
        if sub == "diff":
            args = [sub, "X", "A", "B"]
        elif sub in ["init", "search", "define", "impact"]:
            args = [sub, "X"]
        else:
            args = [sub]
        ns = p.parse_args(args)
        assert getattr(ns, "func", None) is fn
