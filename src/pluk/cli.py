# src/pluk/cli.py
"""
Command-line entry point: argument parsing plus human-readable formatting.

Every command function (`cmd_*`) calls into `query`/`indexer` for the actual
work, then either prints JSON (`--json`) or renders colorized text. Business
logic and errors (`PlukError`) live in `query.py`/`indexer.py`, not here.
"""

import argparse
import json
import os
import sys

from colorama import Fore, Style, init

from pluk import __version__
from pluk.indexer import index
from pluk.query import PlukError, SYMBOL_FIELDS
from pluk import query

# colorama strips escapes when stdout is not a tty, so piping stays clean.
init(autoreset=True, strip=True if os.environ.get("NO_COLOR") else None)

SYMBOL = Fore.CYAN + Style.BRIGHT
LOCATION = Fore.BLUE
LABEL = Style.DIM
KIND = Fore.MAGENTA
HEADING = Style.BRIGHT
GOOD = Fore.GREEN + Style.BRIGHT
WARN = Fore.YELLOW
REMOVED = Fore.RED
ADDED = Fore.GREEN


def paint(text, style):
    """Wrap `text` in a colorama style, resetting after it."""
    return f"{style}{text}{Style.RESET_ALL}"


def field(label, value, width=10):
    """A dim, aligned label followed by its value."""
    return f" {paint(f'{label + ":":<{width}}', LABEL)} {value}"


def emit(args, payload):
    """Print structured output when --json is set. Returns True if it did."""
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return True
    return False


def cmd_init(args):
    """
    Index a git repository.

    The repository is read where it sits -- nothing is copied and nothing
    leaves the machine. A remote URL may be given instead of a path, in which
    case it is mirrored under ~/.pluk/repos first.
    """
    progress = None if args.json else (lambda message: print(paint(message, LABEL)))
    result = index(args.path, args.rev, force=args.force, on_progress=progress)

    if emit(args, result):
        return

    print()
    if result["status"] == "skipped":
        print(paint("[+] Already indexed.", GOOD))
    else:
        print(paint(f"[+] {result['symbols']} symbols indexed.", GOOD))
    print(paint("Current repository:", HEADING))
    print(field("URL", paint(result["repo_url"], LOCATION), width=11))
    print(field("Commit", paint(result["commit_sha"], LOCATION), width=11))


def cmd_search(args):
    """Fuzzy search for symbols in the current indexed commit."""
    result = query.search(args.symbol)

    if emit(args, result):
        return

    symbols = result["symbols"]
    print(
        paint(f"Searching for {args.symbol}", HEADING)
        + paint(f"  @ {result['repo_url']}:{result['commit_sha'][:12]}", LABEL)
    )
    print()

    if not symbols:
        print(paint("No symbols found.", WARN))
        return

    for symbol in symbols:
        print(f"{paint(symbol['name'], SYMBOL)}  {paint(symbol['location'], LOCATION)}")
    print()
    print(paint(f"{len(symbols)} match{'es' if len(symbols) != 1 else ''}.", LABEL))


def cmd_define(args):
    """Show a symbol's definition and its location in the current repository."""
    symbol = query.define(args.symbol)

    if emit(args, symbol):
        return

    end_line = symbol["end_line"]
    span = f"{symbol['file']}:{symbol['line']}{f'-{end_line}' if end_line else ''}"
    scope = symbol["scope"] or "global"
    scope_kind = paint(f"({symbol['scope_kind'] or 'unknown'})", LABEL)

    print(f"{paint(symbol['name'], SYMBOL)}{paint(symbol['signature'] or '', KIND)}")
    print(field("Location", paint(span, LOCATION)))
    print(field("Kind", paint(symbol["kind"] or "unknown", KIND)))
    print(field("Language", symbol["language"] or "unknown"))
    print(field("Scope", f"{scope} {scope_kind}"))
    print()


def cmd_impact(args):
    """
    Show everything that depends on a symbol.

    Lists every reference to the symbol along with the function or class that
    contains it, so the blast radius of a change is visible at a glance.
    """
    references = query.impact(args.symbol)

    if emit(args, {"symbol": args.symbol, "symbol_references": references}):
        return

    print(paint(f"Impact of {args.symbol}", HEADING))
    print()

    if not references:
        print(paint("No references found.", WARN))
        return

    for ref in references:
        print(f" {format_reference(ref)}")
    print()
    count = len(references)
    print(paint(f"{count} reference{'' if count == 1 else 's'}.", LABEL))


def format_reference(ref, marker=""):
    """Render one reference dict as `<container> (<kind>) in <file>:<line>`."""
    container = paint(ref.get("container") or "<scope unknown>", SYMBOL)
    kind = paint(f"({ref.get('container_kind') or '<kind unknown>'})", LABEL)
    where = paint(
        f"{ref.get('file') or '<file unknown>'}:{ref.get('line') or '<line unknown>'}",
        LOCATION,
    )
    return f"{marker}{container} {kind} {paint('in', LABEL)} {where}"


def cmd_diff(args):
    """
    Show how a symbol changed between two commits.

    Both commits are indexed on demand, so any point in history can be compared.
    """
    progress = None if args.json else (lambda message: print(message))
    differences = query.diff(
        args.symbol, args.from_commit, args.to_commit, on_progress=progress
    )

    if emit(args, differences):
        return

    print(paint(f"Changes to {args.symbol}", HEADING))
    print(
        paint(
            f" {differences['from_commit'][:12]} -> {differences['to_commit'][:12]}",
            LABEL,
        )
    )
    print()

    definition_changed = differences["definition_changed"]
    new_references = differences["new_references"]
    removed_references = differences["removed_references"]

    if not definition_changed and not new_references and not removed_references:
        print(paint("No changes found.", WARN))
        return

    print(paint("Definition", HEADING))
    if not definition_changed:
        print(paint(" unchanged", LABEL))
    else:
        details = differences["definition_changed_details"]
        for key in SYMBOL_FIELDS:
            from_value = details["from"].get(key)
            to_value = details["to"].get(key)
            if from_value == to_value:
                print(paint(f" {key}: unchanged", LABEL))
            else:
                print(f" {paint(key, SYMBOL)}:")
                print(paint(f"   - {from_value}", REMOVED))
                print(paint(f"   + {to_value}", ADDED))

    print()
    print(paint("New references", HEADING))
    if not new_references:
        print(paint(" none", LABEL))
    for ref in new_references:
        print(f" {format_reference(ref, marker=paint('+ ', ADDED))}")

    print()
    print(paint("Removed references", HEADING))
    if not removed_references:
        print(paint(" none", LABEL))
    for ref in removed_references:
        print(f" {format_reference(ref, marker=paint('- ', REMOVED))}")
    print()


def add_json_flag(parser):
    """Add the shared `--json` flag to a subcommand parser."""
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output"
    )


def build_parser():
    """
    Build the command line argument parser for Pluk CLI.

    This function sets up the argument parser with subcommands
    for initializing repositories, searching symbols, defining symbols,
    analyzing impacts, and showing diffs.
    """

    # Create the main argument parser
    p = argparse.ArgumentParser(prog="pluk", description="Pluk CLI")
    p.add_argument("--version", action="version", version=f"pluk {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # === Define subcommands ===

    # Index a repository
    p_init = sub.add_parser("init", help="Index a git repo")
    p_init.add_argument("path", nargs="?", default=".", help="Path or URL of the repository")
    p_init.add_argument("--rev", default="HEAD", help="Commit SHA or git alias to index")
    p_init.add_argument("--force", action="store_true", help="Reindex even if already indexed")
    add_json_flag(p_init)
    p_init.set_defaults(func=cmd_init)

    # Search for a symbols
    p_search = sub.add_parser("search", help="Search for a symbol")
    p_search.add_argument("symbol", help="Symbol name")
    add_json_flag(p_search)
    p_search.set_defaults(func=cmd_search)

    # Define a symbol
    p_define = sub.add_parser("define", help="Define a symbol")
    p_define.add_argument("symbol", help="Symbol name")
    add_json_flag(p_define)
    p_define.set_defaults(func=cmd_define)

    # Analyze impact of a symbol
    p_impact = sub.add_parser("impact", help="Analyze impact of a symbol")
    p_impact.add_argument("symbol", help="Symbol name")
    add_json_flag(p_impact)
    p_impact.set_defaults(func=cmd_impact)

    # Show differences for a symbol (between commits/aliases)
    p_diff = sub.add_parser("diff", help="Show differences for a symbol")
    p_diff.add_argument("symbol", help="Symbol name")
    p_diff.add_argument("from_commit", help="Commit SHA or git alias (e.g. head) to compare from")
    p_diff.add_argument("to_commit", help="Commit SHA or git alias (e.g. main) to compare to")
    add_json_flag(p_diff)
    p_diff.set_defaults(func=cmd_diff)

    return p


def main():
    """CLI entry point: parse args, dispatch to the matching `cmd_*`, and turn a PlukError into a clean exit."""
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    try:
        args.func(args)
    except PlukError as error:
        print(paint(f"[/] {error}", Fore.RED + Style.BRIGHT), file=sys.stderr)
        hint = getattr(error, "hint", None)
        if hint:
            print(paint(f"    {hint}", LABEL), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
