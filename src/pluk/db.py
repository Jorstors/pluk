# src/pluk/db.py
"""
Local SQLite storage for the Pluk index.

The whole index lives in a single file under PLUK_HOME (default ~/.pluk).
There is one writer and one reader -- this process -- so no pool is needed.
"""

import os
import sqlite3
from pathlib import Path

from pluk.SQL_UTIL.operations import (
    SCHEMA,
    read_schema_version,
    write_schema_version,
    read_state,
    write_state,
)

# Bump when the schema changes, and add the upgrade step in ensure_schema().
SCHEMA_VERSION = 1


def pluk_home() -> Path:
    return Path(os.environ.get("PLUK_HOME") or (Path.home() / ".pluk"))


def db_path() -> Path:
    return pluk_home() / "pluk.db"


def connect() -> sqlite3.Connection:
    """Open the index, creating and migrating it if necessary."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")

    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Create the schema, or refuse an index this version cannot read.

    Upgrade steps go here as the version climbs, so an existing index never
    needs a full reindex.
    """
    conn.executescript(SCHEMA)

    row = conn.execute(read_schema_version).fetchone()
    if row is None:
        conn.execute(write_schema_version, {"version": SCHEMA_VERSION})
    elif row["version"] != SCHEMA_VERSION:
        raise RuntimeError(
            f"Index at {db_path()} was written by schema version {row['version']}, "
            f"but this Pluk expects version {SCHEMA_VERSION}. "
            f"Delete the file to reindex from scratch."
        )
    conn.commit()


def get_state(conn: sqlite3.Connection, key: str):
    row = conn.execute(read_state, {"key": key}).fetchone()
    return row["value"] if row else None


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(write_state, {"key": key, "value": value})


def get_repo_info(conn: sqlite3.Connection):
    """The repo and commit the last `pluk init` registered."""
    return (
        get_state(conn, "repo_url"),
        get_state(conn, "commit_sha"),
        get_state(conn, "repo_path"),
    )
