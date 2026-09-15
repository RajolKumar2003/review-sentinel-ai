from agents.state import ReviewState
from agents import correctness_agent, security_agent, coverage_agent, documentation_agent, synthesis_agent
from analyzers import diff_utils, secret_scanner, lint_analyzer, complexity_analyzer, coverage_analyzer, documentation_analyzer

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def build_evidence(raw_text: str, fallback_filename: str = "submitted_code.py") -> ReviewState:
    """Runs every deterministic analyzer and packs the results into a fresh state dict.
    Nothing in here is an LLM call, this whole function should be reproducible byte for byte."""
    files = diff_utils.prepare_for_analysis(raw_text, fallback_filename)

    lint_results = {}
    complexity_results = {}
    documentation_results = {}
    all_secrets = []

    for f in files:
        lint_results[f["filename"]] = lint_analyzer.run_ruff(f["content"], f["filename"])
        complexity_results[f["filename"]] = complexity_analyzer.analyze(f["content"], f["filename"])
        documentation_results[f["filename"]] = documentation_analyzer.analyze(f["content"], f["filename"])
        all_secrets.extend(secret_scanner.scan(f["content"], f["filename"]))

    coverage_results = coverage_analyzer.analyze(files)

    state: ReviewState = {
        "files": files,
        "lint_results": lint_results,
        "secret_findings": all_secrets,
        "complexity_results": complexity_results,
        "coverage_results": coverage_results,
        "documentation_results": documentation_results,
    }
    return state


def _build_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("correctness", correctness_agent.run)
    graph.add_node("security", security_agent.run)
    graph.add_node("coverage", coverage_agent.run)
    graph.add_node("documentation", documentation_agent.run)
    graph.add_node("synthesis", synthesis_agent.run)

    graph.set_entry_point("correctness")
    graph.add_edge("correctness", "security")
    graph.add_edge("security", "coverage")
    graph.add_edge("coverage", "documentation")
    graph.add_edge("documentation", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


_compiled_graph = None


def run_pipeline(raw_text: str, fallback_filename: str = "submitted_code.py") -> ReviewState:
    state = build_evidence(raw_text, fallback_filename)

    if LANGGRAPH_AVAILABLE:
        global _compiled_graph
        if _compiled_graph is None:
            _compiled_graph = _build_graph()
        result = _compiled_graph.invoke(state)
    else:
        # langgraph didn't import for some reason (e.g. a broken environment),
        # fall back to calling the same agent functions in the same order by hand.
        # this keeps the app usable even if that one dependency has a bad day.
        result = correctness_agent.run(state)
        result = security_agent.run(result)
        result = coverage_agent.run(result)
        result = documentation_agent.run(result)
        result = synthesis_agent.run(result)

    # belt and suspenders: even if some future refactor breaks synthesis_agent,
    # this can never be anything but True by the time it leaves the pipeline.
    result["requires_human_approval"] = True
    return result
