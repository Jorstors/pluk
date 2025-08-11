import os
from celery import Celery

celery = Celery(
  "worker",
  broker=os.getenv("PLUK_REDIS_URL"),
  backend=os.getenv("PLUK_REDIS_URL"),
)

@celery.task
def reindex_repo(repo_url: str, commit: str = "HEAD"):
    # TODO: clone into a volume, parse AST, write to Postgres
    return {"status": "queued", "repo": repo_url, "commit": commit}
