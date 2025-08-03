# pluk

**pluk** is a minimal symbol lookup / search engine command-line interface.

## Installation

```bash
pip install pluk
```

*(To reserve the name on PyPI, publish a minimal placeholder package with this structure.)*

## Usage

After installation, run:

```bash
pluk [ARGS]
```

Currently this is a stub; extend it with search/index features. Example output:

```bash
$ pluk
pluk: symbol search engine CLI
```

## Development

Set up editable install for development:

```bash
python -m pip install --upgrade build
python -m build
pip install -e .
```

Run tests:

```bash
pytest
```

## Publishing

A GitHub Actions workflow is included to automate publishing on tag push. You need to configure the secret `PYPI_API_TOKEN` in your repository settings.

## License

MIT © Justus Jones
