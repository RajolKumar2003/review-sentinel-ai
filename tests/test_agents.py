from agents import correctness_agent, security_agent, coverage_agent, documentation_agent, synthesis_agent


def test_security_agent_flags_secret():
    state = {"secret_findings": [{"file": "x.py", "line": 3, "type": "aws_access_key", "snippet": "..."}]}
    result = security_agent.run(state)
    assert any("aws_access_key" in n for n in result["security_notes"])


def test_security_agent_clean():
    state = {"secret_findings": []}
    result = security_agent.run(state)
    assert "no hardcoded secrets" in result["security_notes"][0]


def test_correctness_agent_flags_complexity():
    state = {
        "lint_results": {},
        "complexity_results": {
            "x.py": {"skipped": False, "functions": [{"name": "foo", "lineno": 1, "complexity": 15, "severity": "high"}]}
        },
    }
    result = correctness_agent.run(state)
    assert any("foo" in n for n in result["correctness_notes"])


def test_coverage_agent_reports_ratio():
    state = {"coverage_results": {"approx_coverage_ratio": 1.0, "has_test_file_in_diff": True, "untested_symbols": []}}
    result = coverage_agent.run(state)
    assert any("100%" in n for n in result["coverage_notes"])


def test_documentation_agent_flags_missing():
    state = {"documentation_results": {"x.py": {"skipped": False, "has_module_docstring": False, "missing_docstrings": [{"name": "foo", "lineno": 1, "kind": "FunctionDef"}]}}}
    result = documentation_agent.run(state)
    assert any("foo" in n for n in result["documentation_notes"])


def test_synthesis_always_requires_approval():
    state = {
        "secret_findings": [{"file": "x.py", "line": 1, "type": "aws_access_key", "snippet": "x"}],
        "complexity_results": {},
        "lint_results": {},
        "coverage_results": {},
        "correctness_notes": [],
        "security_notes": [],
        "coverage_notes": [],
        "documentation_notes": [],
    }
    result = synthesis_agent.run(state)
    assert result["requires_human_approval"] is True


def test_synthesis_risk_score_increases_with_secrets():
    base_state = {
        "complexity_results": {}, "lint_results": {}, "coverage_results": {},
        "correctness_notes": [], "security_notes": [], "coverage_notes": [], "documentation_notes": [],
    }
    clean = synthesis_agent.run({**base_state, "secret_findings": []})
    dirty = synthesis_agent.run({**base_state, "secret_findings": [{"file": "x.py", "line": 1, "type": "x", "snippet": "x"}]})
    assert dirty["risk_score"] > clean["risk_score"]
