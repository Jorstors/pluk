# tests/test_cli_parser.py
import pytest

from pluk import cli

SUBCOMMANDS = ["init", "search", "define", "impact", "diff"]


def test_build_parser_returns_argparse():
    import argparse

    p = cli.build_parser()
    assert isinstance(p, argparse.ArgumentParser)


def test_help_lists_expected_subcommands():
    help_text = cli.build_parser().format_help().lower()
    for cmd in SUBCOMMANDS:
        assert cmd in help_text


def test_usage_lists_expected_subcommands():
    usage_text = cli.build_parser().format_usage().lower()
    for cmd in SUBCOMMANDS:
        assert cmd in usage_text


def test_service_lifecycle_commands_are_gone():
    """Pluk runs in-process now -- there are no services to start or stop."""
    p = cli.build_parser()
    for cmd in ("start", "status", "cleanup"):
        with pytest.raises(SystemExit):
            p.parse_args([cmd])


def test_init_defaults_to_current_directory():
    ns = cli.build_parser().parse_args(["init"])
    assert ns.path == "."
    assert ns.rev == "HEAD"
