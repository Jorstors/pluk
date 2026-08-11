# Pluk

Git-aware symbol lookup & impact analysis engine

---

## What is a "symbol"?

In Pluk, a **symbol** is any named entity in your codebase that can be referenced, defined, or impacted by changes. This includes functions, classes, methods, interfaces, and structs. Pluk tracks symbols across commits to enable queries like "go to definition", "find all references", and "impact analysis".

Pluk gives developers “go-to-definition”, “find-all-references”, and “blast-radius” impact queries over a Git repository. Everything runs locally in a single process. There are no containers, no daemons, no database server, and **nothing ever leaves your machine**.

---

## Features
-  **Search**: classes, functions, and other symbols in your repo
-  **Define**: list metadata about a specific symbol
-  **Impact**: find references and usage contexts of a symbol
-  **Diff**: compare definitions and references between commits
-  **Indexing**: via tree-sitter, one commit at a time
-  **Local**: one SQLite file, no services to run
-  **Scriptable**: `--json` on every command
-  **Language support:** Python, JavaScript (incl. JSX), TypeScript (incl. TSX), Go, Java, C, C++

---

## Prerequisites
- Python 3.11+
- Git
- Supported OS: Linux, macOS, Windows

---
## Installation
```bash
pip install pluk
```
---

## Usage

```bash
pluk init [path|url]              # index a repository (defaults to .)
pluk search MyClass               # symbol lookup; fuzzy, branch-wide
pluk define my_function           # show symbol definition
pluk impact computeFoo            # list symbol references with context
pluk diff symbol <ref1> <ref2>    # compare symbol changes between commits/aliases (e.g. head, main, or SHAs)
```

There are no services to start; `pluk init` is the first and only setup step.

Initialize a repository:

```powershell
> pluk init .
Indexing https://github.com/jorstors/pluk-diff-sample at dd36847d0f55
Parsing 3 files across 1 languages
  python: 12 symbols from 3 files

[+] 12 symbols indexed.
Current repository:
    URL: https://github.com/jorstors/pluk-diff-sample
    Commit SHA: dd36847d0f55c5af6e70ee920837c782d09edbc2

```

Search for a symbol:

```powershell
> pluk search find
Searching for symbol: find @ https://github.com/jorstors/pluk-diff-sample:dd36847d0f55

Found symbol: find_refs
 Located at: src/app.py:1
```

Define a symbol:

```powershell
> pluk define find_refs
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
 From commit: caa599294066
 To commit: dd36847d0f55

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

`pluk diff` indexes both commits on demand, so any point in history can be compared without indexing it up front.

Every command accepts `--json` for machine-readable output:

```bash
pluk search find --json | jq '.symbols[].location'
```

---

## How it works

```mermaid
flowchart LR
    CLI["pluk"] --> REPO[("your git repo")]
    REPO --> DB[("~/.pluk/pluk.db")]
```

- **`pluk init`** reads the repo where it sits; nothing is copied. Passing a URL instead mirrors it under `~/.pluk/repos` first.
- **tree-sitter** extracts both definitions and references from the files tracked at a commit.
- **SQLite** stores the symbol graph in a single file.
- **`search`** and **`define`** are pure SQL, so they return immediately. **`impact`** additionally re-parses the files that mention the symbol, since call sites are found in the AST rather than stored.
- **`diff`** indexes both commits, then compares their definitions and reference sets.

Everything lives under `~/.pluk` (override with `PLUK_HOME`):

- `pluk.db`: the entire index. Delete it to start over.
- `repos/`: mirrors of repositories indexed by URL only.

Parsing is syntactic, so references resolve by name; dynamic dispatch and reflection will not be found. Files outside the supported languages are skipped.

---

## Development

**Project layout** (`src/pluk`):

- `cli.py`: argument parsing and output
- `query.py`: read queries (`define`, `search`, `impact`, `diff`)
- `indexer.py`: git plumbing and index writes
- `refs_ts.py`: tree-sitter definition and reference extraction
- `db.py`: SQLite connection and schema
- `SQL_UTIL/operations.py`: schema and queries

---

## Testing

```bash
pip install -e ".[test]"
pytest
```
---

## License

MIT License
