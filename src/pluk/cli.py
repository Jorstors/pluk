# src/pluk/cli.py

import argparse
import sys
import subprocess

def cmd_init(args):
    print(f"Initializing repository at {args.path}")
    return

def cmd_search(args):
    print(f"Searching for symbol: {args.symbol}")
    return

def cmd_start(args):
    print(f"Starting API server + worker")
    return

def cmd_cleanup(args):
    print(f"Cleaning up compose stack -- removing active containers")
    subprocess.run(["docker", "compose", "down"], check=True)
    return

def build_parser():
    p = argparse.ArgumentParser(prog="plukd")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Index a git repo")
    p_init.add_argument("path", help="Path to the repository")
    p_init.set_defaults(func=cmd_init)

    p_search = sub.add_parser("search", help="Search for a symbol")
    p_search.add_argument("symbol", help="Symbol name")
    p_search.set_defaults(func=cmd_search)

    p_start = sub.add_parser("start", help="Start API server + worker")
    p_start.set_defaults(func=cmd_start)

    p_cleanup = sub.add_parser("cleanup", help="Cleanup compose stack -- remove active containers")
    p_cleanup.set_defaults(func=cmd_cleanup)

    return p

def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
