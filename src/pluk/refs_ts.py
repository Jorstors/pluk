# refs_ts.py
import subprocess
import tree_sitter as ts
from tree_sitter_language_pack import get_language, get_parser  # type: ignore

CTAGS_TO_TREE_SITTER_MAP = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Go": "go",
    "Java": "java",
    "C": "c",
    "C++": "cpp",
}

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


# Preliminary search for files containing the symbol
def git_grep_files(mirror, commit, name):
    try:
        out = subprocess.check_output(
            ["git", "-C", mirror, "grep", "-lIw", "--", name, commit], text=True
        )
    except subprocess.CalledProcessError:
        return []
    return [ln.split(":", 1)[-1] for ln in out.splitlines()]


# Show the contents of a file at a specific commit in bytes
def extract_file_from_commit(mirror, commit, path):
    print("[extract_file_from_commit] Extracting file from commit...")
    return subprocess.check_output(["git", "-C", mirror, "show", f"{commit}:{path}"])


# Find the nearest container (function/class) for a given node
def locate_parent_container(lang_key, node):
    CONTAINERS = {
        "python": {"function_definition", "class_definition"},
        "javascript": {"function_declaration", "method_definition"},
        "typescript": {"function_declaration", "method_signature", "method_definition"},
        "go": {"function_declaration", "method_declaration"},
        "java": {"method_declaration", "class_declaration"},
        "c": {"function_definition"},
        "cpp": {"function_definition"},
    }[lang_key]
    cur = node
    while cur:
        if cur.type in CONTAINERS:
            return cur
        cur = cur.parent
    return None


LANG = {}
PARSER = {}
QUERY = {}


# Cache builds for reuse
def ensure_lang_ready(lang_key):
    if lang_key in LANG:
        return
    lang = get_language(lang_key)
    parser = get_parser(lang_key)
    query = ts.Query(lang, QUERIES[lang_key])

    LANG[lang_key] = lang
    PARSER[lang_key] = parser
    QUERY[lang_key] = query


# Find references to a symbol in a set of files
def find_refs(mirror, commit, name, lang_key, files):
    ensure_lang_ready(lang_key)
    lang = LANG[lang_key]
    parser = PARSER[lang_key]
    query = QUERY[lang_key]

    references_list = []
    for path in files:
        try:
            src = extract_file_from_commit(mirror, commit, path)
        except subprocess.CalledProcessError:
            continue

        tree = parser.parse(src)
        cursor = ts.QueryCursor(query)
        capdict = cursor.captures(tree.root_node)
        for node in capdict.get("id", []):
            print(f"Found node: {node.type} at {node.start_point} to {node.end_point}")
            s, e = node.start_byte, node.end_byte
            captured = src[s:e].decode("utf-8", "replace")

            if captured != name:
                continue

            line = node.start_point[0] + 1

            cont_node = locate_parent_container(lang_key, node)
            container_name = None

            name_node = cont_node.child_by_field_name("name") if cont_node else None
            if name_node:
                container_name = src[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8", "replace"
                )
            print(
                f"Located container: {container_name} of type {cont_node.type if cont_node else None}"
            )

            reference = {
                "file": path,
                "line": line,
                "container": container_name,
                "container_kind": cont_node.type if cont_node else None,
            }
            print(f"[find_refs] Found reference: {reference}")

            references_list.append(reference)

    return references_list
