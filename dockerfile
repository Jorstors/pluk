FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git universal-ctags build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --upgrade pip setuptools wheel

COPY src/ ./src
RUN pip install .[api,worker,db,refs]
