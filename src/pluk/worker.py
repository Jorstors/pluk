# src/pluk/worker.py

import os
import subprocess
from celery import Celery

celery = Celery(
  "worker",
  broker=os.getenv("PLUK_REDIS_URL"),
  backend=os.getenv("PLUK_REDIS_URL"),
)

@celery.task
def reindex_repo(repo_url: str, commit: str):
    """
    Reindex a repository by cloning it, checking out a specific commit sha,
    and then parsing it with u-ctags.

    Parsed data is stored in a Postgres database.
    """
    print(f"Reindexing {repo_url} at {commit}")
    # Clone the repo into var/pluk/repos
    try:
      repo_name = repo_url.split('/')[-1]                                       # project.git
      absolute_repo_path = f"/var/pluk/repos/{repo_name}"                       # /var/pluk/repos/project.git
      absolute_repo_worktree_path = f"{absolute_repo_path}/worktrees/{commit}"  # /var/pluk/repos/project.git/worktree/{commit}
      absolute_sha_path = f"{absolute_repo_path}/.sha"                          # /var/pluk/repos/project.git/.sha

      # Read the previous commit SHA if it exists
      prev_commit = None
      if os.path.exists(absolute_sha_path):
        with open(absolute_sha_path, "r") as f:
            prev_commit = f.read().strip()

      # If the repository already exists, fetch the latest changes
      has_fetched_changes = False
      if os.path.exists(absolute_repo_path):
        print(f"Repository {absolute_repo_path} already exists, fetching latest changes...")
        # Query for fetched changes
        check = subprocess.check_output(
          ["git", "-C", absolute_repo_path, "fetch", "--prune", "--tags", "--force"],
          text=True,
        )
        if check:
          has_fetched_changes = True
          print(f"Fetched changes for {absolute_repo_path}")
        else:
          print(f"No changes fetched for {absolute_repo_path}")

      # If nothing has changed since the last indexed commit, skip reindexing
      if os.path.exists(absolute_repo_path) and prev_commit == commit and not has_fetched_changes:
        print(f"Repository {absolute_repo_path} is already at {commit}, skipping...")
        return {"status": "FINISHED"}

      if not os.path.exists(absolute_repo_path):
        print(f"Cloning {repo_url} into var/pluk/repos...")
        subprocess.run(
              ["git", "clone", "--mirror", repo_url, absolute_repo_path],
              check=True
          )

      # Makes var/pluk/repos/{repo_name}/worktree
      print(f"Checking out commit {commit} in {absolute_repo_path}...")
      subprocess.run(
        ["git", "-C", absolute_repo_path, "worktree", "add", absolute_repo_worktree_path, commit],
        check=True
      )

      # Save the current commit SHA
      with open(absolute_sha_path, "w") as f:
        f.write(commit)

    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e}")
        return {"status": "ERROR",
                "error_message": str(e)}

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"status": "ERROR",
                "error_message": str(e)}

    finally:
      # Removes var/pluk/repos/{repo_name}/{commit}/
      if os.path.exists(absolute_repo_worktree_path):
        print(f"Removing worktree for {commit} in {absolute_repo_path}...")
        try:
          subprocess.run(
              ["git", "-C", absolute_repo_path, "worktree", "remove", absolute_repo_worktree_path, "--force"],
          )
        except subprocess.CalledProcessError as e:
          print(f"Subprocess error: {e}")
          return {"status": "ERROR",
                  "error_message": str(e)}

    return {"status": "FINISHED"}
