"""Claude Code PreToolUse hook: who may write (and read) which paths (backlog B11).

Reads:  the hook's JSON on stdin (tool_name, tool_input, agent_id, agent_type).
        `agent_id` is present only for subagents; the main session is the
        builder (docs/ways_of_working.md §1).
Writes: a `permissionDecision: deny` JSON on stdout when a call breaks the
        rules below; nothing otherwise (the normal permission flow applies).

Rules (file tools only; Bash isn't parsed, and CI's commit-paths and
red-proof checks are the backstop):
- Test paths can be written only by the test-writer, and by the red-team
  under tests/adversarial/. The builder and every other agent can't.
- The test-writer writes nothing but test paths.
- The red-team writes nothing outside tests/adversarial/.
- The reviewer writes nothing.
- The spec-reconstructor writes only under build/spec_reconstruction/, and
  can't read docs/ or documentation/, so it never sees the contract.
"""

import json
import os
import sys
from typing import Any

from scripts.check_commit_paths import is_test_path

WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
READ_TOOLS = frozenset({"Read", "Grep", "Glob", "NotebookRead"})
_HIDDEN_FROM_SPEC_RECONSTRUCTOR = ("docs/", "documentation/")


def _relative(path: str, project_dir: str) -> str | None:
    """`path` relative to the project with forward slashes, or None if outside it."""
    path = path.replace("\\", "/")
    root = project_dir.replace("\\", "/").rstrip("/")
    is_absolute = path.startswith("/") or (len(path) > 1 and path[1] == ":")
    if not is_absolute:
        return path.removeprefix("./")
    if path.lower().startswith(root.lower() + "/"):
        return path[len(root) + 1 :]
    return None


def _check_write(rel: str, who: str) -> str | None:
    if who == "reviewer":
        return f"The reviewer writes nothing; it tried {rel}."
    if who == "spec-reconstructor":
        if rel.startswith("build/spec_reconstruction/"):
            return None
        return (
            f"The spec-reconstructor writes only build/spec_reconstruction/; not {rel}."
        )
    if who == "test-writer":
        if is_test_path(rel):
            return None
        return f"The test-writer writes only test paths; {rel} isn't one."
    if who == "red-team":
        if rel.startswith("tests/adversarial/"):
            return None
        return f"The red-team writes only tests/adversarial/; not {rel}."
    if is_test_path(rel):
        return (
            f"{rel} is a test path. Only the test-writer subagent writes tests "
            "(docs/ways_of_working.md §3.1). If a test is wrong, ask in QUESTIONS.md."
        )
    return None


def _check_spec_reconstructor_read(
    tool_name: str, tool_input: dict[str, Any], root: str
) -> str | None:
    if tool_name == "Grep" and not tool_input.get("path"):
        return "The spec-reconstructor must give Grep a path outside docs/."
    candidates = [tool_input.get(key) for key in ("file_path", "notebook_path", "path")]
    if tool_name == "Glob":
        candidates.append(tool_input.get("pattern"))
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        rel = _relative(candidate, root)
        if rel is not None and (rel + "/").startswith(_HIDDEN_FROM_SPEC_RECONSTRUCTOR):
            return "The spec-reconstructor works from code only; docs/ is off limits."
    return None


def decide(
    tool_name: str,
    tool_input: dict[str, Any],
    agent_type: str | None,
    is_subagent: bool,
    project_dir: str,
) -> str | None:
    """The reason to deny this call, or None to let it through."""
    # Only agent_id marks a subagent; agent_type alone can be the main
    # session's --agent name, and the main session is always the builder.
    who = (agent_type or "") if is_subagent else "builder"
    if tool_name in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not isinstance(path, str):
            return None
        rel = _relative(path, project_dir)
        return None if rel is None else _check_write(rel, who)
    if tool_name in READ_TOOLS and who == "spec-reconstructor":
        return _check_spec_reconstructor_read(tool_name, tool_input, project_dir)
    return None


def main() -> int:
    event = json.load(sys.stdin)
    project_dir = (
        os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    )
    reason = decide(
        event.get("tool_name", ""),
        event.get("tool_input") or {},
        event.get("agent_type"),
        bool(event.get("agent_id")),
        project_dir,
    )
    if reason is not None:
        decision = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
        print(json.dumps({"hookSpecificOutput": decision}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
