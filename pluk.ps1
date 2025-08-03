# pluk.ps1 - Windows bootstrapper for Pluk
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = "https://github.com/jorstors/pluk.git"
$workdir = "$env:USERPROFILE\.pluk"
$composeFile = Join-Path $workdir "docker-compose.yml"
$envFile = Join-Path $workdir ".env"

Write-Host "=== Pluk bootstrap (Windows) ==="

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker not found. Please install Docker Desktop: https://docs.docker.com/get-docker/"
    exit 1
}

# Clone or update
if (Test-Path $workdir) {
    Write-Host "[info] Updating Pluk at $workdir"
    git -C $workdir pull --ff-only | Out-Null
} else {
    Write-Host "[info] Cloning Pluk into $workdir"
    git clone $repo $workdir | Out-Null
}

Set-Location $workdir

# Load .env if present
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

# Create .env defaults if missing
if (-not (Test-Path $envFile)) {
    @"
PLUK_DATABASE_URL=postgresql://pluk:plukpass@postgres:5432/pluk
PLUK_REDIS_URL=redis://redis:6379/0
"@ | Out-File -Encoding utf8 $envFile
    Write-Host "[info] Created default .env"
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

# Generate docker-compose.yml if missing
if (-not (Test-Path $composeFile)) {
    @"
version: '3.9'
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
      - '8000:8000'
    command: ['pluk', 'start']

volumes:
  pluk_pgdata:
  pluk_redisdata:
"@ | Out-File -Encoding utf8 $composeFile
    Write-Host "[info] Generated docker-compose.yml"
}

Write-Host "[info] Starting Docker Compose stack..."
docker compose up --build -d

Start-Sleep -Seconds 5

Write-Host ""
Write-Host " ✓ Pluk stack is running."
Write-Host "Next steps:"
Write-Host "  pluk init <path-to-your-git-repo>    # index a repository"
Write-Host "  pluk search <symbol>                # start querying"
Write-Host ""
Write-Host "You can also run inside container:"
Write-Host "  docker compose exec pluk pluk --help"
