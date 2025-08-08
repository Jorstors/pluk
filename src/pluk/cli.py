# src/pluk/cli.py

import argparse
import sys
import subprocess
import time

# Initialize a repository
def cmd_init(args):
    """
    Initialize a repository at the specified path.

    This command sets up the necessary structure for Pluk to operate,
    and is necessary to run before using repository commands.

    Immediately parses the repository, indexing its contents
    into the Pluk database.
    """
    print(f"Initializing repository at {args.path}")
    return

def cmd_search(args):
    """
    Search for a symbol in the current repository.

    This command allows users to find symbols by name.
    """
    print(f"Searching for symbol: {args.symbol}")
    return

def cmd_define(args):
    """
    Define a symbol in the current repository.

    This command allows users to define a symbol,
    which can be useful for documentation or metadata purposes.
    """
    print(f"Defining symbol: {args.symbol}")
    return

def cmd_impact(args):
    """
    Analyze the impact of a symbol in the codebase.

    This command allows users to see what parts of the code
    base would be affected by changes to a symbol.
    It can be useful for understanding dependencies and potential side effects.
    """
    print(f"Analyzing impact of symbol: {args.symbol}")
    return

def cmd_diff(args):
    """
    Show the differences for a symbol in the codebase from one commit to another.

    This command allows users to see how a symbol has changed
    over time, including modifications to its definition and usage.
    """
    print(f"Showing differences for symbol: {args.symbol}")
    return


def cmd_start(args):
    """
    Start the API server and worker processes.

    This command launches the Pluk server and worker to handle requests.
    It assumes the Docker Compose stack is already set up.
    """
    print(f"Starting pluk server and worker...")

    # For now, we just start a long running process
    while True:
        print("Pluk server is running...")
        time.sleep(5)

    return


def cmd_cleanup(args):
    """
    Stop the Docker Compose stack. Does not remove containers.

    This command is used to stop the Pluk services without removing them.
    It can be useful for maintenance or updates.
    """
    print(f"Stopping Docker Compose stack...")
    subprocess.run(["docker", "compose", "stop"], check=True, capture_output=True)
    print("Docker Compose stack stopped.")
    return



def build_parser():
    """
    Build the command line argument parser for Pluk CLI.

    This function sets up the argument parser with subcommands
    for initializing repositories, searching symbols, defining symbols,
    analyzing impacts, showing diffs, starting the server, and cleaning up.
    """

    # Create the main argument parser
    p = argparse.ArgumentParser(prog="plukd")
    sub = p.add_subparsers(dest="command", required=True)

    # Define subcommands

    # Initialize a repository
    p_init = sub.add_parser("init", help="Index a git repo")
    p_init.add_argument("path", help="Path to the repository")
    p_init.set_defaults(func=cmd_init)

    # Search for a symbols
    p_search = sub.add_parser("search", help="Search for a symbol")
    p_search.add_argument("symbol", help="Symbol name")
    p_search.set_defaults(func=cmd_search)

    # Define a symbol
    p_define = sub.add_parser("define", help="Define a symbol")
    p_define.add_argument("symbol", help="Symbol name")
    p_define.set_defaults(func=cmd_define)

    # Analyze impact of a symbol
    p_impact = sub.add_parser("impact", help="Analyze impact of a symbol")
    p_impact.add_argument("symbol", help="Symbol name")
    p_impact.set_defaults(func=cmd_impact)

    # Show differences for a symbol (between commits)
    p_diff = sub.add_parser("diff", help="Show differences for a symbol")
    p_diff.add_argument("symbol", help="Symbol name")
    p_diff.set_defaults(func=cmd_diff)

    # Start the API server and worker
    p_start = sub.add_parser("start", help="Start API server + worker")
    p_start.set_defaults(func=cmd_start)

    # Cleanup command to stop the Docker Compose stack
    p_cleanup = sub.add_parser("cleanup", help="Stop Pluk services")
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
