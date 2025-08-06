# src/pluk/cli.py

import argparse
import sys

def cmd_init(args):
    return

def cmd_search(args):
    return

def cmd_start(args):
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
