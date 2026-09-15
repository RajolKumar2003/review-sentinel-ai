from analyzers import diff_utils, secret_scanner, lint_analyzer, complexity_analyzer, documentation_analyzer, coverage_analyzer


def test_looks_like_diff():
    assert diff_utils.looks_like_diff("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n")
    assert not diff_utils.looks_like_diff("def foo():\n    return 1\n")


def test_reconstruct_new_file():
    raw = (
        "diff --git a/x.py b/x.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/x.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+def foo():\n"
        "+    return 1\n"
    )
    files = diff_utils.prepare_for_analysis(raw)
    assert len(files) == 1
    assert files[0]["filename"] == "x.py"
    assert files[0]["is_full_reconstruction"] is True
    assert "def foo():" in files[0]["content"]


def test_raw_code_fallback():
    files = diff_utils.prepare_for_analysis("def foo():\n    return 1\n", "plain.py")
    assert files[0]["filename"] == "plain.py"
    assert files[0]["content"].startswith("def foo")


def test_secret_scanner_finds_aws_key():
    content = 'aws_key = "AKIAABCDEFGHIJKLMNOP"\n'
    findings = secret_scanner.scan(content, "config.py")
    assert any(f["type"] == "aws_access_key" for f in findings)


def test_secret_scanner_clean_code():
    content = "def add(a, b):\n    return a + b\n"
    assert secret_scanner.scan(content, "clean.py") == []


def test_lint_analyzer_catches_unused_import():
    content = "import os\n\ndef foo():\n    return 1\n"
    result = lint_analyzer.run_ruff(content, "bad.py")
    if result.get("skipped"):
        return  # ruff not available in this environment, don't fail the suite over it
    codes = [i["code"] for i in result["issues"]]
    assert any(c and c.startswith("F401") for c in codes)


def test_lint_analyzer_skips_non_python():
    result = lint_analyzer.run_ruff("<html></html>", "index.html")
    assert result["skipped"] is True


def test_complexity_simple_function_is_low():
    content = "def add(a, b):\n    return a + b\n"
    result = complexity_analyzer.analyze(content, "simple.py")
    assert result["functions"][0]["severity"] == "ok"


def test_complexity_flags_high_complexity():
    branches = "\n".join(f"    if x == {i}:\n        y = {i}" for i in range(15))
    content = f"def messy(x):\n{branches}\n    return x\n"
    result = complexity_analyzer.analyze(content, "messy.py")
    assert result["functions"][0]["severity"] in ("medium", "high")


def test_documentation_analyzer_flags_missing_docstring():
    content = "def helper():\n    return 1\n"
    result = documentation_analyzer.analyze(content, "nodoc.py")
    assert any(m["name"] == "helper" for m in result["missing_docstrings"])


def test_documentation_analyzer_module_docstring_detected():
    content = '"""module doc"""\n\ndef helper():\n    """helper doc"""\n    return 1\n'
    result = documentation_analyzer.analyze(content, "documented.py")
    assert result["has_module_docstring"] is True
    assert result["missing_docstrings"] == []


def test_coverage_analyzer_detects_untested_symbol():
    files = [{"filename": "src.py", "content": "def foo():\n    return 1\n", "is_full_reconstruction": True}]
    result = coverage_analyzer.analyze(files)
    assert result["has_test_file_in_diff"] is False
    assert any(u["name"] == "foo" for u in result["untested_symbols"])


def test_coverage_analyzer_detects_tested_symbol():
    files = [
        {"filename": "src.py", "content": "def foo():\n    return 1\n", "is_full_reconstruction": True},
        {"filename": "test_src.py", "content": "from src import foo\ndef test_foo():\n    assert foo() == 1\n", "is_full_reconstruction": True},
    ]
    result = coverage_analyzer.analyze(files)
    assert result["approx_coverage_ratio"] == 1.0
