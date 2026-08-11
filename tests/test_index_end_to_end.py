# tests/test_index_end_to_end.py
"""Index a real git repo and query it back. Covers parsing, storage and lookup."""

import subprocess

import pytest

SOURCE = {
    "svc.py": "class Widget:\n    def render(self, x):\n        return helper(x)\n\n\ndef helper(x):\n    return x\n",
    "lib.go": "package main\n\nfunc double(n int) int { return n * 2 }\n\nfunc Run(n int) int { return double(n) }\n",
}


@pytest.fixture
def indexed(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for name, body in SOURCE.items():
        (repo / name).write_text(body)

    run = lambda *args: subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )
    run("init")
    run("add", "-A")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init")

    monkeypatch.setenv("PLUK_HOME", str(tmp_path / "home"))
    from pluk.indexer import index

    return index(str(repo))


def test_index_reports_symbols(indexed):
    assert indexed["status"] == "indexed"
    assert indexed["symbols"] > 0


def test_define_finds_method_with_its_class_as_scope(indexed):
    from pluk import query

    symbol = query.define("render")
    assert symbol["file"] == "svc.py"
    assert symbol["language"] == "Python"
    assert symbol["scope"] == "Widget"
    assert symbol["signature"] == "(self, x)"


def test_search_matches_on_substring(indexed):
    from pluk import query

    names = {s["name"] for s in query.search("elp")["symbols"]}
    assert "helper" in names


def test_impact_names_the_calling_function(indexed):
    from pluk import query

    refs = query.impact("helper")
    assert [(r["file"], r["container"]) for r in refs] == [("svc.py", "render")]


def test_impact_works_for_a_second_language(indexed):
    from pluk import query

    refs = query.impact("double")
    assert [(r["file"], r["container"]) for r in refs] == [("lib.go", "Run")]


def test_unknown_symbol_raises(indexed):
    from pluk import query
    from pluk.query import PlukError

    with pytest.raises(PlukError):
        query.define("no_such_symbol")
