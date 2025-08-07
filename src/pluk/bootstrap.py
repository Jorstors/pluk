import os, subprocess, sys, textwrap

COMPOSE_YML = textwrap.dedent("""
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

  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - pluk_redisdata:/data

  pluk:
    image: jorstors/pluk:latest
    depends_on:
      - postgres
      - redis
    environment:
      PLUK_DATABASE_URL: postgresql://pluk:plukpass@postgres:5432/pluk
      PLUK_REDIS_URL: redis://redis:6379/0
    volumes:
      - ./:/app
    ports:
      - "8000:8000"
    entrypoint: ["plukd"]
    command: ["start"]

volumes:
  pluk_pgdata:
  pluk_redisdata:
""")

def ensure_bootstrap():
  home = os.path.expanduser("~/.pluk")
  os.makedirs(home, exist_ok=True)
  yml_path = os.path.join(home, "docker-compose.yml")
  if not os.path.exists(yml_path):
    with open(yml_path, "w") as f:
      f.write(COMPOSE_YML)
    # bring up the stack
    subprocess.run(
      ["docker-compose", "-f", yml_path, "up", "-d"],
      check=True
    )
    print("Pluk bootstrap complete! Docker stack is running.")

def main():
  """Entry point for pluk bootstrap."""

  # Bootstrap infra if needed
  ensure_bootstrap()

  # Forward to plukd (container) CLI
  home = os.path.expanduser("~/.pluk/docker-compose.yml")
  cmd = [
    "docker-compose", "-f", home, "exec", "pluk", "plukd"
  ] + sys.argv[1:]

  # Execute the command and capture output

  try:
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
  except subprocess.CalledProcessError as e:
    print(f"Error: {e}", file=sys.stderr)
    if e.stdout:
      print(e.stdout)
    if e.stderr:
      print(e.stderr, file=sys.stderr)
    sys.exit(e.returncode)

if __name__ == "__main__":
  main()
