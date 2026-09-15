import os

DEFAULT_MODEL = os.environ.get("REVIEWSENTINEL_MODEL", "claude-sonnet-5")


def llm_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def explain_evidence(system_prompt: str, evidence_summary: str) -> str:
    """
    Sends already-computed, structured evidence to Claude and asks it to
    explain/prioritize it in plain English. The model is never given the raw
    diff and told to "find bugs" - it only ever narrates evidence that the
    deterministic analyzers already produced. If no API key is set, callers
    should fall back to the rule-based agent logic instead of calling this.
    """
    if not llm_available():
        raise RuntimeError("ANTHROPIC_API_KEY not set, use the rule-based fallback instead")

    # imported lazily so the whole app still works with zero extra deps
    # when nobody has an API key configured
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Here is the structured evidence a static analyzer already produced. "
                       f"Do not invent any findings that aren't in this evidence. "
                       f"Summarize and prioritize it for a human reviewer:\n\n{evidence_summary}",
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")
