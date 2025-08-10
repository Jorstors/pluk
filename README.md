# Pluk

Git-commit–aware symbol lookup & impact analysis engine

Pluk gives developers “go-to-definition”, “find-all-references”, and “blast-radius” impact queries across one or more Git repositories. Heavy lifting (indexing, querying, storage) runs in isolated Docker containers; a lightweight host CLI bootstraps and delegates commands.

---

## Key Features

- **symbol search** (`pluk search`) and definition lookup (`pluk define`)
- **Impact analysis** (`pluk impact`) to trace downstream dependents via recursive CTEs & caching
- **Commit-aware indexing**: evolves symbol graph across Git history (`pluk diff`)
- **Zero-friction install**: `pip install pluk` + Docker & Compose
- **Containerized backend**: PostgreSQL for the graph, Redis for cache
- **Single Python codebase**: host shim (`pluk.bootstrap`) + container CLI (`pluk.cli`)

---

## Quickstart

1. **Install**

   ```bash
   pip install pluk
   ```

   Ensure Docker & Docker Compose are installed and your user can run `docker`.

2. **Bootstrap & index**

   ```bash
   pluk init /path/to/your/repo
   ```

   Sets up containers and indexes the repo.

3. **Run queries**

   ```bash
   pluk search MyClass         # search definitions & refs
   pluk define my_function      # show definition location
   pluk impact computeFoo        # trace downstream dependents
   pluk diff abc123 def456        # symbol changes between commits
   ```

4. **Manage services**
   ```bash
   pluk start    # launch FastAPI server + worker
   pluk cleanup   # teardown Docker Compose stack
   ```

All commands run on the host; Pluk manages Docker Compose under `~/.pluk/docker-compose.yml` by default.

---

## Data Flow

Pluk’s host shim (`pluk`) writes a Compose file and delegates commands into the container CLI (`plukd`). Inside the container, `plukd` interacts with Postgres and Redis; results stream back to your terminal.

[![](https://mermaid.ink/img/pako:eNp9Uu9L40AQ_VeGAcXjYonNtk2CCJp-uIJ3FPGTRmTNbpOlzW7YbNC7tv_7zaY_oAp-yryZeW_mzWaNhRESU1yszHtRcevg_iHXAG33VlreVPDLtM4noI-y-9lzjs2qW8JFRRjaStU_cnzxLVKLXJ-Qp6ZYSvv6R7p3Y5c7GaGsLJwyGh7vdpk5yWVGO660tHt5ARc0C37C7Xx20KdOGlla2VLTIYTp3bH8IIXytf4LGS8q-Xm1s7PeByjtpOX9Hq3P783B9eXlDWzAh4Wpa65FC-dgOtd0bnO66VFw5rU0XxFjX_oif0I8DHnM5pCOWDTcHI193zuOJslm5zLXGGBplcDU2U4GWEtbcw9x7UVydJWsyX5KoeB0fMz1ljgN10_G1AeaNV1ZYbrgq5ZQ1wju5FRxer76mLV0PWkz02mHacJGvQima_zwcBAlwzEbJuEwikZRFOBfTAkNJqNJOGHhOGZJzLYB_uunhoM4TMIrqrAwYTGLxwGSH2fs792PSDdcqBK3_wFCz9YC?type=png)](https://mermaid.live/edit#pako:eNp9Uu9L40AQ_VeGAcXjYonNtk2CCJp-uIJ3FPGTRmTNbpOlzW7YbNC7tv_7zaY_oAp-yryZeW_mzWaNhRESU1yszHtRcevg_iHXAG33VlreVPDLtM4noI-y-9lzjs2qW8JFRRjaStU_cnzxLVKLXJ-Qp6ZYSvv6R7p3Y5c7GaGsLJwyGh7vdpk5yWVGO660tHt5ARc0C37C7Xx20KdOGlla2VLTIYTp3bH8IIXytf4LGS8q-Xm1s7PeByjtpOX9Hq3P783B9eXlDWzAh4Wpa65FC-dgOtd0bnO66VFw5rU0XxFjX_oif0I8DHnM5pCOWDTcHI193zuOJslm5zLXGGBplcDU2U4GWEtbcw9x7UVydJWsyX5KoeB0fMz1ljgN10_G1AeaNV1ZYbrgq5ZQ1wju5FRxer76mLV0PWkz02mHacJGvQima_zwcBAlwzEbJuEwikZRFOBfTAkNJqNJOGHhOGZJzLYB_uunhoM4TMIrqrAwYTGLxwGSH2fs792PSDdcqBK3_wFCz9YC)

---

## Architecture

```text
[Host CLI: pluk] ── docker-compose ──▶ [Container: plukd]
                                    │
                                    ├─▶ Postgres (symbol graph)
                                    └─▶ Redis (cache)
```

- **`pluk` (host shim)**

  - Writes and manages `docker-compose.yml` under `~/.pluk/`
  - Forwards user commands into the container via `docker compose exec`

- **`plukd` (container CLI)**

  - Implements `init`, `search`, `define`, `impact`, `diff`, `start`, `cleanup`
  - Parses repos, builds AST index, executes queries with SQL & Python

- **Postgres** stores commits, symbol definitions, and reference links
- **Redis** caches expensive recursive queries for sub-second responses

---

## Development

```bash
# Clone & install in editable mode
git clone https://github.com/Jorstors/pluk.git
cd pluk
pip install -e .
```

- **Project layout** (`src/pluk`):

  - `bootstrap.py` — host shim entrypoint (`pluk`)
  - `cli.py` — container CLI (`plukd`)

- **Entry points** in `pyproject.toml`:
  ```toml
  [project.scripts]
  pluk  = "pluk.bootstrap:main"
  plukd = "pluk.cli:main"
  ```

---

## Testing

- **Unit tests** for argument parsing and shim logic (`pytest`)
- **Integration tests** invoking `pluk init` on a sample repo

```bash
pytest tests/
```

> **Note:** Docker daemon must be running locally.

---

## 🔖 Versioning

We use [bumpver](https://github.com/philipn/bumpver) for semantic versioning:

```bash
bumpver patch   # 0.1.0 → 0.1.1
bumpver minor    # 0.1.1 → 0.2.0
bumpver major     # 0.2.0 → 1.0.0
```

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
