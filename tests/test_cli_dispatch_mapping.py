# tests/test_cli_dispatch_mapping.py
from pluk import cli


def test_subcommand_sets_func_for_each():
    p = cli.build_parser()
    cases = {
        "init": cli.cmd_init,
        "search": cli.cmd_search,
        "define": cli.cmd_define,
        "impact": cli.cmd_impact,
        "diff": cli.cmd_diff,
    }
    for sub, fn in cases.items():
        if sub == "diff":
            args = [sub, "X", "A", "B"]
        else:
            args = [sub, "X"]
        ns = p.parse_args(args)
        assert getattr(ns, "func", None) is fn


def test_every_subcommand_accepts_json():
    p = cli.build_parser()
    for args in (
        ["init", "."],
        ["search", "X"],
        ["define", "X"],
        ["impact", "X"],
        ["diff", "X", "A", "B"],
    ):
        ns = p.parse_args(args + ["--json"])
        assert ns.json is True
