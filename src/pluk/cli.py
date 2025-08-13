# src/pluk/cli.py

import argparse
import sys
import subprocess
import os
import requests
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
    # Grab repo information to send to the API
    repo_url = "https://github.com/user/repo.git"
    commit = "HEAD"
    # Make a request to the Pluk API to initialize the repository
    reindex_res = requests.post(f"{os.environ.get('PLUK_API_URL')}/reindex/", json={
        "repo_url": repo_url,
        "commit": commit
    })
    if reindex_res.status_code == 200:
        job_id = reindex_res.json()['job_id']
        # Check job status
        while True:
            job_status_res = requests.get(f"{os.environ.get('PLUK_API_URL')}/status/{job_id}")
            if job_status_res.status_code == 200:
                status = job_status_res.json()['status']
                print(f"Job status: {status}")
                if status == "finished":
                    break
            time.sleep(0.1)
        print("Repository initialized successfully.")
    else:
        print(f"Error initializing repository: {reindex_res.status_code}")
    return

def cmd_start(args):
    """
    Start the Pluk services.

    This command starts all the required Docker containers for Pluk,
    including the database, worker, and API services.
    It will create the necessary Docker Compose configuration if it doesn't exist.
    """
    return

def cmd_cleanup(args):
    """
    Stop the Pluk services.

    This command stops all running Pluk Docker containers,
    but does not remove data volumes.
    """
    return

def cmd_status(args):
    """
    Check the status of Pluk services.

    This command checks if all required Pluk services are running
    and reports their current status.
    """
    return

def cmd_search(args):
    """
    Search for a symbol in the current repository.

    This command allows users to find symbols by name, and list its references
    """
    print(f"Searching for symbol: {args.symbol}")
    # Make a request to the Pluk API to search for the symbol
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/search/{args.symbol}")
    if res.status_code == 200:
        res_obj = res.json()
        # Process the response JSON and list references
        for symbol in res_obj['symbols'] or []:
            print(f"Found symbol: {symbol['name']}")
            # Location: file:line@commit
            print(f"Located at: {symbol['location']}@{symbol['commit']}")
            print("References:")
            for ref in symbol['references'] or []:
                print(f" - {ref}")
            if not symbol['references']:
                print("No references found.")
        if not res_obj['symbols']:
            print("No symbols found.")
    else:
        print(f"Error searching for symbol: {res.status_code}")

def cmd_define(args):
    """
    Define a symbol in the current repository.

    This command allows users to define a symbol,
    which can be useful for documentation or metadata purposes.

    Returns the definition of the symbol, and its location in the current repository.
    """
    print(f"Defining symbol: {args.symbol}")
    # Make a request to the Pluk API to define the symbol
    # API returns the symbol definition and its location
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/define/{args.symbol}")
    if res.status_code == 200:
        res_obj = res.json()
        print(f"Symbol definition: {res_obj['definition']}")
        # Location: file:line@commit
        print(f"Located at: {res_obj['location']}@{res_obj['commit']}")
    else:
        print(f"Error defining symbol: {res.status_code}")

def cmd_impact(args):
    """
    Analyze the impact of a symbol in the codebase.

    Shows everything that depends on the symbol, transitively.
    Starts with direct callers/users, then expands to callers of those callers,
    importers of importers, subclass chains, etc.

    Scope: transitive closure over the dependency graph (calls/imports/inheritance).
    """
    print(f"Analyzing impact of symbol: {args.symbol}")
    # Make a request to the Pluk API to analyze impact
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/impact/{args.symbol}")
    if res.status_code == 200:
        res_obj = res.json()
        # Process the response JSON and list impacted files
        print("Impacted files:")
        for file in res_obj['impacted_files'] or []:
            print(f" - {file}")
        if not res_obj['impacted_files']:
            print("No impacted files found.")
    else:
        print(f"Error analyzing impact: {res.status_code}")

def cmd_diff(args):
    """
    Show the differences for a symbol in the codebase from one commit to another.

    This command allows users to see how a symbol has changed
    over time, including modifications to its definition and usage.
    """
    print(f"Showing differences for symbol: {args.symbol}")

    # Make a request to the Pluk API to get the diff
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/diff/", json={
        "symbol": args.symbol,
        "from_commit": args.from_commit,
        "to_commit": args.to_commit
    })
    if res.status_code == 200:
        res_obj = res.json()
        print("Differences found:")
        for diff in res_obj['differences'] or []:
            print(f" - {diff}")
        if not res_obj['differences']:
            print("No differences found.")
    else:
        print(f"Error showing differences: {res.status_code}")

def build_parser():
    """
    Build the command line argument parser for Pluk CLI.

    This function sets up the argument parser with subcommands
    for initializing repositories, searching symbols, defining symbols,
    analyzing impacts, and showing diffs.
    """

    # Create the main argument parser
    p = argparse.ArgumentParser(prog="plukd")
    sub = p.add_subparsers(dest="command", required=True)

    # === Define subcommands ===

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
    p_diff.add_argument("from_commit", help="Commit to compare from")
    p_diff.add_argument("to_commit", help="Commit to compare to")
    p_diff.set_defaults(func=cmd_diff)

    # Start Pluk services
    p_start = sub.add_parser("start", help="Start Pluk services")
    p_start.set_defaults(func=cmd_start)

    # Stop Pluk services
    p_cleanup = sub.add_parser("cleanup", help="Stop Pluk services")
    p_cleanup.set_defaults(func=cmd_cleanup)

    # Check Pluk services status
    p_status = sub.add_parser("status", help="Check Pluk services status")
    p_status.set_defaults(func=cmd_status)

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
