"""
Turns whatever the user pastes into something the static analyzers can work with.

We deliberately do NOT try to be a full diff-apply engine (that means pulling in
the actual base file and running a proper 3-way merge, which is a much bigger
problem than this project needs to solve). Instead we support two honest modes:

1. A unified diff for a *new* file (git shows every line as an addition) -> we
   strip the leading '+' and reconstruct the file exactly.
2. A diff against an *existing* file, or just raw pasted code -> we can't know
   what the untouched lines looked like, so we only pull out the lines that
   were actually added and analyze those in isolation. This is clearly weaker
   (a linter sees fragments, not a full file) and that limitation is called
   out in the README rather than hidden.
"""

import re

DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
HUNK_HEADER_RE = re.compile(r"^@@ .* @@")


def looks_like_diff(text: str) -> bool:
    return bool(DIFF_HEADER_RE.search(text, re.MULTILINE)) or text.strip().startswith("--- ") or "\n+++ " in text


def split_into_files(diff_text: str):
    """Splits a multi-file unified diff into (filename, hunk_lines) chunks."""
    files = []
    current_name = None
    current_lines = []
    in_hunk = False

    for line in diff_text.splitlines():
        header_match = DIFF_HEADER_RE.match(line)
        if header_match:
            if current_name is not None:
                files.append((current_name, current_lines))
            current_name = header_match.group(2)
            current_lines = []
            in_hunk = False
            continue

        if line.startswith("+++ "):
            # b/path/to/file.py -> path/to/file.py, fallback if no diff --git line seen
            if current_name is None:
                name = line[4:].strip()
                current_name = name[2:] if name.startswith("b/") else name
            continue

        if line.startswith("--- "):
            continue

        if HUNK_HEADER_RE.match(line):
            in_hunk = True
            continue

        if in_hunk or current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        files.append((current_name, current_lines))

    # no diff --git headers at all but it still looked like a diff (rare, single file patch)
    if not files and diff_text.strip():
        files.append(("pasted_file.py", diff_text.splitlines()))

    return files


def reconstruct_new_file(hunk_lines):
    """Best-effort reconstruction assuming this is a brand new file (all + lines)."""
    added = [l[1:] for l in hunk_lines if l.startswith("+") and not l.startswith("+++")]
    return "\n".join(added)


def extract_added_lines_only(hunk_lines):
    added = [l[1:] for l in hunk_lines if l.startswith("+") and not l.startswith("+++")]
    return "\n".join(added)


def is_pure_addition(hunk_lines):
    for l in hunk_lines:
        if l.startswith("-") and not l.startswith("---"):
            return False
    return True


def prepare_for_analysis(raw_text: str, fallback_filename: str = "submitted_code.py"):
    """
    Returns a list of dicts: {filename, content, is_full_reconstruction}
    is_full_reconstruction=False means we only have the added-line fragments,
    which downstream analyzers should treat with lower confidence.
    """
    raw_text = raw_text.replace("\r\n", "\n")

    if not looks_like_diff(raw_text):
        return [{
            "filename": fallback_filename,
            "content": raw_text,
            "is_full_reconstruction": True,
        }]

    results = []
    for filename, hunk_lines in split_into_files(raw_text):
        pure_add = is_pure_addition(hunk_lines)
        content = reconstruct_new_file(hunk_lines) if pure_add else extract_added_lines_only(hunk_lines)
        results.append({
            "filename": filename,
            "content": content,
            "is_full_reconstruction": pure_add,
        })
    return results
