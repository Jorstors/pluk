# src/pluk/cli.py

import argparse
import sys
import os
import time
from colorama import Fore, Style, init
import redis

redis_client = redis.Redis.from_url(
    os.environ.get("PLUK_REDIS_URL"), decode_responses=True
)

init(autoreset=True)


def get_repo_info():
    repo_url = redis_client.get("repo_url")
    commit_sha = redis_client.get("commit_sha")
    if not repo_url or not commit_sha:
        return None, None
    return repo_url, commit_sha


# Initialize a repository
def cmd_init(args):
    """
    Initialize a repository at the specified path.

    This command queues a full index job for a repository.

    IMPORTANT: the repository to be indexed must be public (or otherwise
    directly accessible from the worker container). Workers clone repositories
    using the repository URL; private repositories that require credentials are
    not supported by the host shim workflow. When `pluk init /path/to/repo` is
    invoked on the host, the shim extracts the repo's remote URL and commit
    SHA and forwards them into the CLI container via the environment
    variables `PLUK_REPO_URL` and `PLUK_REPO_COMMIT_SHA` before asking the
    API to enqueue the reindex job.
    """
    import requests

    print(f"Initializing repository at {args.path}")
    # Grab repo information to send to the API
    repo_url = os.environ.get("PLUK_REPO_URL")
    repo_commit_sha = os.environ.get("PLUK_REPO_COMMIT_SHA")
    # Make a request to the Pluk API to initialize the repository
    reindex_res = requests.post(
        f"{os.environ.get('PLUK_API_URL')}/reindex/",
        json={"repo_url": repo_url, "commit_sha": repo_commit_sha},
    )
    if reindex_res.status_code == 200:
        sys.stdout.write("[+] Indexing started...")
        job_id = reindex_res.json()["job_id"]
        # Check job status
        start_time = time.perf_counter()
        while True:
            elapsed_time = time.perf_counter() - start_time
            job_status_res = requests.get(
                f"{os.environ.get('PLUK_API_URL')}/status/{job_id}"
            )
            if job_status_res.status_code == 200:
                res_obj = job_status_res.json()
                status = res_obj["status"]
                if status == "SUCCESS":
                    job_result = res_obj["result"]
                    if job_result["status"] == "FINISHED":
                        break
                    elif job_result["status"] == "ERROR":
                        print(
                            f"\n[/] Error initializing repository: {job_result['error_message']}"
                        )
                        return
                elif status == "FAILURE":
                    print(f"\n[/] Failed to initialize repository: {status}")
                    return
                # Update the console output with the current indexing status
                sys.stdout.write(f"\r[-] Indexing {elapsed_time:.1f}s: {status}     ")
                sys.stdout.flush()
            time.sleep(0.1)

        sys.stdout.write(
            f"\r[+] Repository initialized successfully.                                       "
        )
        print("\nCurrent repository:")
        repo_url, commit_sha = get_repo_info()
        print(f"    URL: {repo_url}")
        print(f"    Commit SHA: {commit_sha}")
    else:
        print(f"Error initializing repository: {reindex_res.status_code}")
    return


def cmd_start(args):
    """
    Start the Pluk services.

    NOTE: Starting/stopping/status commands are handled by the host shim (`pluk`)
    and affect Docker Compose on the host. Invoking `start` inside the CLI
    container (`plukd`) is a no-op; use the host shim command `pluk start`.
    """
    return


def cmd_cleanup(args):
    """
    Stop the Pluk services.

    NOTE: This is a host-level command handled by the shim (`pluk`). Use
    `pluk cleanup` on the host to stop the Docker Compose stack. Running this
    inside the CLI container does not perform host-level cleanup.
    """
    return


def cmd_status(args):
    """
    Check the status of Pluk services.

    NOTE: Service lifecycle commands (`start`, `status`, `cleanup`) are
    implemented in the host shim. Use `pluk status` on the host to inspect the
    current Docker Compose state.
    """
    return


def cmd_search(args):
    """
    Fuzzy search for symbols in the current indexed commit. Uses the
    repository currently registered with the service (see `pluk init`).
    """
    import requests

    repo_url, commit_sha = get_repo_info()
    print(
        f"{Fore.CYAN}Searching for symbol: {args.symbol} @ {repo_url if repo_url else 'unknown'}:{commit_sha if commit_sha else 'unknown'}\n"
    )
    # Make a request to the Pluk API to search for the symbol
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/search/{args.symbol}")
    if res.status_code == 200:
        res_obj = res.json()
        # Process the response JSON and list references
        for symbol in res_obj["symbols"] or []:
            print(f"Found symbol: {symbol['name']}")
            # Location: file:line@commit
            print(f"Located at: {symbol['location']}")
            print()
        if not res_obj["symbols"]:
            print("No symbols found.")
    else:
        print(f"Error searching for symbol: {res.status_code}")
        print(
            "     Please ensure the repository indexed is public and reachable by the worker container."
        )
        print(
            "     Also ensure your latest changes are pushed to 'origin' so they are available for search."
        )


def cmd_define(args):
    """
    Define a symbol in the current repository.

    This command allows users to define a symbol,
    which can be useful for documentation or metadata purposes.

    Returns the definition of the symbol, and its location in the current repository.
    """
    import requests

    print(f"Defining symbol: {args.symbol}")
    print()
    # Make a request to the Pluk API to define the symbol
    # API returns the symbol definition and its location
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/define/{args.symbol}")
    if res.status_code == 200:
        symbol_info_res = res.json()["symbol"]
        file, line, end_line, name, kind, language, signature, scope, scope_kind = (
            symbol_info_res.get("file", "unknown"),
            symbol_info_res.get("line", -1),
            symbol_info_res.get("end_line", None),
            symbol_info_res.get("name", "unknown"),
            symbol_info_res.get("kind", None),
            symbol_info_res.get("language", None),
            symbol_info_res.get("signature", None),
            symbol_info_res.get("scope", None),
            symbol_info_res.get("scope_kind", None),
        )
        print(f"Symbol: {args.symbol}")
        print(f" Location: {file}:{line}{f'-{end_line}' if end_line else ''}")
        print(f" Kind: {kind if kind else 'unknown'}")
        print(f" Language: {language if language else 'unknown'}")
        print(f" Signature: {signature if signature else 'unknown'}")
        print(
            f" Scope: {scope if scope else 'global'} ({scope_kind if scope_kind else 'unknown'})"
        )
        print()
    elif res.status_code == 404:
        print("Symbol not found.")
    else:
        print(f"Error defining symbol: {res.status_code}")


def cmd_impact(args):
    """
    Analyze the impact of a symbol in the codebase.

    Shows everything that depends on the symbol in the current repository.
    This command allows users to understand the potential impact of
    changes to a symbol by listing all symbols, including their
    files and lines, that reference it.
    """
    import requests

    print(f"Analyzing impact of symbol: {args.symbol}")
    # Make a request to the Pluk API to analyze impact
    res = requests.get(f"{os.environ.get('PLUK_API_URL')}/impact/{args.symbol}")
    if res.status_code == 200:
        res_obj = res.json()
        # Process the response JSON and list impacted files
        # Outputs formatted: {"file": path, "line": line,
        # "container": cont_node.text.decode() if cont_node else None,
        # "container_kind": cont_node.type if cont_node else None}
        print("References found:")
        for ref in res_obj["symbol_references"] or []:
            print(
                f" - {ref.get('container', '<scope unknown>')} ({ref.get('container_kind', '<kind unknown>')}) in {ref.get('file', '<file unknown>')}:{ref.get('line', '<line unknown>')}"
            )
            print()
        if not res_obj["symbol_references"]:
            print("No symbol references found.")
    elif res.status_code == 404:
        print("Symbol not found.")
    elif res.status_code == 405:
        print("Language not supported.")
        print("Please refer to the documentation for supported languages.")
    elif res.status_code == 500:
        print("Repository not initialized.")
    else:
        print(f"Internal server error: {res.status_code}")


def cmd_diff(args):
    """
    Show the differences for a symbol in the codebase from one commit to another.

    This command allows users to see how a symbol has changed
    over time, including modifications to its definition and usage.
    """
    import requests

    print(f"Showing differences for symbol: {args.symbol}")

    # Make a request to the Pluk API to get the diff
    res = requests.get(
        f"{os.environ.get('PLUK_API_URL')}/diff/{args.symbol}/{args.from_commit}/{args.to_commit}"
    )
    if res.status_code == 200:
        res_obj = res.json()
        print("Differences found:")
        for diff in res_obj["differences"] or []:
            print(f" - {diff}")
        if not res_obj["differences"]:
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
