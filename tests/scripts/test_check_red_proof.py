import subprocess
import sys
from pathlib import Path

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


# --- Audit additions (spec: module and function docstrings, ways of working §3.1)

BASE_2 = """import pytest


async def test_async_kept() -> None:
    assert True


async def test_async_edited() -> None:
    assert 1 == 1


def test_removed() -> None:
    assert True


class TestA:
    def test_same(self) -> None:
        assert True


class TestB:
    def test_same(self) -> None:
        assert True
"""

HEAD_2 = """import pytest


async def test_async_kept() -> None:
    assert True


async def test_async_edited() -> None:
    assert 1 == 2


async def test_async_new() -> None:
    assert False


class TestA:
    def test_same(self) -> None:
        assert True


class TestB:
    def test_same(self) -> None:
        assert False
"""


def test_async_tests_and_same_named_methods_are_tracked_separately() -> None:
    # The removed test isn't a target: there's nothing at head to prove red.
    assert changed_test_functions(BASE_2, HEAD_2) == {
        "test_async_edited",
        "test_async_new",
        "TestB::test_same",
    }


def test_a_changed_decorator_changes_the_test() -> None:
    base = (
        "import pytest\n\n\n"
        '@pytest.mark.parametrize("x", [1, 2])\n'
        "def test_p(x: int) -> None:\n"
        "    assert x > 0\n"
    )
    head = base.replace("[1, 2]", "[1, 2, -1]")
    assert changed_test_functions(base, head) == {"test_p"}


def test_a_python_file_outside_the_test_paths_doesnt_start_the_red_phase() -> None:
    commits = [
        ("c1", "c0", ["scripts/test_helpers.py"]),
        ("c2", "c1", ["ingest/tests/test_x.py"]),
        ("c3", "c2", ["tests/ingest/test_x.py"]),
    ]
    assert find_stubs_commit(commits) == "c2"


def test_a_test_name_doesnt_match_cases_of_a_longer_name() -> None:
    report = _report(
        _case("test_a"),
        _case("test_a_extra", ASSERT),
        _case("test_ab[1]", ASSERT),
    )
    problems = evaluate_report(report, ["tests/scripts/test_a.py::test_a"])
    assert len(problems) == 1
    assert "test_a" in problems[0]
    report = _report(_case("test_ab", ASSERT))
    assert len(evaluate_report(report, ["tests/scripts/test_a.py::test_a"])) == 1


def test_a_same_named_test_in_another_file_doesnt_count() -> None:
    report = _report(_case("test_x", ASSERT, classname="tests.scripts.test_b"))
    problems = evaluate_report(report, ["tests/scripts/test_a.py::test_x"])
    assert len(problems) == 1


REAL_TESTS = """import pytest


def test_assert():
    assert 1 == 2


def test_not_implemented():
    raise NotImplementedError


def test_did_not_raise():
    with pytest.raises(ValueError):
        pass


@pytest.mark.parametrize("x", [1, 2])
def test_all_cases_red(x):
    assert x == 0


class TestGroup:
    def test_method(self):
        assert False


def test_other_exception():
    raise KeyError("k")


def test_passes():
    pass


@pytest.fixture
def broken():
    raise RuntimeError("setup")


def test_setup_error(broken):
    assert False


@pytest.mark.parametrize("x", [1, 2])
def test_one_case_green(x):
    assert x == 1


@pytest.mark.xfail(strict=True)
def test_strict_xpass():
    pass
"""


def test_reads_a_junit_report_that_pytest_really_wrote(tmp_path: Path) -> None:
    # Real reports differ from hand-written ones: an assertion failure's message
    # is "assert 1 == 2", with no "AssertionError" in it.
    test_file = tmp_path / "tests" / "scripts" / "test_real.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(REAL_TESTS)
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    report = tmp_path / "report.xml"
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            f"--rootdir={tmp_path}",
            f"--junitxml={report}",
            "tests/scripts/test_real.py",
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    prefix = "tests/scripts/test_real.py::"
    red = [
        "test_assert",
        "test_not_implemented",
        "test_did_not_raise",
        "test_all_cases_red",
        "TestGroup::test_method",
    ]
    not_red = [
        "test_other_exception",
        "test_passes",
        "test_setup_error",
        "test_one_case_green",
        "test_strict_xpass",
    ]
    xml = report.read_text()
    assert evaluate_report(xml, [prefix + name for name in red]) == []
    problems = evaluate_report(xml, [prefix + name for name in not_red])
    assert len(problems) == len(not_red)
    for name, problem in zip(not_red, problems, strict=True):
        assert name in problem
