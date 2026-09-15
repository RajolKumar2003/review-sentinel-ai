import streamlit as st
from datetime import datetime

from agents.pipeline import run_pipeline
from agents import llm_client
from db.database import init_db, get_session
from db.models import Review, Finding, AuditLogEntry

st.set_page_config(page_title="ReviewSentinel AI", page_icon="\U0001F6E1\uFE0F", layout="wide")
init_db()

SAMPLE_CLEAN = open("sample_data/sample_clean.diff").read()
SAMPLE_ISSUES = open("sample_data/sample_with_issues.diff").read()


def save_review(filename, state):
    session = get_session()
    review = Review(
        filename=filename,
        status="pending",
        risk_score=state.get("risk_score", 0),
        synthesis_summary=state.get("synthesis_summary", ""),
    )
    session.add(review)
    session.flush()

    for pf in state.get("priority_findings", []):
        session.add(Finding(review_id=review.id, severity=pf["severity"], area=pf["area"], detail=pf["detail"]))

    session.add(AuditLogEntry(review_id=review.id, actor="system", action="created", notes="pipeline run completed"))
    session.commit()
    review_id = review.id
    session.close()
    return review_id


def update_status(review_id, new_status, actor):
    session = get_session()
    review = session.get(Review, review_id)
    review.status = new_status
    session.add(AuditLogEntry(review_id=review_id, actor=actor, action=new_status))
    session.commit()
    session.close()


st.title("\U0001F6E1\uFE0F ReviewSentinel AI")
st.caption("Deterministic static analysis + agent reasoning. Nothing here ever auto-merges.")

if llm_client.llm_available():
    st.info(f"Hosted LLM upgrade active (model: {llm_client.DEFAULT_MODEL}). Agents will use Claude to explain evidence.")
else:
    st.warning("No ANTHROPIC_API_KEY found - running fully offline on rule-based agent logic. This is the default, zero-cost mode.")

tab_review, tab_queue, tab_audit, tab_about = st.tabs(["New Review", "Review Queue", "Audit Log", "About"])

if "diff_text_input" not in st.session_state:
    st.session_state["diff_text_input"] = ""

with tab_review:
    col1, col2 = st.columns([2, 1])
    with col2:
        st.subheader("Load a sample")
        if st.button("Load clean sample diff"):
            st.session_state["diff_text_input"] = SAMPLE_CLEAN
        if st.button("Load sample diff with issues"):
            st.session_state["diff_text_input"] = SAMPLE_ISSUES

    with col1:
        filename = st.text_input("Filename (used when the pasted text isn't a full diff)", value="submitted_code.py")
        diff_text = st.text_area(
            "Paste a unified diff or raw python code",
            key="diff_text_input",
            height=350,
        )

        if st.button("Run Review", type="primary"):
            if not diff_text.strip():
                st.error("paste something first")
            else:
                with st.spinner("running static analyzers and agent pipeline..."):
                    result_state = run_pipeline(diff_text, filename)
                st.session_state["last_state"] = result_state
                st.session_state["last_review_id"] = save_review(filename, result_state)

    if "last_state" in st.session_state:
        state = st.session_state["last_state"]
        st.divider()
        st.subheader(f"Result - risk score {state.get('risk_score', 0)}/100")
        st.text(state.get("synthesis_summary", ""))

        with st.expander("Raw evidence (what the deterministic analyzers actually found)"):
            st.write("**Lint (ruff)**")
            st.json(state.get("lint_results", {}))
            st.write("**Secrets**")
            st.json(state.get("secret_findings", []))
            st.write("**Complexity**")
            st.json(state.get("complexity_results", {}))
            st.write("**Coverage heuristic**")
            st.json(state.get("coverage_results", {}))
            st.write("**Documentation**")
            st.json(state.get("documentation_results", {}))

        st.divider()
        st.subheader("Human decision required")
        st.write("Nothing above is a merge decision. A human has to explicitly approve or reject below.")
        approver = st.text_input("Your name/handle", value="reviewer")
        c1, c2 = st.columns(2)
        if c1.button("Approve"):
            update_status(st.session_state["last_review_id"], "approved", approver)
            st.success("marked approved and logged")
        if c2.button("Reject"):
            update_status(st.session_state["last_review_id"], "rejected", approver)
            st.error("marked rejected and logged")

with tab_queue:
    st.subheader("All reviews")
    session = get_session()
    reviews = session.query(Review).order_by(Review.created_at.desc()).all()
    if not reviews:
        st.write("no reviews yet")
    for r in reviews:
        with st.expander(f"#{r.id} {r.filename} - {r.status} - risk {r.risk_score}"):
            st.text(r.synthesis_summary)
            st.caption(f"created {r.created_at}")
    session.close()

with tab_audit:
    st.subheader("Audit log")
    session = get_session()
    entries = session.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc()).all()
    if not entries:
        st.write("no audit entries yet")
    for e in entries:
        st.text(f"[{e.timestamp}] review #{e.review_id} - {e.actor} -> {e.action}" + (f" ({e.notes})" if e.notes else ""))
    session.close()

with tab_about:
    st.markdown("""
    **ReviewSentinel AI** is a code review accelerator, not an autonomous merge bot.

    Design rules that are actually enforced in code, not just described in this README:
    - Every finding traces back to a deterministic analyzer (ruff, radon, a regex secret scanner, an AST docstring
      check, and a static test-reference heuristic). The LLM agents only ever explain and prioritize that evidence.
    - `requires_human_approval` is hard-coded to `True` in the synthesis agent and re-asserted at the end of the
      pipeline. There is no config flag or confidence threshold anywhere that can skip it.
    - Submitted code is never executed. All analysis is static (AST parsing, regex, or a linter subprocess),
      which is also why "test coverage" here is a static heuristic and not a real coverage.py run.
    - Works fully offline for free. Setting `ANTHROPIC_API_KEY` upgrades the agents to use a hosted Claude model
      to write nicer summaries of the exact same evidence, nothing more.
    """)
