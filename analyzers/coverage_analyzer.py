import ast
import re

# Important design decision, not a shortcut: this tool reviews code that has
# not been vetted yet, so we never execute it to get real coverage.py numbers.
# Running an untrusted diff through a test runner is exactly the kind of thing
# that turns a code review tool into a remote code execution vector. Instead
# we approximate "is this change tested" with static heuristics: does a
# function/class get referenced by name somewhere that looks like a test.


def _extract_definitions(content: str):
    names = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    return names


def analyze(files):
    """
    files: list of {filename, content, is_full_reconstruction}
    Returns which defined functions/classes have no apparent test reference
    anywhere in the submitted diff.
    """
    test_files = [f for f in files if "test" in f["filename"].lower()]
    non_test_files = [f for f in files if f not in test_files]

    test_blob = "\n".join(f["content"] for f in test_files)

    defined = []
    for f in non_test_files:
        if f["filename"].endswith(".py"):
            for name in _extract_definitions(f["content"]):
                defined.append((f["filename"], name))

    untested = []
    for filename, name in defined:
        pattern = re.compile(re.escape(name))
        if not pattern.search(test_blob):
            untested.append({"file": filename, "name": name})

    coverage_ratio = None
    if defined:
        tested_count = len(defined) - len(untested)
        coverage_ratio = round(tested_count / len(defined), 2)

    return {
        "has_test_file_in_diff": len(test_files) > 0,
        "defined_symbols": len(defined),
        "untested_symbols": untested,
        "approx_coverage_ratio": coverage_ratio,
        "note": "heuristic based on name references in the diff, not measured coverage.py execution",
    }
