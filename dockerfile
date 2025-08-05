FROM python:3.13-slim

# 1. Set working directory
WORKDIR /app

# 2. Install only git (required for gitpython) and clean up apt cache
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

# 3. Copy dependency manifests and install dependencies (excluding dev dependencies)
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-root --without dev

# 4. Copy application code into the image
COPY src/ ./src

# 5. Expose the API port
EXPOSE 8000

# 6. Set the default entrypoint and command to run `pluk start`
ENTRYPOINT ["pluk"]
CMD ["start"]
