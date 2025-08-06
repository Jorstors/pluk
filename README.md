

# Pluk

Pluk is a git-commit–aware, backend-first symbol lookup and cross-reference engine with impact analysis. It helps developers explore and refactor large codebases by indexing symbol definitions and usages across one or more Git repositories.

Designed for clarity, speed, and developer ergonomics, Pluk runs as a simple CLI tool on the host, while all heavy computation (indexing, querying, storage) runs in isolated Docker containers.


## Features

- Symbol search and definition lookup
- Git commit–aware cross-reference indexing
- Impact analysis of symbol usage across history
- Fully containerized backend (Postgres + Redis)
- Pip-installable host CLI
- Single unified Python codebase for host shim and CLI core


## Installation

```bash
pip install pluk
````

Ensure Docker and Docker Compose are installed and running on your machine.


## Usage

```bash
# Initialize and index a repository
pluk init ~/myrepo

# Search for a symbol
pluk search MyClass

# Show where a symbol is defined
pluk define my_function

# Show usage/impact of a symbol
pluk impact my_function

# Show changes to a symbol across commits
pluk diff abc123 def456 --symbol SomeClass
```

All commands are executed from the host. Pluk automatically starts the necessary backend services in Docker under the hood.

---
# Data Flow

[![](https://mermaid.ink/img/pako\:eNp9Uu9L40AQ_VeGAcXjYonNtk2CCJp-uIJ3FPGTRmTNbpOlzW7YbNC7tv_7zaY_oAp-yryZeW_mzWaNhRESU1yszHtRcevg_iHXAG33VlreVPDLtM4noI-y-9lzjs2qW8JFRRjaStU_cnzxLVKLXJ-Qp6ZYSvv6R7p3Y5c7GaGsLJwyGh7vdpk5yWVGO660tHt5ARc0C37C7Xx20KdOGlla2VLTIYTp3bH8IIXytf4LGS8q-Xm1s7PeByjtpOX9Hq3P783B9eXlDWzAh4Wpa65FC-dgOtd0bnO66VFw5rU0XxFjX_oif0I8DHnM5pCOWDTcHI193zuOJslm5zLXGGBplcDU2U4GWEtbcw9x7UVydJWsyX5KoeB0fMz1ljgN10_G1AeaNV1ZYbrgq5ZQ1wju5FRxer76mLV0PWkz02mHacJGvQima_zwcBAlwzEbJuEwikZRFOBfTAkNJqNJOGHhOGZJzLYB_uunhoM4TMIrqrAwYTGLxwGSH2fs792PSDdcqBK3_wFCz9YC?type=png)](https://mermaid.live/edit#pako:eNp9Uu9L40AQ_VeGAcXjYonNtk2CCJp-uIJ3FPGTRmTNbpOlzW7YbNC7tv_7zaY_oAp-yryZeW_mzWaNhRESU1yszHtRcevg_iHXAG33VlreVPDLtM4noI-y-9lzjs2qW8JFRRjaStU_cnzxLVKLXJ-Qp6ZYSvv6R7p3Y5c7GaGsLJwyGh7vdpk5yWVGO660tHt5ARc0C37C7Xx20KdOGlla2VLTIYTp3bH8IIXytf4LGS8q-Xm1s7PeByjtpOX9Hq3P783B9eXlDWzAh4Wpa65FC-dgOtd0bnO66VFw5rU0XxFjX_oif0I8DHnM5pCOWDTcHI193zuOJslm5zLXGGBplcDU2U4GWEtbcw9x7UVydJWsyX5KoeB0fMz1ljgN10_G1AeaNV1ZYbrgq5ZQ1wju5FRxer76mLV0PWkz02mHacJGvQima_zwcBAlwzEbJuEwikZRFOBfTAkNJqNJOGHhOGZJzLYB_uunhoM4TMIrqrAwYTGLxwGSH2fs792PSDdcqBK3_wFCz9YC)

Pluk uses the host shim (`pluk`) to forward commands into a running container where the core CLI (`plukd`) executes. The `plukd` CLI interacts with Postgres and Redis over Docker’s internal network. Output is streamed back to the host terminal.

---

# Architecture

* `pluk` (host shim): Ensures the container stack is up and forwards CLI calls via `docker compose exec`.
* `plukd` (real CLI): Executes commands inside the container using the indexed symbol graph.
* `Postgres`: Stores the symbol graph, commits, and metadata.
* `Redis`: Caches results of expensive queries like impact analysis.


## Development

Project structure:

```
src/pluk/
├── bootstrap.py     # Host shim
├── cli.py           # Container CLI logic
```

Entry points (in pyproject.toml):

```toml
[project.scripts]
pluk = "pluk.bootstrap:main"
plukd = "pluk.cli:main"
```

Build and run:

```bash
pip install -e .
pluk init .
```


## Tests

* Unit tests for CLI and shim logic
* Integration test: `pluk init` on toy repo
* Requires Docker daemon running locally




## License

MIT License

```
