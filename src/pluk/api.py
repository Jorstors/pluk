from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pluk.worker import celery, reindex_repo
from pydantic import BaseModel
from pluk.db import POOL

app = FastAPI()

class ReindexRequest(BaseModel):
    repo_url: str
    commit: str = "HEAD"
class DiffRequest(BaseModel):
    from_commit: str
    to_commit: str
    symbol: str

define_query = """
SELECT * FROM symbols WHERE name = %(symbol)s
"""

search_query = """
SELECT * FROM symbols WHERE name ILIKE %(symbol)s
"""

impact_query = """
SELECT * FROM symbols WHERE name = %(symbol)s
"""

diff_query = """
SELECT * FROM symbols WHERE name = %(symbol)s
"""

@app.get("/health")
def health():
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.post("/reindex")
def reindex(request: ReindexRequest):
    job = reindex_repo.delay(request.repo_url, request.commit)
    if job:
        return JSONResponse(status_code=200, content={"status": "queued", "job_id": job.id})
    return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to enqueue job"})

@app.get("/status/{job_id}")
def status(job_id: str):
    res = celery.AsyncResult(job_id)
    if res.ready():
        return JSONResponse(status_code=200, content={"status": "finished", "result": res.result})
    return JSONResponse(status_code=200, content={"status": res.status})

# === Data base queries ===

@app.get("/define/{symbol}")
def define(symbol: str):
    return JSONResponse(status_code=200, content={"definition": symbol, "location": "file:line", "commit": "abc123"})

@app.get("/search/{symbol}")
def search(symbol: str):
    return JSONResponse(status_code=200, content={"symbols": [{"name": symbol, "location": "file:line","commit": "abc123", "references": ["ref1", "ref2"]}]})

@app.get("/impact/{symbol}")
def impact(symbol: str):
    return JSONResponse(status_code=200, content={"impacted_files": ["file1.py", "file2.py"]})

@app.get("/diff")
def diff(request: DiffRequest):
    return JSONResponse(status_code=200, content={"differences": ["diff1", "diff2"]})
