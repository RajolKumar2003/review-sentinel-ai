# Interview notes: ReviewSentinel AI

## 2-minute pitch

"ReviewSentinel AI is a code review accelerator built around one rule: the LLM
never invents a finding. Every piece of evidence — lint issues, complexity,
hardcoded secrets, missing docstrings, whether new code looks tested — comes
from a deterministic, independently-tested function first. A five-agent
LangGraph pipeline takes that structured evidence and does the reasoning work
a senior reviewer would do: prioritize it, explain why it matters, and roll it
into one risk score. But the system never merges anything itself —
`requires_human_approval` is hard-coded `True` in the synthesis step, not a
config flag, so there's no threshold or agent decision that can skip a human
in the loop. It runs completely free and offline by default with rule-based
agents, and a single environment variable upgrades it to use a hosted Claude
model to write nicer summaries of the exact same evidence. I built it as the
software-engineering-lifecycle counterpart to my other agentic project,
CyberSentinel AI, which applies the same deterministic-evidence-plus-agent-
reasoning pattern to network security investigation."

## Architecture walkthrough (if asked to go deeper)

1. **Ingestion (`analyzers/diff_utils.py`)** — parses a pasted unified diff or
   raw code paste into per-file content. New-file diffs reconstruct exactly;
   diffs against existing files fall back to added-lines-only, and that
   degradation is surfaced, not hidden.
2. **Deterministic analyzers** — five independent, unit-tested functions:
   ruff (lint), radon (cyclomatic complexity), a regex secret scanner, an AST
   docstring checker, and a static test-coverage heuristic. None of them
   execute the submitted code.
3. **Shared state (`agents/state.py`)** — a single `ReviewState` TypedDict that
   flows through the whole pipeline, so every agent works off the same typed
   contract instead of passing ad-hoc dicts around.
4. **Agent pipeline (`agents/pipeline.py`)** — LangGraph `StateGraph` chaining
   Correctness → Security → Coverage → Documentation → Synthesis. Each agent
   reads only the analyzer evidence relevant to its area; if an API key is
   set, it asks Claude to summarize that evidence (explicitly told not to
   invent anything beyond it); otherwise a rule-based fallback runs, so the
   app is fully functional with zero API keys.
5. **Synthesis (`agents/synthesis_agent.py`)** — computes a deterministic
   0-100 risk score from plain arithmetic (not an LLM judgment call), and
   unconditionally sets `requires_human_approval = True`.
6. **Human gate + audit trail (`app.py`, `db/models.py`)** — every review, its
   findings, and every approve/reject action is written to SQLite with a
   timestamp and the actor's name, whether or not an LLM was involved.

## Engineering notes (real trade-offs made during development)

- **Coverage measurement was the hardest design call.** The obvious approach
  is to run the code's test suite through `coverage.py` and diff the numbers.
  But this tool's entire premise is reviewing code that hasn't been vetted
  yet — executing it to measure coverage would mean running arbitrary
  untrusted code, which is a real code-execution vulnerability in exactly the
  kind of tool that's supposed to catch security problems. I replaced it with
  a static heuristic (does a defined function/class name show up anywhere in
  a file that looks like a test) and made sure the UI and README are explicit
  that this is an approximation, not measured coverage. It's a weaker signal
  than real coverage, but it's an honest one, and I'd rather defend "we chose
  not to execute untrusted code" than "we silently exec() diffs."
- **Diff reconstruction for existing files is genuinely incomplete**, and I
  decided not to fake completeness. Reconstructing a full modified file from a
  unified diff means knowing the base file, which means either requiring a
  real git checkout or calling the GitHub API for file contents — both bigger
  scope than this project needed to prove the core agent-pipeline idea. Rather
  than pretend the reconstruction is perfect, the code tags each file with
  `is_full_reconstruction` and the added-lines-only case is flagged as lower
  confidence.
- **LangGraph fallback.** Wiring the five agents through LangGraph's
  `StateGraph` is the "correct" multi-agent implementation, but a single
  broken dependency shouldn't take down a portfolio demo during a live
  interview. `agents/pipeline.py` catches the import failure and falls back to
  calling the same five functions directly in sequence — same output, same
  guarantees, just without the graph abstraction.

## Likely interview questions

**"How do you know the LLM isn't hallucinating a finding?"**
Because it never sees the raw diff. Every agent is handed pre-computed
structured evidence from a deterministic function and is explicitly prompted
to only explain/prioritize that evidence, never to generate new findings. You
can turn the LLM off entirely (no API key) and get the same findings from the
rule-based fallback — the LLM only changes the prose, never the substance.

**"What happens if the risk score is 0? Does it auto-approve?"**
No. `requires_human_approval = True` is set unconditionally in the synthesis
agent regardless of score, and reasserted again at the end of the pipeline
function as a second guarantee. There's no code path, config value, or
confidence threshold that can flip it.

**"Why didn't you just run the test suite for real coverage numbers?"**
Because that means executing code that hasn't been reviewed yet — see the
engineering notes above. I chose a weaker but safe static heuristic over a
stronger but dangerous real measurement.

**"What would you build next if you had another two weeks?"**
Real GitHub PR ingestion via the GitHub API (the pipeline function is already
decoupled from the input source, so this is mostly a new ingestion adapter),
and a FastAPI layer so the pipeline can be called from something other than
the Streamlit UI.

**"Why Streamlit instead of a full FastAPI + frontend split?"**
For this project the goal was a single deployable artifact that demonstrates
the pipeline end to end. The core logic (`analyzers/`, `agents/`) has zero
Streamlit imports, so it's already decoupled and could sit behind a FastAPI
layer without changes if this needed to become a real service.
