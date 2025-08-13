import os
from celery import Celery
from time import sleep

celery = Celery(
  "worker",
  broker=os.getenv("PLUK_REDIS_URL"),
  backend=os.getenv("PLUK_REDIS_URL"),
)

@celery.task
def reindex_repo(repo_url: str, commit: str):
    # TODO: clone into a volume, parse AST, write to Postgres
    print(f"Reindexing {repo_url} at {commit}")
    sleep(5)  # Simulate long-running task
    return {"status": "finished"}
