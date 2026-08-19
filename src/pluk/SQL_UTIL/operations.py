# src/pluk/SQL_UTIL/operations.py
"""
The SQLite schema and every query the rest of Pluk runs against it.

Kept as plain strings rather than an ORM so `db.py` and `query.py` can stay
thin wrappers; this is the one place schema and SQL changes need to happen.
"""

import textwrap

SCHEMA = textwrap.dedent("""
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS state (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS repos (
  url TEXT PRIMARY KEY,
  path TEXT
);

CREATE TABLE IF NOT EXISTS commits (
  repo_url TEXT NOT NULL REFERENCES repos(url) ON DELETE CASCADE,
  sha TEXT NOT NULL,
  committed_at TEXT,
  PRIMARY KEY (repo_url, sha)
);

CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_url TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  file TEXT NOT NULL,
  line INTEGER NOT NULL,
  end_line INTEGER,
  name TEXT NOT NULL,
  kind TEXT,
  language TEXT,
  signature TEXT,
  scope TEXT,
  scope_kind TEXT,
  FOREIGN KEY (repo_url, commit_sha) REFERENCES commits(repo_url, sha) ON DELETE CASCADE,
  UNIQUE (repo_url, commit_sha, file, line, name)
);

CREATE INDEX IF NOT EXISTS idx_symbols_commit_sha_name ON symbols (commit_sha, name);
""")

read_schema_version = "SELECT version FROM schema_version LIMIT 1;"

write_schema_version = "INSERT INTO schema_version (version) VALUES (:version)"

read_state = "SELECT value FROM state WHERE key = :key;"

write_state = textwrap.dedent("""
  INSERT INTO state (key, value) VALUES (:key, :value)
  ON CONFLICT (key) DO UPDATE SET value = excluded.value
""")

insert_repo = textwrap.dedent("""
  INSERT INTO repos (url, path) VALUES (?, ?)
  ON CONFLICT (url) DO UPDATE SET path = excluded.path
""")

insert_commit = textwrap.dedent("""
  INSERT INTO commits (repo_url, sha, committed_at) VALUES (?, ?, ?)
  ON CONFLICT (repo_url, sha) DO NOTHING
""")

insert_symbol = textwrap.dedent("""
  INSERT INTO symbols (repo_url, commit_sha, file, line, end_line, name, kind, language, signature, scope, scope_kind)
  VALUES (:repo_url, :commit_sha, :file, :line, :end_line, :name, :kind, :language, :signature, :scope, :scope_kind)
  ON CONFLICT (repo_url, commit_sha, file, line, name) DO NOTHING
""")

commit_is_indexed = (
    "SELECT 1 FROM commits WHERE repo_url = :repo_url AND sha = :commit_sha LIMIT 1;"
)

# SQL query for fuzzy matching of symbol names within a specific commit.
# SQLite's LIKE is case-insensitive for ASCII, so it stands in for Postgres ILIKE.
find_symbols_fuzzy_match = textwrap.dedent("""
SELECT file, line, end_line, name, kind, language, signature, scope, scope_kind
FROM symbols
WHERE repo_url = :repo_url AND commit_sha = :commit_sha AND name LIKE '%' || :symbol || '%'
ORDER BY (name LIKE :symbol) DESC, LENGTH(name), file, line
LIMIT 50;
""")

find_exact_symbol = textwrap.dedent("""
SELECT file, line, end_line, name, kind, language, signature, scope, scope_kind
FROM symbols
WHERE repo_url = :repo_url AND commit_sha = :commit_sha AND name = :name
LIMIT 1;
""")
