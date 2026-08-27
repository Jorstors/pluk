# Pluk

Git-aware symbol lookup & impact analysis engine

---

## What is a "symbol"?

In Pluk, a **symbol** is any named entity in your codebase that can be referenced, defined, or impacted by changes. This includes functions, classes, methods, interfaces, and structs. Pluk tracks symbols across commits to enable queries like "go to definition", "find all references", and "impact analysis".

Pluk gives developers “go-to-definition”, “find-all-references”, and “blast-radius” impact queries over a Git repository. Everything runs locally in a single process. There are no containers, no daemons, no database server, and **nothing ever leaves your machine**.

---

## Features
-  **Search**: classes, functions, and other symbols in your repo
-  **Define**: metadata, source preview, docstring and callers for a symbol
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
> pluk init
Indexing https://github.com/jorstors/pluk at 8ba49f32f594
Parsing 15 files across 1 languages
  python: 67 symbols from 15 files

[+] 67 symbols indexed.
Current repository:
 URL:        https://github.com/jorstors/pluk
 Commit:     8ba49f32f59496d6419fdcafbf445e095be30c8d

```

Search for a symbol:

```powershell
> pluk search definition
Searching for definition  @ https://github.com/jorstors/pluk:8ba49f32f594

definition_name_node  src/pluk/refs_ts.py:201
definition_params_node  src/pluk/refs_ts.py:226

2 matches.
```

Define a symbol:

```powershell
> pluk define PlukError
PlukError
 Location:  src/pluk/query.py:29-34
 Kind:      class
 Language:  Python
 Scope:     global (unknown)
 Callers:   6 (2 files)
 Docstring: none
 Last change: 99b6f65 feat: Update code to use SQLite and run indexing through a single file rather than a docker volume

Source:
   29 | class PlukError(Exception):
   30 |     """Anything the user can act on. The CLI prints it and exits non-zero."""
   31 | 
   32 |     def __init__(self, message, hint=None):
   33 |         super().__init__(message)
   34 |         self.hint = hint
```

Check symbol impact:

```powershell
> pluk impact PlukError
Impact of PlukError

 resolve_commit (function_definition) in src/pluk/indexer.py:71
 resolve_target (function_definition) in src/pluk/indexer.py:101
 impact (function_definition) in src/pluk/query.py:108
 current_repo (function_definition) in src/pluk/query.py:41
 define (function_definition) in src/pluk/query.py:59
 impact (function_definition) in src/pluk/query.py:112

6 references.
```

Diff a symbol across commits:

```powershell
> pluk diff find_refs caa599294066de31f01305a781ca8ff0bbe06aba dd36847d0f55c5af6e70ee920837c782d09edbc2
Changes to find_refs
 caa599294066 -> dd36847d0f55

Definition
 file: unchanged
 line: unchanged
 end_line:
   - 2
   + 3
 name: unchanged
 kind: unchanged
 language: unchanged
 signature: unchanged
 scope: unchanged
 scope_kind: unchanged

New references
 + other (function_definition) in src/app.py:13

Removed references
 - use (function_definition) in src/app.py:6
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
- **`search`** is pure SQL and returns immediately. **`define`** also reads the file back from git history for a source preview and docstring, then reports the symbol's callers and last change. **`impact`** re-parses the files that mention the symbol, since call sites are found in the AST rather than stored.
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
