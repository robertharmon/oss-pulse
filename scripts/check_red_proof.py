"""Red-proof check (backlog B11, ways of working §3.1, ADR 0002 §5).

Reads:  a PR's commits (base..head), its changed Python test files at base
        and at head, and a pytest JUnit report produced by running the head
        versions of those tests against the code of the stubs commit.
Fails:  if any test function the PR adds or changes doesn't fail, in the
        test body, against the stubs: a pass, a skip, an import or setup
        error all count as "not red". The stubs commit is the parent of the
        PR's first tests-only commit.

Usage:  python -m scripts.check_red_proof <base-sha> <head-sha>
"""

from collections.abc import Iterable, Sequence


def changed_test_functions(base_source: str | None, head_source: str) -> set[str]:
    """Names of test functions (``test_*``, incl. ``Class::test_*``) that are new or
    whose source differs between the base and head versions of one test file."""
    raise NotImplementedError


def find_stubs_commit(
    commits: Sequence[tuple[str, str, list[str]]],
) -> str | None:
    """Given (sha, parent_sha, changed paths) in order, the parent of the first
    commit whose paths are all Python test files, or None if there's none."""
    raise NotImplementedError


def evaluate_report(junit_xml: str, targets: Iterable[str]) -> list[str]:
    """Problems for targets (``path::name``) that weren't red in the JUnit report.

    Red means every case of the test failed with AssertionError,
    NotImplementedError or pytest's ``Failed`` (DID NOT RAISE), and at least
    one case ran. Errors, skips, passes and missing tests are problems.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
