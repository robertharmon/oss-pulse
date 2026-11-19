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

from typing import Any


def decide(
    tool_name: str,
    tool_input: dict[str, Any],
    agent_type: str | None,
    is_subagent: bool,
    project_dir: str,
) -> str | None:
    """The reason to deny this call, or None to let it through."""
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
