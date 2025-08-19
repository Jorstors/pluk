# src/pluk/SQL_UTIL/operations.py
import textwrap

create_repos = textwrap.dedent("""
  CREATE TABLE IF NOT EXISTS repos (
    url VARCHAR(255) PRIMARY KEY
  );
""")

create_commits = textwrap.dedent("""
  CREATE TABLE IF NOT EXISTS commits (
    repo_url VARCHAR(255) NOT NULL REFERENCES repos(url) ON DELETE CASCADE,
    sha VARCHAR(255) NOT NULL,
    committed_at TIMESTAMP,
    PRIMARY KEY (repo_url, sha)
  );
""")

create_symbols = textwrap.dedent("""
  CREATE TABLE IF NOT EXISTS symbols (
    id BIGSERIAL PRIMARY KEY,
    repo_url VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(255) NOT NULL,
    FOREIGN KEY (repo_url, commit_sha) REFERENCES commits(repo_url, sha) ON DELETE CASCADE,
    file VARCHAR(255) NOT NULL,
    line INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(255),
    signature VARCHAR(255),
    scope VARCHAR(255),
    scope_kind VARCHAR(255),
    UNIQUE (repo_url, commit_sha, file, line, name)
  );
""")

create_idx_symbols_commit_sha_name = textwrap.dedent("""
  CREATE INDEX IF NOT EXISTS idx_symbols_commit_sha_name ON symbols (commit_sha, name);
""")

insert_repo = textwrap.dedent("""
  INSERT INTO repos (url) VALUES (%s) ON CONFLICT (url) DO NOTHING
""")

insert_commit = textwrap.dedent("""
  INSERT INTO commits (repo_url, sha, committed_at) VALUES (%s, %s, %s) ON CONFLICT (repo_url, sha) DO NOTHING
""")

insert_symbol = textwrap.dedent("""
  INSERT INTO symbols (repo_url, commit_sha, file, line, name, kind, signature, scope, scope_kind) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (repo_url, commit_sha, file, line, name) DO NOTHING
""")
