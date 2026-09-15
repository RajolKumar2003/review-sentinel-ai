import subprocess
import tempfile
import os
import json


def run_ruff(content: str, filename: str = "temp.py"):
    """
    Writes content to a temp .py file and runs ruff on it. Ruff only parses
    and statically checks the file, it never executes it, so this is safe to
    run on code we don't trust yet (which is the whole point of this tool).
    """
    if not filename.endswith(".py"):
        return {"skipped": True, "reason": f"ruff only supports python, got {filename}"}

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, os.path.basename(filename))
        with open(path, "w") as f:
            f.write(content)

        try:
            result = subprocess.run(
                ["ruff", "check", path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            return {"skipped": True, "reason": "ruff not installed"}
        except subprocess.TimeoutExpired:
            return {"skipped": True, "reason": "ruff timed out"}

        if not result.stdout.strip():
            return {"skipped": False, "issues": []}

        try:
            raw_issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"skipped": True, "reason": "could not parse ruff output"}

        issues = []
        for item in raw_issues:
            issues.append({
                "code": item.get("code"),
                "message": item.get("message"),
                "line": item.get("location", {}).get("row"),
                "severity": "warning",
            })
        return {"skipped": False, "issues": issues}
