# src/pluk/query.py
"""
Read queries against the local index.

These return plain Python data and raise PlukError on failure; formatting and
exit codes are the CLI's job.
"""

from pluk.db import connect, get_repo_info
from pluk.SQL_UTIL.operations import (
    find_symbols_fuzzy_match,
    find_exact_symbol,
)
from pluk.refs_ts import LANGUAGES, git_grep_files, find_refs

SYMBOL_FIELDS = [
    "file",
    "line",
    "end_line",
    "name",
    "kind",
    "language",
    "signature",
    "scope",
    "scope_kind",
]


class PlukError(Exception):
    """Anything the user can act on. The CLI prints it and exits non-zero."""

    def __init__(self, message, hint=None):
        super().__init__(message)
        self.hint = hint


def current_repo(conn):
    repo_url, commit_sha, repo_path = get_repo_info(conn)
    if not repo_url or not commit_sha:
        raise PlukError(
            "No repository indexed.",
            hint="Run `pluk init .` inside a git repository first.",
        )
    return repo_url, commit_sha, repo_path


def define(symbol: str, commit_sha: str = None):
    conn = connect()
    try:
        repo_url, current_sha, _ = current_repo(conn)
        commit_sha = commit_sha or current_sha
        row = conn.execute(
            find_exact_symbol,
            {"repo_url": repo_url, "commit_sha": commit_sha, "name": symbol},
        ).fetchone()
        if row is None:
            raise PlukError(f"Symbol '{symbol}' not found.")
        return dict(row)
    finally:
        conn.close()


def search(symbol: str):
    conn = connect()
    try:
        repo_url, commit_sha, _ = current_repo(conn)
        rows = conn.execute(
            find_symbols_fuzzy_match,
            {"repo_url": repo_url, "commit_sha": commit_sha, "symbol": symbol},
        ).fetchall()
        return {
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "symbols": [
                {
                    "name": row["name"],
                    "location": f"{row['file']}:{row['line']}",
                    "commit": commit_sha,
                }
                for row in rows
            ],
        }
    finally:
        conn.close()


def impact(symbol: str, commit_sha: str = None):
    conn = connect()
    try:
        repo_url, current_sha, repo_path = current_repo(conn)
        commit_sha = commit_sha or current_sha

        row = conn.execute(
            find_exact_symbol,
            {"repo_url": repo_url, "commit_sha": commit_sha, "name": symbol},
        ).fetchone()
        if row is None:
            raise PlukError(f"Symbol '{symbol}' not found.")

        lang_key = LANGUAGES.get(row["language"])
        if not lang_key:
            raise PlukError(
                f"Language '{row['language']}' is not supported.",
                hint=f"Supported languages: {', '.join(LANGUAGES)}.",
            )
    finally:
        conn.close()

    files = git_grep_files(repo_path, commit_sha, symbol)
    if not files:
        return []
    return find_refs(repo_path, commit_sha, symbol, lang_key, files)


def diff(symbol: str, from_commit: str, to_commit: str, on_progress=None):
    """
    Compare a symbol's definition and references between two commits.

    Both commits are indexed on demand -- `pluk diff` against history that was
    never indexed should just work.
    """
    from pluk.indexer import index, remember_current

    conn = connect()
    try:
        repo_url, original_sha, repo_path = current_repo(conn)
    finally:
        conn.close()

    from_sha = index(str(repo_path), from_commit, on_progress=on_progress)["commit_sha"]
    to_sha = index(str(repo_path), to_commit, on_progress=on_progress)["commit_sha"]

    # Indexing points `current` at whatever it just indexed. A diff is a
    # read -- it should not move the commit the user is working against.
    conn = connect()
    try:
        remember_current(conn, repo_url, original_sha, repo_path)
        conn.commit()
    finally:
        conn.close()

    differences = {
        "from_commit": from_sha,
        "to_commit": to_sha,
        "definition_changed": False,
        "definition_changed_details": {},
        "new_references": [],
        "removed_references": [],
    }

    definition_from = define(symbol, from_sha)
    definition_to = define(symbol, to_sha)

    if any(definition_from[f] != definition_to[f] for f in SYMBOL_FIELDS):
        differences["definition_changed"] = True
        differences["definition_changed_details"] = {
            "from": definition_from,
            "to": definition_to,
        }

    refs_from = impact(symbol, from_sha)
    refs_to = impact(symbol, to_sha)

    from_set = {(ref["container"], ref["file"]) for ref in refs_from}
    to_set = {(ref["container"], ref["file"]) for ref in refs_to}

    differences["new_references"] = [
        ref for ref in refs_to if (ref["container"], ref["file"]) in to_set - from_set
    ]
    differences["removed_references"] = [
        ref for ref in refs_from if (ref["container"], ref["file"]) in from_set - to_set
    ]

    return differences
