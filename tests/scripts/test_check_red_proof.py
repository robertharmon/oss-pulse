from scripts.check_red_proof import (
    changed_test_functions,
    evaluate_report,
    find_stubs_commit,
)

BASE = """import pytest


def helper() -> int:
    return 1


def test_kept() -> None:
    assert helper() == 1


def test_edited() -> None:
    assert 1 == 1


class TestGroup:
    def test_in_class(self) -> None:
        assert True
"""

HEAD = """import pytest


def helper() -> int:
    return 2


def test_kept() -> None:
    assert helper() == 1


def test_edited() -> None:
    assert 1 == 2


def test_new() -> None:
    assert False


class TestGroup:
    def test_in_class(self) -> None:
        assert True

    def test_new_method(self) -> None:
        assert False
"""


def test_changed_functions_are_new_or_edited_tests_only() -> None:
    assert changed_test_functions(BASE, HEAD) == {
        "test_edited",
        "test_new",
        "TestGroup::test_new_method",
    }


def test_every_test_in_a_new_file_is_changed() -> None:
    assert changed_test_functions(None, BASE) == {
        "test_kept",
        "test_edited",
        "TestGroup::test_in_class",
    }


def test_unchanged_file_has_no_changed_functions() -> None:
    assert changed_test_functions(BASE, BASE) == set()


def test_stubs_commit_is_parent_of_first_tests_only_commit() -> None:
    commits = [
        ("c1", "c0", ["docs/x.md"]),
        ("c2", "c1", ["scripts/a.py"]),
        ("c3", "c2", ["tests/scripts/test_a.py"]),
        ("c4", "c3", ["scripts/a.py"]),
        ("c5", "c4", ["tests/scripts/test_b.py"]),
    ]
    assert find_stubs_commit(commits) == "c2"


def test_no_tests_only_commit_means_no_stubs() -> None:
    assert find_stubs_commit([("c1", "c0", ["scripts/a.py"])]) is None


def test_non_python_test_paths_dont_start_the_red_phase() -> None:
    commits = [
        ("c1", "c0", ["tests/fixtures/hour.json.gz"]),
        ("c2", "c1", ["scripts/a.py"]),
        ("c3", "c2", ["tests/scripts/test_a.py"]),
    ]
    assert find_stubs_commit(commits) == "c2"


def _case(name: str, inner: str = "", classname: str = "tests.scripts.test_a") -> str:
    return f'<testcase classname="{classname}" name="{name}">{inner}</testcase>'


def _report(*cases: str) -> str:
    body = "".join(cases)
    return f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>'


ASSERT = '<failure message="AssertionError: assert 1 == 2">x</failure>'
NOT_IMPL = '<failure message="NotImplementedError">x</failure>'
NO_RAISE = (
    '<failure message="Failed: DID NOT RAISE &lt;class ValueError&gt;">x</failure>'
)


def test_assertion_not_implemented_and_did_not_raise_are_red() -> None:
    report = _report(
        _case("test_a", ASSERT),
        _case("test_b", NOT_IMPL),
        _case("test_c[1]", NO_RAISE),
        _case("test_c[2]", ASSERT),
    )
    targets = ["tests/scripts/test_a.py::test_a", "tests/scripts/test_a.py::test_b"]
    targets.append("tests/scripts/test_a.py::test_c")
    assert evaluate_report(report, targets) == []


def test_pass_error_skip_and_other_exceptions_are_not_red() -> None:
    report = _report(
        _case("test_pass"),
        _case("test_err", '<error message="ModuleNotFoundError: x">x</error>'),
        _case("test_skip", '<skipped message="skip">x</skipped>'),
        _case(
            "test_import", '<failure message="ImportError: cannot import">x</failure>'
        ),
    )
    names = ["test_pass", "test_err", "test_skip", "test_import"]
    targets = [f"tests/scripts/test_a.py::{n}" for n in names]
    problems = evaluate_report(report, targets)
    assert len(problems) == 4
    for name, problem in zip(names, problems, strict=True):
        assert name in problem


def test_one_green_parametrized_case_makes_the_test_not_red() -> None:
    report = _report(_case("test_p[1]", ASSERT), _case("test_p[2]"))
    problems = evaluate_report(report, ["tests/scripts/test_a.py::test_p"])
    assert len(problems) == 1


def test_target_missing_from_report_is_a_problem() -> None:
    problems = evaluate_report(_report(), ["tests/scripts/test_a.py::test_gone"])
    assert len(problems) == 1
    assert "test_gone" in problems[0]


def test_class_methods_match_by_class_and_name() -> None:
    report = _report(
        _case("test_m", ASSERT, classname="tests.scripts.test_a.TestGroup"),
        _case("test_m", "", classname="tests.scripts.test_a"),
    )
    assert evaluate_report(report, ["tests/scripts/test_a.py::TestGroup::test_m"]) == []
    assert len(evaluate_report(report, ["tests/scripts/test_a.py::test_m"])) == 1
