import os
from agents.pipeline import run_pipeline

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def _read_sample(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def test_clean_sample_has_low_risk_and_still_requires_approval():
    diff_text = _read_sample("sample_clean.diff")
    result = run_pipeline(diff_text)
    assert result["requires_human_approval"] is True
    assert result["risk_score"] < 25


def test_issues_sample_flags_secret_and_complexity():
    diff_text = _read_sample("sample_with_issues.diff")
    result = run_pipeline(diff_text)
    assert result["requires_human_approval"] is True
    assert len(result["secret_findings"]) > 0
    assert result["risk_score"] > 25
    areas_flagged = {f["area"] for f in result["priority_findings"]}
    assert "security" in areas_flagged


def test_pipeline_never_skips_human_approval_regardless_of_score():
    clean = run_pipeline(_read_sample("sample_clean.diff"))
    dirty = run_pipeline(_read_sample("sample_with_issues.diff"))
    assert clean["requires_human_approval"] is True
    assert dirty["requires_human_approval"] is True
