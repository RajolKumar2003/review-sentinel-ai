from radon.complexity import cc_visit
from radon.visitors import ComplexityVisitor

# thresholds are a judgment call, not a law of physics - tuned loosely against
# what most style guides consider "getting hard to review"
WARN_THRESHOLD = 8
FLAG_THRESHOLD = 12


def analyze(content: str, filename: str = ""):
    if not filename.endswith(".py"):
        return {"skipped": True, "reason": f"complexity analysis only supports python, got {filename}"}

    try:
        blocks = cc_visit(content)
    except SyntaxError as e:
        return {"skipped": True, "reason": f"could not parse file: {e}"}

    results = []
    for block in blocks:
        severity = "ok"
        if block.complexity >= FLAG_THRESHOLD:
            severity = "high"
        elif block.complexity >= WARN_THRESHOLD:
            severity = "medium"

        results.append({
            "name": block.name,
            "complexity": block.complexity,
            "lineno": block.lineno,
            "severity": severity,
        })

    return {"skipped": False, "functions": results}
