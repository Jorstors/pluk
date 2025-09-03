from pluk.db import POOL
from pluk.SQL_UTIL.operations import (
    create_repos,
    create_commits,
    create_symbols,
    create_idx_symbols_commit_sha_name,
)


def init_db():
    with POOL.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_repos)
            cur.execute(create_commits)
            cur.execute(create_symbols)
            cur.execute(create_idx_symbols_commit_sha_name)


if __name__ == "__main__":
    init_db()
    print("[init_db] Database schema initialized successfully.")
    POOL.close()
