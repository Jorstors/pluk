# Use a slim Python base
FROM python:3.13-slim

# Create app dir
WORKDIR /app

# Install any OS-level deps (e.g. for Postgres/Redis clients or builds)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

# Copy dependency spec and install
COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --no-dev

# Copy your application code
# - the src/ directory containing pluk package
# - CLI stubs and any scripts (e.g. pluk.sh, pluk.ps1) if you want them baked in
COPY src/ ./src/
COPY pluk.sh pluk.ps1 ./

# Tell Docker which port the FastAPI server listens on
EXPOSE 8000

# Default entrypoint: launch the Pluk server + worker
ENTRYPOINT ["pluk"]
CMD ["start"]
