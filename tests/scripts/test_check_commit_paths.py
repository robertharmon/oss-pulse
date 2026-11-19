import pytest

from scripts.check_commit_paths import classify_commit, evaluate, is_test_path


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
