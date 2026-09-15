import ast


def analyze(content: str, filename: str = ""):
    if not filename.endswith(".py"):
        return {"skipped": True, "reason": f"docstring analysis only supports python, got {filename}"}

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return {"skipped": True, "reason": f"could not parse file: {e}"}

    module_doc = ast.get_docstring(tree)

    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node) is None:
                missing.append({"name": node.name, "lineno": node.lineno, "kind": type(node).__name__})

    return {
        "skipped": False,
        "has_module_docstring": module_doc is not None,
        "missing_docstrings": missing,
    }
