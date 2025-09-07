# src/pluk/api.py

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pluk.worker import celery, reindex_repo
from pydantic import BaseModel
import redis
from pluk.db import POOL
from pluk.SQL_UTIL.operations import (
    find_symbols_fuzzy_match,
    find_exact_symbol,
    find_scope_dependencies,
)
from pluk.refs_ts import git_grep_files, find_refs, CTAGS_TO_TREE_SITTER_MAP

app = FastAPI()

redis_client = redis.Redis.from_url(
    os.environ.get("PLUK_REDIS_URL"), decode_responses=True
)


def get_repo_info():
    repo_url = redis_client.get("repo_url")
    commit_sha = redis_client.get("commit_sha")
    if not repo_url or not commit_sha:
        return None, None
    return repo_url, commit_sha


no_init_response = JSONResponse(
    status_code=500,
    content={
        "status": "error",
        "message": "No repository initialized. Please reindex.",
    },
)


class ReindexRequest(BaseModel):
    repo_url: str
    commit_sha: str = "HEAD"


class DiffRequest(BaseModel):
    from_commit: str
    to_commit: str
    symbol: str


@app.get("/health")
def health():
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.post("/reindex")
def reindex(request: ReindexRequest):
    job = reindex_repo.delay(request.repo_url, request.commit_sha)
    if job:
        redis_client.set("repo_url", request.repo_url)
        redis_client.set("commit_sha", request.commit_sha)
        return JSONResponse(
            status_code=200, content={"status": "queued", "job_id": job.id}
        )
    return JSONResponse(
        status_code=500, content={"status": "error", "message": "Failed to enqueue job"}
    )


@app.get("/status/{job_id}")
def status(job_id: str):
    res = celery.AsyncResult(job_id)
    if res.ready():
        job_result = res.result
        return JSONResponse(
            status_code=200, content={"status": res.status, "result": job_result}
        )
    return JSONResponse(status_code=200, content={"status": res.status})


@app.get("/define/{symbol}")
def define(symbol: str) -> JSONResponse:
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response

    return define_logic(symbol, repo_url, commit_sha)


@app.get("/search/{symbol}")
def search(symbol: str) -> JSONResponse:
    """
    Fuzzy search for symbols in the current commit.
    Returns results matching the symbol name across all symbols in the current commit.
    """
    return search_logic(symbol)


@app.get("/impact/{symbol}")
def impact(symbol: str) -> JSONResponse:
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response

    return impact_logic(symbol, repo_url, commit_sha)


@app.get("/diff/{symbol}/{from_commit}/{to_commit}")
def diff(symbol: str, from_commit: str, to_commit: str):
    return diff_logic(symbol, from_commit, to_commit)


def define_logic(symbol: str, repo_url: str, commit_sha: str):
    symbol_info = {}
    with POOL.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                find_exact_symbol,
                params={
                    "repo_url": repo_url,
                    "commit_sha": commit_sha,
                    "name": symbol,
                },
            )
            found_symbol = cur.fetchone()
            if not found_symbol:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "Symbol not found"},
                )
            symbol_info = {
                "file": found_symbol["file"],
                "line": found_symbol["line"],
                "end_line": found_symbol.get("end_line"),
                "name": found_symbol["name"],
                "kind": found_symbol.get("kind"),
                "language": found_symbol.get("language"),
                "signature": found_symbol.get("signature"),
                "scope": found_symbol.get("scope"),
                "scope_kind": found_symbol.get("scope_kind"),
            }
            return JSONResponse(status_code=200, content={"symbol": symbol_info})


def search_logic(symbol: str):
    repo_url, commit_sha = get_repo_info()
    symbols = []
    with POOL.connection() as conn:
        with conn.cursor() as cur:
            # Perform fuzzy matching for symbol names in the current commit only
            cur.execute(
                find_symbols_fuzzy_match,
                params={
                    "repo_url": repo_url,
                    "commit_sha": commit_sha,
                    "symbol": symbol,
                },
            )
            res = cur.fetchall()
            print(f"Search results for {symbol}: {res}")
            for item in res:
                symbol_info = {
                    "name": item["name"],
                    "location": f"{item['file']}:{item['line']}",
                    "commit": commit_sha,
                }
                symbols.append(symbol_info)
    return JSONResponse(status_code=200, content={"symbols": symbols})


def impact_logic(symbol: str, repo_url: str, commit_sha: str):
    symbol_info = {}

    # Query symbol info from Postgres
    with POOL.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                find_exact_symbol,
                params={"repo_url": repo_url, "commit_sha": commit_sha, "name": symbol},
            )
            found_symbol = cur.fetchone()
            if found_symbol:
                symbol_info = {
                    "file": found_symbol["file"],
                    "line": found_symbol["line"],
                    "end_line": found_symbol.get("end_line"),
                    "name": found_symbol["name"],
                    "kind": found_symbol.get("kind"),
                    "language": found_symbol.get("language"),
                    "signature": found_symbol.get("signature"),
                    "scope": found_symbol.get("scope"),
                    "scope_kind": found_symbol.get("scope_kind"),
                }
            else:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "Symbol not found"},
                )

    name = symbol_info.get("name")
    file = symbol_info.get("file")
    line = symbol_info.get("line")
    language = symbol_info.get("language")

    print(f"Found symbol: {name}, {file}:{line}, Language: {language}")

    # Map language to tree-sitter key
    lang_key = CTAGS_TO_TREE_SITTER_MAP.get(language)
    if not lang_key:
        return JSONResponse(
            status_code=406,
            content={"status": "error", "message": "Unsupported language"},
        )

    symbol_references = []
    repo_name = repo_url.split("/")[-1]
    abs_mirror_directory = f"/var/pluk/repos/{repo_name}"

    # Check if worktree exists
    if not os.path.exists(abs_mirror_directory):
        return JSONResponse(
            status_code=505,
            content={"status": "error", "message": "Worktree not found"},
        )

    # Find symbol occurrences in files
    symbol_occurrences = git_grep_files(abs_mirror_directory, commit_sha, symbol)
    if symbol_occurrences:
        symbol_references = find_refs(
            abs_mirror_directory, commit_sha, symbol, lang_key, symbol_occurrences
        )
    else:
        return JSONResponse(
            status_code=200, content={"symbol_references": symbol_references}
        )

    return JSONResponse(
        status_code=200, content={"symbol_references": symbol_references}
    )


def diff_logic(symbol: str, from_commit: str, to_commit: str):
    # - Initialize both commits if they are not already indexed
    # - Find the symbol definition and references in both commits
    # - Compare the references and definitions to find differences
    # - Return the differences
    import json

    repo_url, commit_sha = get_repo_info()

    differences = {
        "definition_changed": False,
        "definition_changed_details": {},
        "new_references": [],
        "removed_references": [],
    }
    # Call reindex for both commits
    reindex_call_from = reindex_repo.delay(repo_url, from_commit)
    reindex_call_to = reindex_repo.delay(repo_url, to_commit)
    reindex_call_from.get()
    reindex_call_to.get()

    # Call define to get symbol info in both commits
    symbol_info_from_res = define_logic(symbol, repo_url, from_commit)
    symbol_info_to_res = define_logic(symbol, repo_url, to_commit)
    if symbol_info_from_res.status_code != 200 or symbol_info_to_res.status_code != 200:
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": "Symbol not found in one of the commits",
            },
        )
    # Compare definitions
    # Convert response bodies to JSON
    symbol_info_from = json.loads(symbol_info_from_res.body)["symbol"]
    symbol_info_to = json.loads(symbol_info_to_res.body)["symbol"]

    equivalent = False
    for key in [
        "file",
        "line",
        "end_line",
        "name",
        "kind",
        "language",
        "signature",
        "scope",
        "scope_kind",
    ]:
        if symbol_info_from.get(key) != symbol_info_to.get(key):
            equivalent = False
            break
        equivalent = True

    if not equivalent:
        differences["definition_changed"] = True
        differences["definition_changed_details"] = {
            "from": symbol_info_from,
            "to": symbol_info_to,
        }

    # Grab symbol references in both commits (impact)
    impact_from_res = impact_logic(symbol, repo_url, from_commit)
    impact_to_res = impact_logic(symbol, repo_url, to_commit)
    if impact_from_res.status_code not in [
        200,
        404,
    ] or impact_to_res.status_code not in [200, 404]:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to get symbol references in one of the commits",
            },
        )

    impact_from = json.loads(impact_from_res.body)["symbol_references"]
    impact_to = json.loads(impact_to_res.body)["symbol_references"]

    from_set = {(ref["container"], ref["file"]) for ref in impact_from}
    to_set = {(ref["container"], ref["file"]) for ref in impact_to}

    if to_set == from_set:
        return JSONResponse(status_code=200, content={"differences": differences})

    new_refs_set = to_set - from_set
    removed_refs_set = from_set - to_set

    # Find matching references to get full details
    if new_refs_set:
        differences["new_references"] = [
            ref for ref in impact_to if (ref["container"], ref["file"] in new_refs_set)
        ]
    if removed_refs_set:
        differences["removed_references"] = [
            ref
            for ref in impact_from
            if (ref["container"], ref["file"]) in removed_refs_set
        ]
    return JSONResponse(status_code=200, content={"differences": differences})
