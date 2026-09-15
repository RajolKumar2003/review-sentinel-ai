from agents.state import ReviewState
from agents import llm_client


def run(state: ReviewState) -> ReviewState:
    notes = []
    doc_results = state.get("documentation_results", {})

    for filename, result in doc_results.items():
        if result.get("skipped"):
            continue
        if not result.get("has_module_docstring"):
            notes.append(f"{filename}: no module-level docstring")
        for item in result.get("missing_docstrings", []):
            notes.append(f"{filename}:{item['lineno']} {item['kind']} '{item['name']}' has no docstring")

    if not notes:
        notes.append("documentation looks reasonably complete for this diff")

    if llm_client.llm_available():
        try:
            evidence = "\n".join(notes)
            explained = llm_client.explain_evidence(
                "You are summarizing documentation coverage findings for a code review, be concise.",
                evidence,
            )
            notes = [explained]
        except Exception as e:
            notes.append(f"(LLM explanation unavailable: {e})")

    state["documentation_notes"] = notes
    return state
