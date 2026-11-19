import io
import json
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.lock_paths_hook import decide, main

ROOT = "/repo"


def _write(path: str, who: str | None, tool: str = "Write") -> str | None:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return decide(tool, {key: f"{ROOT}/{path}"}, who, who is not None, ROOT)


TEST_FILES = [
    "tests/ingest/test_hello.py",
    "tests/fixtures/hour.json.gz",
    "tests/expected/trending.csv",
    "dbt/tests/r01.sql",
    "dbt/models/staging/_unit_tests.yml",
    "terraform/tests/a.tftest.hcl",
]


@pytest.mark.parametrize("path", TEST_FILES)
@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_builder_cannot_write_test_paths(path: str, tool: str) -> None:
    reason = _write(path, None, tool)
    assert reason is not None
    assert path in reason


def test_builder_can_write_code_and_docs() -> None:
    for path in ["ingest/src/osp_ingest/hello.py", "docs/roadmap.md", "scripts/x.py"]:
        assert _write(path, None) is None


@pytest.mark.parametrize("who", ["general-purpose", "Explore", "Plan"])
def test_other_agents_cannot_write_test_paths(who: str) -> None:
    assert _write("tests/ingest/test_hello.py", who) is not None


def test_test_writer_writes_only_test_paths() -> None:
    assert _write("tests/ingest/test_hello.py", "test-writer") is None
    assert _write("dbt/models/staging/_unit_tests.yml", "test-writer") is None
    assert _write("ingest/src/osp_ingest/hello.py", "test-writer") is not None


def test_red_team_writes_only_adversarial_tests() -> None:
    assert _write("tests/adversarial/test_break.py", "red-team") is None
    assert _write("tests/ingest/test_hello.py", "red-team") is not None
    assert _write("ingest/src/osp_ingest/hello.py", "red-team") is not None


def test_reviewer_writes_nothing() -> None:
    assert _write("docs/roadmap.md", "reviewer") is not None
    assert _write("build/notes.md", "reviewer") is not None


def test_spec_reconstructor_writes_only_its_output_folder() -> None:
    who = "spec-reconstructor"
    assert _write("build/spec_reconstruction/stg_events.yml", who) is None
    assert _write("docs/data_contract.md", who) is not None
    assert _write("dbt/models/staging/stg_events.sql", who) is not None


def test_spec_reconstructor_cannot_read_docs() -> None:
    who = "spec-reconstructor"

    def read(tool: str, tool_input: dict[str, str]) -> str | None:
        return decide(tool, tool_input, who, True, ROOT)

    assert read("Read", {"file_path": f"{ROOT}/docs/data_contract.md"}) is not None
    assert read("Read", {"file_path": f"{ROOT}/documentation/Session05.md"}) is not None
    assert read("Grep", {"pattern": "grain", "path": f"{ROOT}/docs"}) is not None
    assert read("Glob", {"pattern": "docs/**/*.md"}) is not None
    assert read("Read", {"file_path": f"{ROOT}/dbt/models/staging/x.sql"}) is None


def test_other_agents_can_read_docs() -> None:
    for who in [None, "test-writer", "reviewer"]:
        tool_input = {"file_path": f"{ROOT}/docs/data_contract.md"}
        assert decide("Read", tool_input, who, who is not None, ROOT) is None


def test_relative_and_backslash_paths_are_normalized() -> None:
    assert decide("Write", {"file_path": "tests/x.py"}, None, False, ROOT) is not None
    windows = {"file_path": "C:\\repo\\tests\\x.py"}
    assert decide("Edit", windows, None, False, "C:\\repo") is not None


def test_paths_outside_the_project_are_not_this_hooks_business() -> None:
    outside = {"file_path": "/home/someone/scratch/test_x.py"}
    assert decide("Write", outside, None, False, ROOT) is None


def test_session_started_with_agent_flag_is_still_the_builder() -> None:
    # agent_type can be set in the main session (--agent); only agent_id marks a
    # subagent. A main session named "test-writer" must not get its rights.
    assert decide(
        "Write", {"file_path": f"{ROOT}/tests/x.py"}, "test-writer", False, ROOT
    )


# --- Audit additions (spec: ADR 0002 §2, ways of working §1, module docstring) --


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_reviewer_writes_nothing_with_any_file_tool(tool: str) -> None:
    assert _write("tests/ingest/test_hello.py", "reviewer", tool) is not None
    assert _write("ingest/src/osp_ingest/hello.py", "reviewer", tool) is not None


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "NotebookEdit"])
def test_test_writer_is_held_to_test_paths_with_every_file_tool(tool: str) -> None:
    assert _write("tests/ingest/test_hello.py", "test-writer", tool) is None
    assert _write("ingest/src/osp_ingest/hello.py", "test-writer", tool) is not None


@pytest.mark.parametrize("who", ["general-purpose", "Explore", "claude", "anything"])
def test_other_agents_can_write_non_test_paths(who: str) -> None:
    assert _write("ingest/src/osp_ingest/hello.py", who) is None


def test_lookalike_folders_are_not_the_locked_ones() -> None:
    # Path rules match whole folder names, not string prefixes.
    assert _write("testsuite/x.py", None) is None
    assert _write("tests/adversarial_extra/test_x.py", "red-team") is not None
    who = "spec-reconstructor"
    assert _write("build/spec_reconstruction_old/x.yml", who) is not None
    nested_docs = {"file_path": f"{ROOT}/dbt/models/docs/overview.md"}
    assert decide("Read", nested_docs, who, True, ROOT) is None


def test_dot_dot_segments_cant_dodge_the_rules() -> None:
    assert _write("ingest/../tests/test_x.py", None) is not None
    who = "spec-reconstructor"
    assert _write("build/spec_reconstruction/../../docs/x.md", who) is not None
    sneaky = {"file_path": f"{ROOT}/dbt/../docs/data_contract.md"}
    assert decide("Read", sneaky, who, True, ROOT) is not None


def test_spec_reconstructor_cant_search_docs_by_folder_or_whole_repo() -> None:
    who = "spec-reconstructor"

    def call(tool: str, tool_input: dict[str, str]) -> str | None:
        return decide(tool, tool_input, who, True, ROOT)

    assert call("Glob", {"pattern": "*.md", "path": f"{ROOT}/docs"}) is not None
    assert call("Glob", {"pattern": "*.md", "path": f"{ROOT}/documentation"})
    # Grep with no path, or the project root, searches docs/ along with the rest,
    # and returns the contract's lines.
    assert call("Grep", {"pattern": "grain"}) is not None
    assert call("Grep", {"pattern": "grain", "path": ROOT}) is not None
    assert call("Grep", {"pattern": "grain", "path": f"{ROOT}/dbt"}) is None


def test_spec_reconstructor_cant_read_docs_by_windows_path() -> None:
    tool_input = {"file_path": "C:\repo\\docs\\data_contract.md"}
    assert decide("Read", tool_input, "spec-reconstructor", True, "C:\repo")


def test_bash_is_not_parsed() -> None:
    tool_input = {"command": "echo x > tests/test_x.py"}
    assert decide("Bash", tool_input, None, False, ROOT) is None


def _run_main(
    payload: Mapping[str, object],
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    # The hook runs with the project as cwd and CLAUDE_PROJECT_DIR set
    # (.claude/settings.json), and the input carries cwd too.
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    monkeypatch.chdir(project)
    data = json.dumps({"cwd": str(project), **payload}).encode()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
    code = main()
    return code, capsys.readouterr().out


def test_main_denies_with_a_pretooluse_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "tests" / "test_x.py")},
    }
    code, out = _run_main(payload, tmp_path, monkeypatch, capsys)
    assert code == 0  # Claude Code reads the JSON decision only on exit 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"]


def test_main_lets_a_subagent_test_writer_through_silently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "tests" / "test_x.py")},
        "agent_id": "a1b2c3",
        "agent_type": "test-writer",
    }
    code, out = _run_main(payload, tmp_path, monkeypatch, capsys)
    assert code == 0
    assert out.strip() == ""


def test_main_treats_agent_type_without_agent_id_as_the_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Module docstring: `agent_id` is present only for subagents. A main session
    # started with --agent test-writer carries agent_type but no agent_id.
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "tests" / "test_x.py")},
        "agent_type": "test-writer",
    }
    code, out = _run_main(payload, tmp_path, monkeypatch, capsys)
    assert code == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
