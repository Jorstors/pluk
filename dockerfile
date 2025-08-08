
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install git (required for gitpython) and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better cache usage
COPY pyproject.toml README.md ./

# Install build dependencies
RUN pip install --upgrade pip setuptools wheel

# Copy source code
COPY src/ ./src

# Install the application package binaries
RUN pip install .

# Expose the API port
EXPOSE 8000

# Set the default entrypoint and command to run `plukd start`
ENTRYPOINT ["plukd"]
CMD ["start"]
