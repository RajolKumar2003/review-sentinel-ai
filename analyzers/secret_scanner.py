import re

# not trying to catch every possible secret format on earth, just the common
# ones that actually show up in real leaked-credential incidents
PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "aws_secret_key": re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][0-9a-zA-Z/+]{40}['\"]"),
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    "private_key_block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "hardcoded_password": re.compile(r"(?i)password\s*=\s*['\"][^'\"]{4,}['\"]"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
}


def scan(content: str, filename: str = ""):
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, start=1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append({
                    "type": label,
                    "line": i,
                    "snippet": line.strip()[:120],
                    "severity": "critical",
                    "file": filename,
                })
    return findings
