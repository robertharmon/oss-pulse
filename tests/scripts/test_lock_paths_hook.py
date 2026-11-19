import pytest

from scripts.lock_paths_hook import decide

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
