from agents.state import ReviewState

# this is the one function in the whole pipeline where a single mistake would
# defeat the entire "human approves everything" promise, so the risk score is
# a plain deterministic sum, nothing an LLM can nudge one way or the other.


def _compute_risk_score(state: ReviewState) -> int:
    score = 0
    score += len(state.get("secret_findings", [])) * 30

    for result in state.get("complexity_results", {}).values():
        if result.get("skipped"):
            continue
        for fn in result.get("functions", []):
            if fn["severity"] == "high":
                score += 10
            elif fn["severity"] == "medium":
                score += 4

    for result in state.get("lint_results", {}).values():
        if result.get("skipped"):
            continue
        score += len(result.get("issues", [])) * 2

    coverage = state.get("coverage_results", {})
    ratio = coverage.get("approx_coverage_ratio")
    if ratio is not None and ratio < 0.5:
        score += 15

    return min(score, 100)


def run(state: ReviewState) -> ReviewState:
    score = _compute_risk_score(state)

    priority_findings = []
    if state.get("secret_findings"):
        priority_findings.append({"severity": "critical", "area": "security", "detail": "hardcoded secret(s) detected"})

    for result in state.get("complexity_results", {}).values():
        if result.get("skipped"):
            continue
        for fn in result.get("functions", []):
            if fn["severity"] == "high":
                priority_findings.append({
                    "severity": "high",
                    "area": "correctness",
                    "detail": f"function '{fn['name']}' complexity {fn['complexity']}",
                })

    coverage = state.get("coverage_results", {})
    if coverage.get("approx_coverage_ratio") is not None and coverage["approx_coverage_ratio"] < 0.5:
        priority_findings.append({"severity": "medium", "area": "coverage", "detail": "less than half of new symbols appear tested"})

    if score >= 60:
        verdict = "high risk"
    elif score >= 25:
        verdict = "needs attention"
    else:
        verdict = "looks reasonable"

    summary_lines = [
        f"Risk score: {score}/100 ({verdict})",
        "",
        "Correctness:",
        *[f"  - {n}" for n in state.get("correctness_notes", [])],
        "",
        "Security:",
        *[f"  - {n}" for n in state.get("security_notes", [])],
        "",
        "Test coverage:",
        *[f"  - {n}" for n in state.get("coverage_notes", [])],
        "",
        "Documentation:",
        *[f"  - {n}" for n in state.get("documentation_notes", [])],
    ]

    state["risk_score"] = score
    state["priority_findings"] = priority_findings
    state["synthesis_summary"] = "\n".join(summary_lines)

    # hard-coded, not a config value, not something upstream state can override.
    # every single code path through this pipeline ends here with this exact line.
    state["requires_human_approval"] = True

    return state
