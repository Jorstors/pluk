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
    find_scope_dependencies
)

app = FastAPI()

redis_client = redis.Redis.from_url(os.environ.get("PLUK_REDIS_URL"), decode_responses=True)

def get_repo_info():
    repo_url = redis_client.get("repo_url")
    commit_sha = redis_client.get("commit_sha")
    if not repo_url or not commit_sha:
        return None, None
    return repo_url, commit_sha

no_init_response = JSONResponse(status_code=500, content={"status": "error", "message": "No repository initialized. Please reindex."})

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
        return JSONResponse(status_code=200, content={"status": "queued", "job_id": job.id})
    return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to enqueue job"})

@app.get("/status/{job_id}")
def status(job_id: str):
    res = celery.AsyncResult(job_id)
    if res.ready():
        job_result = res.result
        return JSONResponse(status_code=200, content={"status": res.status, "result": job_result})
    return JSONResponse(status_code=200, content={"status": res.status})

# === Data base queries ===

@app.get("/define/{symbol}")
def define(symbol: str):
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response
    return JSONResponse(status_code=200, content={"definition": symbol, "location": "file:line", "commit": "abc123"})

@app.get("/search/{symbol}")
def search(symbol: str):
    import ast
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response
    symbols = []
    with POOL.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(find_symbols_fuzzy_match, params={"repo_url": repo_url, "commit_sha": commit_sha, "symbol": symbol})
            res = cur.fetchall()
            print(f"Search results for {symbol}: {res}")
            for item in res:
                symbol_info = {
                    "name": item['name'],
                    "location": f"{item['file']}:{item['line']}",
                    "commit": commit_sha,
                    "references": None
                }
                symbols.append(symbol_info)
    return JSONResponse(status_code=200, content={"symbols": symbols})

@app.get("/impact/{symbol}")
def impact(symbol: str):
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response
    return JSONResponse(status_code=200, content={"impacted_files": ["file1.py", "file2.py"]})

@app.get("/diff/{symbol}/{from_commit}/{to_commit}")
def diff(symbol: str, from_commit: str, to_commit: str):
    repo_url, commit_sha = get_repo_info()
    if not repo_url or not commit_sha:
        return no_init_response
    return JSONResponse(status_code=200, content={"differences": ["diff1", "diff2"]})
