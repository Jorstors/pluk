# src/pluk/shim.py
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pluk -d pluk -h localhost"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - pluk_redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    image: jorstors/pluk:latest
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      PLUK_DATABASE_URL: postgresql://pluk:plukpass@postgres:5432/pluk
      PLUK_REDIS_URL: redis://redis:6379/0
    expose:
      - "8000"
    command: ["uvicorn", "pluk.api:app", "--host", "0.0.0.0", "--port", "8000"]

  worker:
    image: jorstors/pluk:latest
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      api:
        condition: service_started
    environment:
      PLUK_DATABASE_URL: postgresql://pluk:plukpass@postgres:5432/pluk
      PLUK_REDIS_URL: redis://redis:6379/0
      PLUK_REPOS_DIR: /var/pluk/repos
    volumes:
      - pluk_repos:/var/pluk/repos
    command: ["celery", "-A", "pluk.worker", "worker", "-l", "info"]

  cli:
    image: jorstors/pluk:latest
    restart: unless-stopped
    depends_on:
      api:
        condition: service_started
    environment:
      PLUK_API_URL: http://api:8000
      PLUK_REPOS_DIR: /var/pluk/repos
      PYTHONUNBUFFERED: 1
    command: ["sleep", "infinity"]

volumes:
  pluk_pgdata:
  pluk_redisdata:
  pluk_repos:

""")

def ensure_running(home, yml_path):
  """
  Ensure that the Pluk services are running.

  This functions checks if the necessary Docker containers are up and running.
  If they are not running, it will return False.
  """
  import json
  os.makedirs(home, exist_ok=True)

  try:
    # Check if the expected services are running
    res = subprocess.run(
      ["docker", "compose", "-f", yml_path, "ps", "--status=running", "--format", "json"],
      check=True,
      capture_output=True,
      text=True
    )
  except subprocess.CalledProcessError as e:
    print("Error checking Docker Compose status:", e.stderr, file=sys.stderr)
    print('Please ensure Docker is installed, running, and accessible from your terminal. Try running "pluk start" again, and check for any error messages above.')
    return False

  required_services = {"postgres", "redis", "api", "worker", "cli"}
  found_services = set()

  lines = res.stdout.splitlines()

  # Parse line by line json output
  for line in lines:
    try:
      res_object = json.loads(line)
      if res_object["Service"] in required_services:
        found_services.add(res_object["Service"])
    except (json.JSONDecodeError, KeyError) as e:
      print(f"Warning: Error parsing service info: {e}", file=sys.stderr)
      continue

  # Check if all required services are found
  return {"running": bool(found_services),
          "found": found_services,
          "required": required_services}


def start_pluk_services(home, yml_path):
  """
  Ensure the Docker Compose stack is set up for Pluk.

  This function checks if the necessary Docker Compose file exists,
  creates it if not, and brings up the Docker stack if needed.
  """

  # Ensure the home directory exists
  os.makedirs(home, exist_ok=True)

  created = False
  # Create or update the Docker Compose file
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

  try:
    # Always pull the latest images before starting
    # print("Pulling latest Docker images...")
    # subprocess.run(
    #   ["docker", "compose", "-f", yml_path, "pull"],
    #   check=True,
    #   capture_output=True,
    # )

    # Bring up the stack
    print("Starting Pluk services...")
    subprocess.run(
      ["docker", "compose", "-f", yml_path, "up", "-d"],
      check=True,
    )
    print("Pluk services are now running.")
  except subprocess.CalledProcessError as e:
    print("Error starting Pluk services:", e.stderr, file=sys.stderr)
    print('Please ensure Docker is installed, running, and accessible from your terminal. Try running "pluk start" again, and check for any error messages above.')
    return

def end_pluk_services(home, yml_path):
    """
    Stop the Docker Compose stack. Does not remove containers.

    This command is used to stop the Pluk services without removing them.
    It can be useful for maintenance or updates.
    """
    try:
      print(f"Stopping Pluk services...")
      subprocess.run(["docker", "compose", "-f", yml_path, "stop"], check=True)
      print("Pluk services stopped.")
    except subprocess.CalledProcessError as e:
      print("Error stopping Pluk services:", e.stderr, file=sys.stderr)
      print('Please ensure Docker is installed, running, and accessible from your terminal. Try running "pluk start" again, and check for any error messages above.')
      return


def main():
  """
  Entry point for pluk shim.

  This function only handles the start command and forwards other commands
  to the plukd CLI running inside the Docker container.

  It ensures that the Pluk services are running before executing any commands.
  """

  home = os.path.expanduser("~/.pluk")
  yml_path = os.path.join(home, "docker-compose.yml")
  run_check = ensure_running(home, yml_path)

  is_running = run_check["running"]
  found_services = run_check["found"]
  required_services = run_check["required"]
  services_are_synced = found_services == required_services

  # Handle the start command separately
  if len(sys.argv) > 1 and sys.argv[1] == "start":
    if is_running and services_are_synced:
      print("Pluk services are already running.")
      return

    start_pluk_services(home, yml_path)
    return

  # Handle the cleanup command
  if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
    if not found_services:
      print("Pluk services are not running. Nothing to clean up.")
      return
    end_pluk_services(home, yml_path)
    return

  # Handle the status command
  if len(sys.argv) > 1 and sys.argv[1] == "status":
    if is_running:
      if services_are_synced:
        print("Pluk services are running.")
      else:
        print("Pluk services are running, but found services do not match required services.")
        print('   Run "pluk start" to sync services.')
    else:
      print("Pluk services are not running.")
    return

  # Ensure the Pluk services are running
  if not is_running:
    print("Pluk services are not running. Please start them with:")
    print('   "pluk start"')
    return

  # === Forward commands to plukd (container) CLI ===

  cmd = [
    "docker", "compose", "-f", yml_path, "exec", "cli", "plukd"
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

  except subprocess.CalledProcessError as e:
    print(f"Error executing command: {e}", file=sys.stderr)
    return False

if __name__ == "__main__":
  main()
