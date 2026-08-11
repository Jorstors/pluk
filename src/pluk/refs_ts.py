# refs_ts.py
"""
tree-sitter parsing for both halves of the index: definitions (what `search`
and `define` return) and references (what `impact` walks).

One parser feeds both, so the supported-language list below is the whole story
-- a language Pluk cannot resolve references for is not indexed at all.
"""

import os
import subprocess

import tree_sitter as ts
from tree_sitter_language_pack import get_language, get_parser  # type: ignore

# The languages Pluk supports, display name -> tree-sitter key.
LANGUAGES = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Go": "go",
    "Java": "java",
    "C": "c",
    "C++": "cpp",
}

LANGUAGE_BY_KEY = {key: name for name, key in LANGUAGES.items()}

# File extension -> tree-sitter key. Replaces ctags' language detection.
EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
}

# Directories never worth indexing.
SKIP_DIRS = {".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__"}

QUERIES = {
    "python": """
    (call function: (identifier) @id)
    (call function: (attribute attribute: (identifier) @id))
  """,
    "javascript": """
    (call_expression function: (identifier) @id)
    (call_expression function: (member_expression property: (property_identifier) @id))
  """,
    "typescript": """
    (call_expression function: (identifier) @id)
    (call_expression function: (member_expression property: (property_identifier) @id))
  """,
    "go": """(call_expression function: (identifier) @id)""",
    "java": """(method_invocation name: (identifier) @id)""",
    "c": """(call_expression function: (identifier) @id)""",
    "cpp": """(call_expression function: (identifier) @id)""",
}

DEFINITION_QUERIES = {
    "python": """
    (function_definition) @def
    (class_definition) @def
  """,
    "javascript": """
    (function_declaration) @def
    (class_declaration) @def
    (method_definition) @def
  """,
    "typescript": """
    (function_declaration) @def
    (class_declaration) @def
    (method_definition) @def
    (interface_declaration) @def
    (type_alias_declaration) @def
  """,
    "go": """
    (function_declaration) @def
    (method_declaration) @def
  """,
    "java": """
    (class_declaration) @def
    (interface_declaration) @def
    (method_declaration) @def
    (constructor_declaration) @def
  """,
    "c": """
    (function_definition) @def
    (struct_specifier) @def
  """,
    "cpp": """
    (function_definition) @def
    (class_specifier) @def
    (struct_specifier) @def
  """,
}

# tree-sitter node type -> the `kind` column, so output stays stable across languages.
KINDS = {
    "function_definition": "function",
    "function_declaration": "function",
    "method_definition": "method",
    "method_declaration": "method",
    "constructor_declaration": "constructor",
    "class_definition": "class",
    "class_declaration": "class",
    "class_specifier": "class",
    "struct_specifier": "struct",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
}

# Node types that hold a definition's parameter list, for the `signature` column.
PARAM_TYPES = {
    "parameters",
    "formal_parameters",
    "parameter_list",
    "function_declarator",
}

CONTAINERS = {
    "python": {"function_definition", "class_definition"},
    "javascript": {"function_declaration", "method_definition", "class_declaration"},
    "typescript": {
        "function_declaration",
        "method_signature",
        "method_definition",
        "class_declaration",
    },
    "go": {"function_declaration", "method_declaration"},
    "java": {"method_declaration", "class_declaration"},
    "c": {"function_definition"},
    "cpp": {"function_definition"},
}


def language_for_path(path):
    """tree-sitter key for a file path, or None if Pluk does not support it."""
    return EXTENSIONS.get(os.path.splitext(path)[1].lower())


# Preliminary search for files containing the symbol
def git_grep_files(repo, commit, name):
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "grep", "-lIw", "--", name, commit], text=True
        )
    except subprocess.CalledProcessError:
        return []
    return [ln.split(":", 1)[-1] for ln in out.splitlines()]


# List every file tracked at a commit
def git_list_files(repo, commit):
    out = subprocess.check_output(
        ["git", "-C", repo, "ls-tree", "-r", "--name-only", commit], text=True
    )
    return out.splitlines()


# Show the contents of a file at a specific commit in bytes
def extract_file_from_commit(repo, commit, path):
    return subprocess.check_output(["git", "-C", repo, "show", f"{commit}:{path}"])


# Find the nearest container (function/class) for a given node
def locate_parent_container(lang_key, node):
    containers = CONTAINERS[lang_key]
    cur = node
    while cur:
        if cur.type in containers:
            return cur
        cur = cur.parent
    return None


def node_text(src, node):
    if node is None:
        return None
    return src[node.start_byte : node.end_byte].decode("utf-8", "replace")


def definition_name_node(node):
    """
    The identifier naming a definition.

    Most grammars expose it as a `name` field. C and C++ bury it inside nested
    declarators instead, so walk down until an identifier turns up.
    """
    named = node.child_by_field_name("name")
    if named is not None:
        return named

    cur = node.child_by_field_name("declarator")
    while cur is not None:
        if cur.type in ("identifier", "field_identifier", "type_identifier"):
            return cur
        nxt = cur.child_by_field_name("declarator")
        if nxt is None:
            for child in cur.named_children:
                if child.type in ("identifier", "field_identifier"):
                    return child
            return None
        cur = nxt
    return None


def definition_params_node(node):
    """The parameter list of a definition, searching through C-style declarators."""
    for field in ("parameters", "parameter_list"):
        found = node.child_by_field_name(field)
        if found is not None:
            return found

    cur = node.child_by_field_name("declarator")
    while cur is not None:
        found = cur.child_by_field_name("parameters")
        if found is not None:
            return found
        if cur.type in PARAM_TYPES:
            return cur
        cur = cur.child_by_field_name("declarator")
    return None


LANG = {}
PARSER = {}
QUERY = {}
DEF_QUERY = {}


# Cache builds for reuse
def ensure_lang_ready(lang_key):
    if lang_key in LANG:
        return
    lang = get_language(lang_key)
    parser = get_parser(lang_key)

    LANG[lang_key] = lang
    PARSER[lang_key] = parser
    QUERY[lang_key] = ts.Query(lang, QUERIES[lang_key])
    DEF_QUERY[lang_key] = ts.Query(lang, DEFINITION_QUERIES[lang_key])


def find_defs(repo, commit, lang_key, files):
    """
    Extract symbol definitions from `files` at `commit`.

    Rows match the `symbols` table columns. `scope`/`scope_kind` name the
    enclosing definition, so a method's scope is its class and a top-level
    function's scope is None.
    """
    ensure_lang_ready(lang_key)
    parser = PARSER[lang_key]
    query = DEF_QUERY[lang_key]
    language = LANGUAGE_BY_KEY[lang_key]

    definitions = []
    for path in files:
        try:
            src = extract_file_from_commit(repo, commit, path)
        except subprocess.CalledProcessError:
            continue

        tree = parser.parse(src)
        cursor = ts.QueryCursor(query)
        for node in cursor.captures(tree.root_node).get("def", []):
            name_node = definition_name_node(node)
            if name_node is None:
                continue

            container = locate_parent_container(lang_key, node.parent)

            definitions.append(
                {
                    "file": path,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "name": node_text(src, name_node),
                    "kind": KINDS.get(node.type, node.type),
                    "language": language,
                    "signature": node_text(src, definition_params_node(node)),
                    "scope": node_text(src, definition_name_node(container))
                    if container
                    else None,
                    "scope_kind": KINDS.get(container.type, container.type)
                    if container
                    else None,
                }
            )

    return definitions


# Find references to a symbol in a set of files
def find_refs(repo, commit, name, lang_key, files):
    ensure_lang_ready(lang_key)
    parser = PARSER[lang_key]
    query = QUERY[lang_key]

    references_list = []
    for path in files:
        try:
            src = extract_file_from_commit(repo, commit, path)
        except subprocess.CalledProcessError:
            continue

        tree = parser.parse(src)
        cursor = ts.QueryCursor(query)
        capdict = cursor.captures(tree.root_node)
        for node in capdict.get("id", []):
            captured = node_text(src, node)
            if captured != name:
                continue

            cont_node = locate_parent_container(lang_key, node)
            name_node = definition_name_node(cont_node) if cont_node else None

            references_list.append(
                {
                    "file": path,
                    "line": node.start_point[0] + 1,
                    "container": node_text(src, name_node) if name_node else None,
                    "container_kind": cont_node.type if cont_node else None,
                }
            )

    return references_list
