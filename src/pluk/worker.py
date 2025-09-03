# src/pluk/worker.py

import os
import subprocess
from celery import Celery
import json
from pluk.db import POOL
from pluk.SQL_UTIL.operations import (
    create_repos,
    create_commits,
    create_symbols,
    create_idx_symbols_commit_sha_name,
    insert_repo,
    insert_commit,
    insert_symbol,
)

celery = Celery(
    "worker",
    broker=os.getenv("PLUK_REDIS_URL"),
    backend=os.getenv("PLUK_REDIS_URL"),
)


@celery.task
def reindex_repo(repo_url: str, commit_sha: str):
    """
    Reindex a repository by cloning it, checking out a specific commit sha,
    and then parsing it with u-ctags.

    Parsed data is stored in a Postgres database.
    """
    print(f"Reindexing {repo_url} at {commit_sha}")
    # Clone the repo into var/pluk/repos
    try:
        repo_name = repo_url.split("/")[-1]  # project.git
        absolute_repo_path = (
            f"/var/pluk/repos/{repo_name}"  # /var/pluk/repos/project.git
        )
        relative_repo_worktree_path = f"worktrees/{commit_sha}"  # worktrees/{commit}
        absolute_repo_worktree_path = f"{absolute_repo_path}/{relative_repo_worktree_path}"  # /var/pluk/repos/project.git/worktree/{commit}
        absolute_sha_path = (
            f"{absolute_repo_path}/.sha"  # /var/pluk/repos/project.git/.sha
        )

        # Read the previous commit SHA if it exists
        prev_commit = None
        if os.path.exists(absolute_sha_path):
            with open(absolute_sha_path, "r") as f:
                prev_commit = f.read().strip()

        # If the repository already exists, fetch the latest changes
        has_fetched_changes = False
        if os.path.exists(absolute_repo_path):
            print(
                f"Repository {absolute_repo_path} already exists, fetching latest changes..."
            )
            # Query for fetched changes
            check = subprocess.check_output(
                [
                    "git",
                    "-C",
                    absolute_repo_path,
                    "fetch",
                    "--prune",
                    "--tags",
                    "--force",
                ],
                text=True,
            )
            if check:
                has_fetched_changes = True
                print(f"Fetched changes for {absolute_repo_path}")
            else:
                print(f"No changes fetched for {absolute_repo_path}")

        # If nothing has changed since the last indexed commit, skip reindexing
        if (
            os.path.exists(absolute_repo_path)
            and prev_commit == commit_sha
            and not has_fetched_changes
        ):
            print(
                f"Repository {absolute_repo_path} is already at {commit_sha}, skipping..."
            )
            return {"status": "FINISHED"}

        if not os.path.exists(absolute_repo_path):
            print(f"Cloning {repo_url} into var/pluk/repos...")
            subprocess.run(
                ["git", "clone", "--mirror", repo_url, absolute_repo_path], check=True
            )

        # Makes var/pluk/repos/{repo_name}/worktree
        print(f"Checking out commit {commit_sha} in {absolute_repo_path}...")
        if not os.path.exists(absolute_repo_worktree_path):
            subprocess.run(
                [
                    "git",
                    "-C",
                    absolute_repo_path,
                    "worktree",
                    "add",
                    relative_repo_worktree_path,
                    commit_sha,
                ],
                check=True,
            )
        else:
            print(
                f"Worktree {absolute_repo_worktree_path} already exists, previous worker didn't remove it. Continuing..."
            )

        # Run ctags on the repository
        CTAGS_CMD = [
            "ctags",
            "-R",
            "--fields-all=*",
            "--output-format=json",
            "--sort=no",
            "--links=no",
            "--exclude=.git",
            "--exclude=node_modules",
            "--exclude=dist",
            "--exclude=build",
            "--exclude=venv",
            "--languages=-Asciidoc,-BibTeX,-Ctags,-DBusIntrospect,-DTD,-Glade,-HTML,-Iniconf,-IPythonCell,-JavaProperties,-JSON,-Markdown,-Man,-PlistXML,-Pod,-QemuHX,-RelaxNG,-ReStructuredText,-SVG,-SystemdUnit,-Tex,-TeXBeamer,-Txt2tags,-XML,-XSLT,-Yaml,-YumRepo,-RpmMacros,-RpmSpec,-Passwd,-WindRes,-FunctionParameters,-PythonLoggingConfig,-R6Class,-S4Class",
            "-o",
            "-",
        ]
        tags_str = subprocess.check_output(
            CTAGS_CMD, cwd=absolute_repo_worktree_path, text=True
        )
        # Parse JSON objects by line
        print(f"Parsing tags for {repo_url} at {commit_sha}...")
        tags_obj_array = []
        for line in tags_str.splitlines():
            tags_obj_array.append(json.loads(line))
        print(tags_obj_array)

        with POOL.connection() as conn:
            with conn.cursor() as cur:
                # Insert symbols (tags) into the database
                print(f"Inserting repo {repo_url} into the database...")
                cur.execute(insert_repo, (repo_url,))
                print(f"Inserting commit {commit_sha} into the database...")
                cur.execute(insert_commit, (repo_url, commit_sha, None))
                print(f"Inserting symbols into the database...")
                for tag in tags_obj_array:
                    cur.execute(
                        insert_symbol,
                        params={
                            "repo_url": repo_url,
                            "commit_sha": commit_sha,
                            "file": tag.get("path", "unknown"),
                            "line": tag.get("line", -1),
                            "end_line": tag.get("end", None),
                            "name": tag.get("name", "unknown"),
                            "kind": tag.get("kind", None),
                            "language": tag.get("language", None),
                            "signature": tag.get("signature", None),
                            "scope": tag.get("scope", None),
                            "scope_kind": tag.get("scopeKind", None),
                        },
                    )
                conn.commit()
                print(f"Finished inserting symbols for {repo_url} at {commit_sha}")

        # Save the current commit SHA
        with open(absolute_sha_path, "w") as f:
            f.write(commit_sha)

    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e}")
        return {"status": "ERROR", "error_message": str(e)}

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"status": "ERROR", "error_message": str(e)}

    finally:
        # Removes var/pluk/repos/{repo_name}/{commit}/
        if os.path.exists(absolute_repo_worktree_path):
            print(f"Removing worktree for {commit_sha} in {absolute_repo_path}...")
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        absolute_repo_path,
                        "worktree",
                        "remove",
                        "--force",
                        commit_sha,
                    ],
                )
            except subprocess.CalledProcessError as e:
                print(f"Subprocess error: {e}")
                return {"status": "ERROR", "error_message": str(e)}

    return {"status": "FINISHED"}
