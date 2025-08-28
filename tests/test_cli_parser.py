# tests/test_cli_parser.py
import os

os.environ.setdefault("PLUK_REDIS_URL", "redis://localhost:6379/0")
from pluk import cli


def test_build_parser_returns_argparse():
    import argparse

    p = cli.build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_help_lists_expected_subcommands():
    help_text = cli.build_parser().format_help().lower()
    cmds = [
        "init",
        "search",
        "define",
        "impact",
        "diff",
        "start",
        "status",
        "cleanup",
    ]
    for cmd in cmds:
        assert cmd in help_text


def test_usage_lists_expected_subcommands():
    usage_text = cli.build_parser().format_usage().lower()
    cmds = [
        "init",
        "search",
        "define",
        "impact",
        "diff",
        "start",
        "status",
        "cleanup",
    ]
    for cmd in cmds:
        assert cmd in usage_text
