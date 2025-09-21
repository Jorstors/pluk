# Pluk

Git-commit–aware symbol lookup & impact analysis engine

---

## What is a "symbol"?

In Pluk, a **symbol** is any named entity in your codebase that can be referenced, defined, or impacted by changes. This includes functions, classes, methods, variables, and other identifiers that appear in your source code. Pluk tracks symbols across commits and repositories to enable powerful queries like "go to definition", "find all references", and "impact analysis".

Pluk gives developers “go-to-definition”, “find-all-references”, and “blast-radius” impact queries across one or more Git repositories. Heavy lifting (indexing, querying, storage) runs in Docker containers; a lightweight host shim (`pluk`) boots the stack and delegates commands into a thin CLI container (`plukd`) that talks to an internal API.

---

## Features
-  **Search**: classes, functions, and other symbols in your repo  
-  **Define**: list metadata about a specific symbol 
-  **Impact**: find references and usage contexts of a symbol  
-  **Diff**: compare definitions and references between commits  
-  **Indexing**: via universal-ctags and tree-sitter (one branch at a time)
-  **Containerized**: runs with Docker Compose, no host setup needed  
-  **Language support:** Python, JavaScript, TypeScript, Go, Java, C, C++

---

## Prerequisites
- Docker and Docker Compose
- Git repositories must be **public or cloneable** from inside the container  
- Supported OS: Linux, macOS, Windows (with Docker Desktop)

---
## Installation
```bash
pip install pluk
```
---

## Usage

```bash
pluk start                        # launch services
pluk status                       # check if services are running
pluk cleanup                      # stop services

pluk init /path/to/repo           # queue full index of a repository
pluk search MyClass               # symbol lookup; symbol matches branch-wide
pluk define my_function           # show symbol definition
pluk impact computeFoo            # list symbol references with context
pluk diff symbol SHA-1 SHA-2      # show symbol changes between commit SHAs SHA-1 → SHA-2
```

Start the Pluk services:

```powershell
> pluk start
Pulling latest Docker images...
Starting Pluk services...
[+] Running 5/5
 ✔ Container pluk-redis-1     Healthy                                                                                                                                                                                                                                           7.5s 
 ✔ Container pluk-postgres-1  Healthy                                                                                                                                                                                                                                           7.5s 
 ✔ Container pluk-api-1       Started                                                                                                                                                                                                                                           7.0s 
 ✔ Container pluk-worker-1    Started                                                                                                                                                                                                                                           8.0s 
 ✔ Container pluk-cli-1       Started                                                                                                                                                                                                                                           7.4s 
Pluk services are now running.

```

Initialize a repository:

```powershell
> pluk init .
Initializing repository at .
[+] Repository initialized successfully.
Current repository:
    URL: https://github.com/jorstors/pluk-diff-sample
    Commit SHA: dd36847d0f55c5af6e70ee920837c782d09edbc2

```

Search for a symbol:

```powershell
> pluk search find
Searching for symbol: find @ https://github.com/jorstors/pluk-diff-sample:dd36847d0f55c5af6e70ee920837c782d09edbc2

Found symbol: find_refs
 Located at: src/app.py:1
```

Define a symbol:

```powershell
> pluk define find_refs
Defining symbol: find_refs

Symbol: find_refs
 Location: src/app.py:1-3
 Kind: function
 Language: Python
 Signature: (x)
 Scope: global (unknown)
```

Check symbol impact:

```powershell
> pluk impact find_refs
Analyzing impact of symbol: find_refs

References found:
 other (function_definition) in src/app.py:13
```

Diff a symbol across commits:

```powershell
> pluk diff find_refs caa599294066de31f01305a781ca8ff0bbe06aba dd36847d0f55c5af6e70ee920837c782d09edbc2
Showing differences for symbol: find_refs
 From commit: caa599294066de31f01305a781ca8ff0bbe06aba
 To commit: dd36847d0f55c5af6e70ee920837c782d09edbc2
Differences found:
 Definition:
 * file: No change
 * line: No change
 * end_line:
     - From: 2
     - To:   3
 * name: No change
 * kind: No change
 * language: No change
 * signature: No change
 * scope: No change
 * scope_kind: No change

 New references:
 * other (function_definition) in src/app.py:13

 Removed references:
 * use (function_definition) in src/app.py:6
```

If you want a full teardown (remove containers/network), use:

```bash
docker compose -f ~/.pluk/docker-compose.yml down -v
```

---

## Data Flow

[![](https://mermaid.ink/img/pako:eNp9UtGO2jAQ_BVrHyqQAiKBhCSVKrWg6irRit6dVKmkqkyyl0Qkdmo7BUr4967D0eNe-rT27OzsztonSGWGEMNTJfdpwZVhq_tEMKbbba54U7A7qY0FGHsoynqTQFO1OzYoCGaakGECP2weRZaIV5VLme5Q_fyCZi_V7qKxWH0iibQqmUb1u0wxEQMrmL1leMCUGa5yNFdNxt6vLZ83t_yPXBvCX0jfSB4V8fb94Ya6wArV8YV5j1mpN4M-JGKrpKW_YSlPCxw-c5YfNoM1ucsVPnxdJUIf662sWO9p-Nqq3Qgbjd51_eylMLKzDm2KQp-5e3xcd9aGBSlc6OJXiy2SW73THXse52qkp6RS6Lb-L2WvSoPUNcNDR1PfNlDIM0Y9VIna5sCBXJUZxEa16ECNqub2CidblYApsMYEYjpmnN4KEnGmmoaL71LW1zIl27yA-IlXmm5tk3GDy5LTZup_qKLloFrIVhiIg8j3ehWIT3CAeOSF_tibzqahO43mURDNZw4cIXa9YBzOCJyEfjQJvDA4O_Cn7-yOPd-fBG7ou-48CN25A7QKI9Xny7_tv-_5L0GP5fk?type=png)](https://mermaid.live/edit#pako:eNp9UtGO2jAQ_BVrHyqQAiKBhCSVKrWg6irRit6dVKmkqkyyl0Qkdmo7BUr4967D0eNe-rT27OzsztonSGWGEMNTJfdpwZVhq_tEMKbbba54U7A7qY0FGHsoynqTQFO1OzYoCGaakGECP2weRZaIV5VLme5Q_fyCZi_V7qKxWH0iibQqmUb1u0wxEQMrmL1leMCUGa5yNFdNxt6vLZ83t_yPXBvCX0jfSB4V8fb94Ya6wArV8YV5j1mpN4M-JGKrpKW_YSlPCxw-c5YfNoM1ucsVPnxdJUIf662sWO9p-Nqq3Qgbjd51_eylMLKzDm2KQp-5e3xcd9aGBSlc6OJXiy2SW73THXse52qkp6RS6Lb-L2WvSoPUNcNDR1PfNlDIM0Y9VIna5sCBXJUZxEa16ECNqub2CidblYApsMYEYjpmnN4KEnGmmoaL71LW1zIl27yA-IlXmm5tk3GDy5LTZup_qKLloFrIVhiIg8j3ehWIT3CAeOSF_tibzqahO43mURDNZw4cIXa9YBzOCJyEfjQJvDA4O_Cn7-yOPd-fBG7ou-48CN25A7QKI9Xny7_tv-_5L0GP5fk)

**How it works**

- **Host shim (`pluk`)** writes the Compose file, **pulls images**, and runs `docker compose up`.
- **CLI container (`plukd`)** is the exec target; it calls the API at `http://api:8000`.
- **API (FastAPI)** serves read endpoints (`/search`, `/define`, `/impact`, `/diff`) and enqueues write jobs (`/reindex`) to **Redis**.
- **Worker (Celery)** consumes jobs from **Redis**, clones/pulls repos into a volume (`/var/pluk/repos`), parses it, and writes to **Postgres**.

---

## Testing

```bash
pytest
```
---

## License

MIT License
