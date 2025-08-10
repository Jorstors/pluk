import os
from celery import Celery

app = Celery(
  "worrker",
  broker=os.getenv("PLUK_REDIS_URL"),
  backend=os.getenv("PLUK_REDIS_URL"),
)

@app.task
def reindex_repository(repo_url: str, commit: str = "HEAD"):
    # TODO: clone into a volume, parse AST, write to Postgres
    return {"status": "queued", "repo": repo_url, "commit": commit}
