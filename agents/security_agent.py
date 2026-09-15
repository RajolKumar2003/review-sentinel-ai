from agents.state import ReviewState
from agents import llm_client


def run(state: ReviewState) -> ReviewState:
    notes = []
    findings = state.get("secret_findings", [])

    for f in findings:
        notes.append(f"{f['file']}:{f['line']} possible {f['type']} exposed - {f['snippet']}")

    if not findings:
        notes.append("no hardcoded secrets or credentials detected")

    if llm_client.llm_available() and findings:
        try:
            evidence = "\n".join(notes)
            explained = llm_client.explain_evidence(
                "You are a security engineer summarizing secret-scanner findings for a code review. "
                "Do not soften the severity of exposed credentials.",
                evidence,
            )
            notes = [explained]
        except Exception as e:
            notes.append(f"(LLM explanation unavailable: {e})")

    state["security_notes"] = notes
    return state
