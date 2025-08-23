CREATE TABLE IF NOT EXISTS repos (
  url VARCHAR(255) PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS commits (
  repo_url VARCHAR(255) NOT NULL REFERENCES repos(url) ON DELETE CASCADE,
  sha VARCHAR(255) NOT NULL,
  committed_at TIMESTAMP,
  PRIMARY KEY (repo_url, sha)
);

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

CREATE INDEX IF NOT EXISTS idx_symbols_commit_sha_name ON symbols (commit_sha, name);
