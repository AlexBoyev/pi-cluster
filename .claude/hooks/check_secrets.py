#!/usr/bin/env python3
"""PreToolUse hook: blocks `git commit` when the staged diff looks like it
contains a hardcoded secret/credential (CLAUDE.md security rule)."""
import json
import re
import subprocess
import sys

PLACEHOLDER_RE = re.compile(
    r"^(change_?me|xxx+|your[_-].*|<.*>|\{\{.*\}\}|\$\{.*\}|example.*|test.*|"
    r"dummy.*|redacted|placeholder|todo|none|null|fixme|sample.*|"
    r"insert.*here|replace.*)$",
    re.IGNORECASE,
)

SPECIFIC_PATTERNS = [
    ("AWS access key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]

GENERIC_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)"
    r"\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?"
)


def added_lines(diff_text: str):
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            yield line[1:]


def scan(diff_text: str):
    findings = []
    for line in added_lines(diff_text):
        for name, pattern in SPECIFIC_PATTERNS:
            if pattern.search(line):
                findings.append(name)
        m = GENERIC_ASSIGNMENT_RE.search(line)
        if m:
            key, value = m.group(1), m.group(2)
            if not PLACEHOLDER_RE.match(value):
                findings.append(f"possible {key} value")
    return findings


def main():
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass  # tool_input isn't needed beyond the `if` filter already applied

    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        # Fail open: never block a commit because the scanner itself broke.
        print(f"check_secrets.py: could not run git diff ({exc}), skipping scan", file=sys.stderr)
        return

    if result.returncode != 0:
        print(f"check_secrets.py: git diff --cached failed, skipping scan: {result.stderr}", file=sys.stderr)
        return

    findings = scan(result.stdout)
    if not findings:
        return

    unique = sorted(set(findings))
    reason = (
        "Staged diff looks like it contains a secret/credential ("
        + ", ".join(unique)
        + "). CLAUDE.md forbids hardcoded secrets - move it to .env and "
        "re-stage, or unstage this file if it's a false positive."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


if __name__ == "__main__":
    main()
