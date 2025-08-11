from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pluk.worker import celery, reindex_repo
from pydantic import BaseModel

app = FastAPI()

class ReindexRequest(BaseModel):
    repo_url: str
    commit: str = None

@app.get("/health")
def health():
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.post("/reindex")
def reindex(request: ReindexRequest):
    job = reindex_repo.delay(request.repo_url, request.commit)
    if job:
        return JSONResponse(status_code=200, content={"status": "accepted", "job_id": job.id})
    return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to enqueue job"})

@app.get("/status/{job_id}")
def status(job_id: str):
    res = celery.AsyncResult(job_id)
    payload = {"status": res.status}
    if res.result:
        payload["result"] = res.result
    return JSONResponse(status_code=200, content=payload)
