import subprocess
from pathlib import Path

import pytest

from scripts.check_commit_paths import classify_commit, evaluate, is_test_path, main


@pytest.mark.parametrize(
    "path",
    [
        "tests/ingest/test_hello.py",
        "tests/fixtures/hour.json.gz",
        "dbt/tests/reconciliation/r01.sql",
        "dbt/models/staging/_unit_tests.yml",
        "dbt/models/marts/trending/_unit_tests.yml",
        "terraform/tests/buckets.tftest.hcl",
    ],
)
def test_test_paths(path: str) -> None:
    assert is_test_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "ingest/src/osp_ingest/hello.py",
        "dbt/models/staging/schema.yml",
        "dbt/models/staging/stg_events.sql",
        "scripts/check_commit_paths.py",
        "pyproject.toml",
        "docs/tests.md",
        "testsuite/x.py",
    ],
)
def test_non_test_paths(path: str) -> None:
    assert not is_test_path(path)


def test_classify() -> None:
    assert classify_commit(["tests/a.py", "tests/b.py"]) == "test"
    assert classify_commit(["ingest/a.py", "README.md"]) == "code"
    assert classify_commit(["tests/a.py", "ingest/a.py"]) == "mixed"
    assert classify_commit([]) == "empty"


def test_evaluate_flags_only_mixed_commits() -> None:
    commits = [
        ("aaa1111", ["ingest/a.py"]),
        ("bbb2222", ["tests/test_a.py"]),
        ("ccc3333", ["tests/test_a.py", "ingest/a.py"]),
    ]
    problems = evaluate(commits)
    assert len(problems) == 1
    assert "ccc3333" in problems[0]
    assert "tests/test_a.py" in problems[0]
    assert "ingest/a.py" in problems[0]


# --- Audit additions (spec: ways of working §3.1, module docstring) ---------


@pytest.mark.parametrize(
    "path",
    [
        "dbt/models/_unit_tests.yml",  # `**/` matches zero folders too
        "dbt/models/marts/trending/daily/_unit_tests.yml",
        "terraform/tests/modules/buckets/a.tftest.hcl",
        "tests/adversarial/test_break.py",
    ],
)
def test_nested_and_shallow_test_paths(path: str) -> None:
    assert is_test_path(path)


@pytest.mark.parametrize(
    "path",
    [
        # The list in §3.1 is explicit: a `tests/` folder elsewhere isn't one.
        "ingest/tests/test_hello.py",
        "dbt/macros/tests/x.sql",
        "terraform/modules/x/tests/a.tftest.hcl",
        "dbt/testsx/a.sql",
        "terraform/testsuite/a.hcl",
        # Unit-test files count only by exact name, and only under dbt/models.
        "dbt/models/staging/my_unit_tests.yml",
        "dbt/_unit_tests.yml",
    ],
)
def test_lookalike_paths_are_not_test_paths(path: str) -> None:
    assert not is_test_path(path)


def test_evaluate_reports_every_mixed_commit_and_ignores_empty_ones() -> None:
    commits = [
        ("aaa1111", ["tests/test_a.py", "ingest/a.py"]),
        ("bbb2222", []),
        ("ccc3333", ["terraform/main.tf", "terraform/tests/a.tftest.hcl"]),
    ]
    problems = evaluate(commits)
    assert len(problems) == 2
    assert "aaa1111" in problems[0]
    assert "ccc3333" in problems[1]


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Isolate from the user's git config (hooks, signing, autocrlf).
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@example.com")
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    monkeypatch.chdir(root)
    return root


def test_main_passes_a_pr_whose_commits_are_each_one_kind(repo: Path) -> None:
    # The base commit itself is mixed, but it isn't part of the PR (base..head).
    base = _commit(repo, "base", {"tests/test_a.py": "x\n", "ingest/a.py": "x\n"})
    _commit(repo, "stubs", {"ingest/a.py": "y\n"})
    _commit(repo, "red", {"tests/test_a.py": "y\n"})
    head = _commit(repo, "green", {"ingest/a.py": "z\n"})
    assert main([base, head]) == 0


def test_main_fails_a_pr_with_a_mixed_commit(repo: Path) -> None:
    base = _commit(repo, "base", {"README.md": "x\n"})
    _commit(repo, "red", {"tests/test_a.py": "y\n"})
    head = _commit(repo, "sneaky", {"tests/test_a.py": "z\n", "ingest/a.py": "z\n"})
    assert main([base, head]) != 0


def test_main_counts_both_sides_of_a_move_out_of_tests(repo: Path) -> None:
    # Moving a test file into code deletes a test path and adds a non-test path:
    # the commit changes both kinds, so it's mixed.
    base = _commit(repo, "base", {"tests/test_a.py": "def test_x(): ...\n"})
    (repo / "ingest").mkdir()
    _git(repo, "mv", "tests/test_a.py", "ingest/a.py")
    head = _commit(repo, "move", {})
    assert main([base, head]) != 0
