#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/jorstors/pluk.git"
WORKDIR="${HOME}/.pluk"
COMPOSE_FILE="${WORKDIR}/docker-compose.yml"
ENV_FILE="${WORKDIR}/.env"

echo "=== Pluk bootstrap (Unix) ==="

# Check for Docker
if ! command -v docker >/dev/null; then
  echo "ERROR: Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
  exit 1
fi

# Check for docker compose (v2+)
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: 'docker compose' subcommand not available. Ensure Docker Compose v2+ is installed (modern Docker includes it)."
  exit 1
fi

# Clone or update the Pluk code
if [ -d "$WORKDIR" ]; then
  echo "[info] Updating existing Pluk installation at $WORKDIR"
  git -C "$WORKDIR" pull --ff-only || true
else
  echo "[info] Cloning Pluk into $WORKDIR"
  git clone "$REPO" "$WORKDIR"
fi

cd "$WORKDIR"

# Load .env if present
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1091
  set -o allexport
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +o allexport
fi

# Ensure .env exists with sane defaults
if [ ! -f "$ENV_FILE" ]; then
  cat <<EOF > "$ENV_FILE"
PLUK_DATABASE_URL=postgresql://pluk:plukpass@postgres:5432/pluk
PLUK_REDIS_URL=redis://redis:6379/0
EOF
  echo "[info] Created default .env at $ENV_FILE"
  set -o allexport
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +o allexport
fi

# Generate docker-compose.yml if missing
if [ ! -f "$COMPOSE_FILE" ]; then
  cat <<'EOF' > "$COMPOSE_FILE"
version: "3.9"
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
      test: ["CMD-SHELL", "pg_isready -U pluk"]
      interval: 5s
      retries: 5

  redis:
    image: redis:alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping"]
      interval: 5s
      retries: 5

  pluk:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      PLUK_DATABASE_URL: \${PLUK_DATABASE_URL}
      PLUK_REDIS_URL: \${PLUK_REDIS_URL}
    volumes:
      - ./:/workspace
    ports:
      - "8000:8000"
    command: ["pluk", "start"]

volumes:
  pluk_pgdata:
  pluk_redisdata:
EOF
  echo "[info] Generated default docker-compose.yml"
fi

echo "[info] Starting Pluk stack via Docker Compose..."
docker compose up --build -d

echo "[info] Waiting a few seconds for services to initialize..."
sleep 5

echo ""
echo " ✓ Pluk stack is running."
echo "Next steps:"
echo "  pluk init <path-to-your-git-repo>    # index a repository"
echo "  pluk search <symbol>                # start querying"
echo ""
echo "If you want to run commands inside the container:"
echo "  docker compose exec pluk pluk --help"
