"""GitHub Actions policy check (backlog B11, access matrix §6, security §6).

Reads:  .github/workflows/*.yml and *.yaml.
Fails:  if a workflow uses `pull_request_target`, has no top-level
        `permissions:` block, or references an action not pinned to a full
        40-character commit SHA (local `./` actions and digest-pinned
        `docker://` images are allowed).
"""

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

_USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^\s'\"#]+)", re.MULTILINE)
_PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
_PINNED_DOCKER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
_TOP_LEVEL_PERMISSIONS = re.compile(r"^permissions:", re.MULTILINE)
_PR_TARGET = re.compile(r"\bpull_request_target\b")
_COMMENT = re.compile(r"(^|\s)#.*$")


def _without_comments(text: str) -> str:
    """Drop YAML `#` comments, so prose about a rule doesn't trip it."""
    return "\n".join(_COMMENT.sub("", line) for line in text.splitlines())


def check_workflow(name: str, text: str) -> list[str]:
    """One problem per policy violation in a workflow file."""
    problems = []
    text = _without_comments(text)
    if _PR_TARGET.search(text):
        problems.append(f"{name}: uses pull_request_target, which is banned")
    if not _TOP_LEVEL_PERMISSIONS.search(text):
        problems.append(f"{name}: no top-level `permissions:` block")
    for ref in _USES.findall(text):
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not _PINNED_DOCKER.match(ref):
                problems.append(f"{name}: {ref} is not pinned to an image digest")
        elif not _PINNED_ACTION.match(ref):
            problems.append(f"{name}: {ref} is not pinned to a full commit SHA")
    return problems


def main() -> int:
    files = sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")])
    problems = [
        problem
        for path in files
        for problem in check_workflow(path.name, path.read_text(encoding="utf-8"))
    ]
    print(f"{len(files)} workflows checked")
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
