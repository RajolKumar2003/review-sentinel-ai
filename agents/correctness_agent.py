from agents.state import ReviewState
from agents import llm_client


def run(state: ReviewState) -> ReviewState:
    notes = []
    lint = state.get("lint_results", {})
    complexity = state.get("complexity_results", {})

    for filename, result in lint.items():
        if result.get("skipped"):
            continue
        for issue in result.get("issues", []):
            notes.append(f"{filename}:{issue['line']} [{issue['code']}] {issue['message']}")

    for filename, result in complexity.items():
        if result.get("skipped"):
            continue
        for fn in result.get("functions", []):
            if fn["severity"] in ("medium", "high"):
                notes.append(
                    f"{filename}:{fn['lineno']} function '{fn['name']}' has cyclomatic complexity "
                    f"{fn['complexity']} ({fn['severity']}) - consider breaking it up"
                )

    if not notes:
        notes.append("no lint or complexity issues found by static analysis")

    if llm_client.llm_available():
        try:
            evidence = "\n".join(notes)
            explained = llm_client.explain_evidence(
                "You are a senior engineer summarizing correctness findings from a static analyzer for a code review.",
                evidence,
            )
            notes = [explained]
        except Exception as e:
            notes.append(f"(LLM explanation unavailable: {e})")

    state["correctness_notes"] = notes
    return state
