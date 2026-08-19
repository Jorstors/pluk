# src/pluk/indexer.py
"""
Indexing runs inline, in the calling process.

A local repository is read where it sits -- Pluk never copies it. Only a repo
named by URL gets mirrored into PLUK_HOME/repos, since there is nothing local
to read.
"""

import subprocess
from pathlib import Path

from pluk.db import connect, pluk_home, set_state
from pluk.query import PlukError
from pluk.SQL_UTIL.operations import (
    insert_repo,
    insert_commit,
    insert_symbol,
    commit_is_indexed,
)
from pluk.refs_ts import (
    SKIP_DIRS,
    find_defs,
    git_list_files,
    language_for_path,
)


def repos_dir() -> Path:
    """Where mirrors of URL-indexed repos are cloned, under PLUK_HOME/repos."""
    return pluk_home() / "repos"


def git(repo, *args, quiet=False, **kwargs):
    """Run a git command in `repo` and return its trimmed stdout."""
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
        stderr=subprocess.DEVNULL if quiet else None,
        **kwargs,
    ).strip()


def is_git_repo(path) -> bool:
    """Whether `path` is (inside) a git working tree."""
    try:
        git(path, "rev-parse", "--git-dir", quiet=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        return False


def looks_like_url(target: str) -> bool:
    """Whether `target` names a remote repo rather than a local path."""
    return target.startswith(("http://", "https://", "git@", "ssh://", "git://"))


def origin_url(repo):
    """The `origin` remote URL for `repo`, or None if it has no remote."""
    try:
        return git(repo, "remote", "get-url", "origin", quiet=True)
    except subprocess.CalledProcessError:
        return None


def resolve_commit(repo, rev):
    """Resolve a git revision (SHA, branch, alias) to a full commit SHA."""
    try:
        return git(repo, "rev-parse", rev, quiet=True)
    except subprocess.CalledProcessError:
        raise PlukError(f"Could not resolve '{rev}' in {repo}")


def mirror_repo(url: str) -> Path:
    """Clone or refresh a mirror of a remote repo under PLUK_HOME/repos."""
    repos_dir().mkdir(parents=True, exist_ok=True)
    mirror = repos_dir() / url.rstrip("/").split("/")[-1]

    if mirror.exists():
        subprocess.run(
            ["git", "-C", str(mirror), "fetch", "--prune", "--tags", "--force"],
            check=True,
        )
    else:
        subprocess.run(["git", "clone", "--mirror", url, str(mirror)], check=True)
    return mirror


def resolve_target(target: str):
    """
    Turn a CLI target into (repo_path, repo_url).

    A path is indexed in place; a URL is mirrored first.
    """
    if looks_like_url(target):
        mirror = mirror_repo(target)
        return mirror, target

    path = Path(target).resolve()
    if not is_git_repo(path):
        raise PlukError(f"{path} is not a git repository.")

    # Prefer the remote URL as the identity so an index survives the directory moving.
    return path, origin_url(path) or str(path)


def indexable_files(repo, commit):
    """Tracked files at `commit` that Pluk can parse, grouped by language."""
    by_language = {}
    for path in git_list_files(repo, commit):
        parts = Path(path).parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        lang_key = language_for_path(path)
        if lang_key is None:
            continue
        by_language.setdefault(lang_key, []).append(path)
    return by_language


def index(target: str, rev: str = "HEAD", force: bool = False, on_progress=None):
    """
    Index `target` at `rev` and register it as the current repository.

    Returns a summary dict. Already-indexed commits are skipped unless `force`.
    """

    report = on_progress or (lambda message: None)

    repo_path, repo_url = resolve_target(target)
    commit_sha = resolve_commit(repo_path, rev)
    report(f"Indexing {repo_url} at {commit_sha[:12]}")

    conn = connect()
    try:
        already = conn.execute(
            commit_is_indexed, {"repo_url": repo_url, "commit_sha": commit_sha}
        ).fetchone()

        if already and not force:
            report("Commit already indexed, skipping.")
            remember_current(conn, repo_url, commit_sha, repo_path)
            conn.commit()
            return {
                "status": "skipped",
                "repo_url": repo_url,
                "commit_sha": commit_sha,
                "symbols": 0,
            }

        by_language = indexable_files(repo_path, commit_sha)
        file_count = sum(len(files) for files in by_language.values())
        report(f"Parsing {file_count} files across {len(by_language)} languages")

        conn.execute(insert_repo, (repo_url, str(repo_path)))
        conn.execute(insert_commit, (repo_url, commit_sha, None))

        total = 0
        for lang_key, files in by_language.items():
            definitions = find_defs(repo_path, commit_sha, lang_key, files)
            for definition in definitions:
                conn.execute(
                    insert_symbol,
                    {"repo_url": repo_url, "commit_sha": commit_sha, **definition},
                )
            total += len(definitions)
            report(f"  {lang_key}: {len(definitions)} symbols from {len(files)} files")

        remember_current(conn, repo_url, commit_sha, repo_path)
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "indexed",
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "symbols": total,
    }


def remember_current(conn, repo_url, commit_sha, repo_path):
    set_state(conn, "repo_url", repo_url)
    set_state(conn, "commit_sha", commit_sha)
    set_state(conn, "repo_path", str(repo_path))
