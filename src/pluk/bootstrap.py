# src/pluk/bootstrap.py
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
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    environment:
      PLUK_DATABASE_URL: postgresql://pluk:plukpass@postgres:5432/pluk
      PLUK_REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    entrypoint: ["plukd"]
    command: ["start"]

volumes:
  pluk_pgdata:
  pluk_redisdata:
""")

def ensure_bootstrap():
  """
  Ensure the Docker Compose stack is set up for Pluk.

  This function checks if the necessary Docker Compose file exists,
  creates it if not, and brings up the Docker stack if needed.
  """
  home = os.path.expanduser("~/.pluk")
  os.makedirs(home, exist_ok=True)
  yml_path = os.path.join(home, "docker-compose.yml")
  created = False
  if not os.path.exists(yml_path):
    with open(yml_path, "w") as f:
      f.write(COMPOSE_YML)
      created = True
      print("Created Docker Compose file at", yml_path)
  else:
    with open(yml_path, "r+") as f:
      if f.read() != COMPOSE_YML:
        print("Updating existing Docker Compose file at", yml_path)
        f.seek(0)
        f.write(COMPOSE_YML)
        f.truncate()
        created = True

  # bring up the stack if it was created or updated
  res = subprocess.run(
    ["docker", "compose", "-f", yml_path, "ps", "--status=running"],
    check=True,
    capture_output=True,
    text=True
  )

  running = "pluk" in res.stdout

  if created or not running:
    print("Starting Pluk services...")
    subprocess.run(
      ["docker", "compose", "-f", yml_path, "up", "-d"],
      check=True,
    )
    print("Pluk services are running.")
  if created:
    print("Pluk bootstrap complete! Pluk services are running.")

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
    process = subprocess.Popen(
      cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True
    )

    # Read and print output in real-time
    for line in process.stdout:
      print(line, end="")

    # Read any errors as well
    for line in process.stderr:
      print(line, end="", file=sys.stderr)

    process.wait()

    if process.returncode != 0:
      print(f"Command failed with exit code {process.returncode}", file=sys.stderr)
      sys.exit(process.returncode)

  except Exception as e:
    print(f"Error executing command: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
  main()
