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
  file TEXT NOT NULL,
  line INT NOT NULL,
  end_line INT,
  name VARCHAR(255) NOT NULL,
  kind VARCHAR(255),
  language VARCHAR(255),
  signature TEXT,
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
  INSERT INTO symbols (repo_url, commit_sha, file, line, end_line, name, kind, language, signature, scope, scope_kind)
  VALUES (%(repo_url)s, %(commit_sha)s, %(file)s, %(line)s, %(end_line)s, %(name)s, %(kind)s, %(language)s, %(signature)s, %(scope)s, %(scope_kind)s) ON CONFLICT (repo_url, commit_sha, file, line, name) DO NOTHING
""")

# SQL query for fuzzy matching of symbol names within a specific commit
find_symbols_fuzzy_match = textwrap.dedent("""
SELECT file, line, end_line, name, kind, language, signature, scope, scope_kind
FROM symbols
WHERE repo_url = %(repo_url)s AND commit_sha = %(commit_sha)s AND name ILIKE '%%' || %(symbol)s || '%%'
ORDER BY (name ILIKE %(symbol)s) DESC, LENGTH(name), file, line
LIMIT 50;
""")

find_exact_symbol = textwrap.dedent("""
SELECT file, line, end_line, name, kind, language, signature, scope, scope_kind
FROM symbols
WHERE repo_url = %(repo_url)s AND commit_sha = %(commit_sha)s AND name = %(name)s
LIMIT 1;
""")

find_scope_dependencies = textwrap.dedent("""
WITH RECURSIVE deps(id) AS (
  SELECT id
  FROM symbols
  WHERE repo_url=%(repo_url)s AND commit_sha=%(commit_sha)s AND name=%(name)s

  UNION ALL

  SELECT c.id
  FROM symbols c
  JOIN symbols p
    ON c.repo_url=p.repo_url
    AND c.commit_sha=p.commit_sha
    AND c.file=p.file
    AND c.scope=p.name
  JOIN deps d ON p.id=d.id
  WHERE c.repo_url=%(repo_url)s AND c.commit_sha=%(commit_sha)s
)
SELECT s.file, s.line, s.end_line, s.name, s.kind, s.signature, s.scope, s.scope_kind
FROM symbols s
JOIN deps d ON s.id=d.id
ORDER BY s.file, s.line;
""")
