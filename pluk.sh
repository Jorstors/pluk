#!/usr/bin/env bash
set -euo pipefail

repo="https://github.com/jorstors/pluk.git"
workdir="$HOME/.pluk"
composeFile="$workdir/docker-compose.yml"
envFile="$workdir/.env"

echo "===== Pluk Bootstrap (Unix) ====="

# Prereqs
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker CLI not found. Install/start Docker and ensure the daemon is running." >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found. Install git to proceed." >&2
  exit 1
fi

# Suppress Docker errors, then check exit code
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon unreachable. Start Docker and try again." >&2
  exit 1
fi

# Ensure Linux containers (images are Linux-based)
server_os=$(docker version --format '{{.Server.Os}}' 2>/dev/null || true)
server_os=${server_os,,}
if [[ -n "$server_os" && "$server_os" != "linux" ]]; then
  echo "ERROR: Docker server is running on '$server_os'. Need Linux containers." >&2
  exit 1
fi

# Clone or update repo
if [[ -d "$workdir" ]]; then
  echo "[info] Updating Pluk at $workdir"
  git -C "$workdir" pull --ff-only >/dev/null
else
  echo "[info] Cloning Pluk into $workdir"
  git clone "$repo" "$workdir" >/dev/null
fi

cd "$workdir"

# Ensure .env exists
if [[ ! -f "$envFile" ]]; then
  cat <<EOF > "$envFile"
PLUK_DATABASE_URL=postgresql://pluk:plukpass@postgres:5432/pluk
PLUK_REDIS_URL=redis://redis:6379/0
EOF
  echo "[info] Created default .env"
fi

# Generate docker-compose.yml if missing
if [[ ! -f "$composeFile" ]]; then
  cat <<'EOF' > "$composeFile"
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: pluk
      POSTGRES_PASSWORD: plukpass
      POSTGRES_DB: pluk
    volumes:
      - pluk_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U pluk']
      interval: 5s
      retries: 5

  redis:
    image: redis:alpine
    restart: unless-stopped
    healthcheck:
      test: ['CMD-SHELL', 'redis-cli ping']
      interval: 5s
      retries: 5

  pluk:
    image: jorstors/pluk:latest
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    environment:
      PLUK_DATABASE_URL: '${PLUK_DATABASE_URL}'
      PLUK_REDIS_URL: '${PLUK_REDIS_URL}'
    volumes:
      - ./:/app
    ports:
      - '8000:8000'
    command: ['pluk', 'start']

volumes:
  pluk_pgdata:
  pluk_redisdata:
EOF
  echo "[info] Generated docker-compose.yml"
fi

# Determine compose command
if docker compose version >/dev/null 2>&1; then
  dc_cmd="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  dc_cmd="docker-compose"
else
  echo "ERROR: Neither 'docker compose' nor 'docker-compose' available." >&2
  exit 1
fi

echo "[info] Validating compose configuration..."
$dc_cmd config >/dev/null

echo "[info] Pulling images..."
$dc_cmd pull --quiet

echo "[info] Starting stack..."
$dc_cmd up --build -d

sleep 3

echo
echo "===== Pluk stack is running! ====="
echo "Next steps:"
echo "  pluk init <path-to-your-git-repo>    # index a repository"
echo "  pluk search <symbol>                 # start querying"
echo
echo "Inside container:"
echo "  $dc_cmd exec pluk pluk --help"
