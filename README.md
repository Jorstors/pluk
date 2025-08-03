# PLUK

**Pluk** is a minimal, backend-first symbol lookup and cross-reference engine CLI.
Index git-tracked code, search symbols, see definitions/usages, and compute impact/blast-radius impact chains.

## Quick install

### Unix / Linux / macOS (or Git Bash on Windows)

```bash
curl -sSL https://cdn.jsdelivr.net/gh/Jorstors/pluk@v0.1.1/pluk.sh | bash
```

### Windows (PowerShell)

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression (Invoke-WebRequest https://cdn.jsdelivr.net/gh/Jorstors/pluk@v0.1.1/pluk.ps1).Content)"
```

## Verify installer (optional)

```bash
curl -sSL https://github.com/Jorstors/pluk/releases/download/v0.1.1/pluk.sh.sha256 -o pluk.sh.sha256
curl -sSL https://cdn.jsdelivr.net/gh/Jorstors/pluk@v0.1.1/pluk.sh -o pluk.sh
sha256sum -c pluk.sh.sha256
```

## Basic usage

After the bootstrapper has run (it brings up the service via Docker Compose):

```bash
pluk start                  # run API + worker
pluk init ./path/to/repo    # index a git repository
pluk search <symbol>        # fuzzy lookup
pluk define <symbol>        # show definition + references
pluk impact <symbol>        # show downstream impact
pluk diff --from A --to B   # compare commits
pluk status                 # health & repo status
pluk doctor                 # diagnostics
```

## Development

Editable/development install and test:

```bash
python -m pip install --upgrade build
python -m build
pip install -e .
pytest
```

## Releases

Tagging a semantic version like `v0.1.1` triggers the release workflow, publishing `pluk.sh`, `pluk.ps1`, and their checksums. Users can install a specific version via the jsDelivr URLs above.

## Requirements

- Docker with `docker compose` (v2+)
- Git (for target repositories)
- Python (for development/testing, optional for users using embedded CLI)

## License

## MIT © Justus Jones
