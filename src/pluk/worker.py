# src/pluk/worker.py

import os
import subprocess
from celery import Celery
from time import sleep

celery = Celery(
  "worker",
  broker=os.getenv("PLUK_REDIS_URL"),
  backend=os.getenv("PLUK_REDIS_URL"),
)

# Clones into a volume, parses repo with u-ctags, then writes to Postgres
@celery.task
def reindex_repo(repo_url: str, commit: str):
    print(f"Reindexing {repo_url} at {commit}")
    # Clone the repo into var/pluk/repos
    try:
      repo_name = repo_url.split('/')[-1]
      repo_path = f"/var/pluk/repos/{repo_name}"

      if not os.path.exists(repo_path):
        subprocess.run(
            ["git", "clone", "--mirror", repo_url, repo_path],
            check=True
        )
        print(f"Cloned {repo_url} into {repo_path} successfully.")
      else:
        print(f"Repository {repo_path} already exists, updating...")
        subprocess.run(
          ["git", "-C", repo_path, "fetch", "--prune", "--tags", "--force"],
          check=True
        )

    except subprocess.CalledProcessError as e:
        print(f"Error cloning repo: {e}")
        return {"status": "ERROR", "error_message": str(e)}

    return {"status": "FINISHED"}
