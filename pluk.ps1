#!/usr/bin/env pwsh
# pluk.ps1 - Windows bootstrapper for Pluk
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = "https://github.com/jorstors/pluk.git"
$workdir = "$env:USERPROFILE\.pluk"
$composeFile = Join-Path $workdir "docker-compose.yml"
$envFile = Join-Path $workdir ".env"

Write-Host "===== Pluk Bootstrap (Windows) =====" -ForegroundColor Cyan

# Prereqs
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker CLI not found. Install/start Docker Desktop and ensure it's running."
    exit 1
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git not found. Install Git to proceed."
    exit 1
}

$oldErrPref = $ErrorActionPreference
$ErrorActionPreference = 'SilentlyContinue'
docker info 2>$null | Out-Null
$ErrorActionPreference = $oldErrPref
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon unreachable. Start Docker Desktop and try again."
    exit 1
}

# Ensure Linux containers (images are Linux-based)
$serverOs = (& docker version --format '{{.Server.Os}}' 2>$null).Trim().ToLower()
if ($serverOs -and $serverOs -ne 'linux') {
    Write-Error "Docker server is running on '$serverOs'. Switch to Linux containers."
    exit 1
}

# Clone or update repo
if (Test-Path $workdir) {
    Write-Host "[info] Updating Pluk at $workdir"
    git -C $workdir pull --ff-only | Out-Null
} else {
    Write-Host "[info] Cloning Pluk into $workdir"
    git clone $repo $workdir | Out-Null
}

Set-Location $workdir

# Ensure .env exists with sane defaults
if (-not (Test-Path $envFile)) {
    @"
PLUK_DATABASE_URL=postgresql://pluk:plukpass@postgres:5432/pluk
PLUK_REDIS_URL=redis://redis:6379/0
"@ | Out-File -Encoding utf8 $envFile
    Write-Host "[info] Created default .env"
}

# Generate docker-compose.yml if missing
if (-not (Test-Path $composeFile)) {
    @"
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
      PLUK_DATABASE_URL: '$${PLUK_DATABASE_URL}'
      PLUK_REDIS_URL: '$${PLUK_REDIS_URL}'
    volumes:
      - ./:/app
    ports:
      - '8000:8000'
    command: ['pluk', 'start']

volumes:
  pluk_pgdata:
  pluk_redisdata:

"@ | Out-File -Encoding utf8 $composeFile
    Write-Host "[info] Generated docker-compose.yml"
}

# Ensure docker compose is available
$composeTest = & docker compose version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "'docker compose' subcommand not available. Ensure Docker CLI v2 is installed."
    exit 1
}

Write-Host "[info] Validating compose configuration..."
docker compose config | Out-Null

Write-Host "[info] Pulling images..."
docker compose pull --quiet

Write-Host "[info] Starting stack..."
docker compose up --build -d

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "===== Pluk stack is running! =====" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  pluk init <path-to-your-git-repo>    # index a repository" -ForegroundColor Yellow
Write-Host "  pluk search <symbol>                # start querying" -ForegroundColor Yellow
Write-Host ""
Write-Host "Inside container:" -ForegroundColor Magenta
Write-Host "  docker compose exec pluk pluk --help" -ForegroundColor DarkGray
