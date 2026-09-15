from typing import TypedDict, List, Dict, Any, Optional


class ReviewState(TypedDict, total=False):
    files: List[Dict[str, Any]]  # from diff_utils.prepare_for_analysis

    lint_results: Dict[str, Any]
    secret_findings: List[Dict[str, Any]]
    complexity_results: Dict[str, Any]
    coverage_results: Dict[str, Any]
    documentation_results: Dict[str, Any]

    correctness_notes: List[str]
    security_notes: List[str]
    coverage_notes: List[str]
    documentation_notes: List[str]

    risk_score: int  # 0-100, higher = riskier, computed deterministically
    synthesis_summary: Optional[str]
    priority_findings: List[Dict[str, Any]]

    requires_human_approval: bool  # always True. never read anywhere as a variable to flip.
