from agents.state import ReviewState
from agents import llm_client


def run(state: ReviewState) -> ReviewState:
    notes = []
    result = state.get("coverage_results", {})

    if not result:
        notes.append("no python files to evaluate for test coverage")
    else:
        ratio = result.get("approx_coverage_ratio")
        if ratio is None:
            notes.append("no functions or classes defined in this diff, nothing to test")
        else:
            notes.append(f"approx {int(ratio * 100)}% of new symbols appear referenced by a test (heuristic, not measured)")

        if not result.get("has_test_file_in_diff"):
            notes.append("no test file included in this diff")

        for item in result.get("untested_symbols", []):
            notes.append(f"{item['file']}: '{item['name']}' has no apparent test reference")

    if llm_client.llm_available():
        try:
            evidence = "\n".join(notes)
            explained = llm_client.explain_evidence(
                "You are summarizing static test-coverage heuristics for a code review. "
                "Be clear these are heuristics, not measured coverage.",
                evidence,
            )
            notes = [explained]
        except Exception as e:
            notes.append(f"(LLM explanation unavailable: {e})")

    state["coverage_notes"] = notes
    return state
