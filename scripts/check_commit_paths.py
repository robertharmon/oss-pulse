"""No-mixed-commits check (backlog B11, ways of working §3.1).

Reads:  the commits between a PR's base and head (`git rev-list`), and the
        paths each one changes.
Fails:  if any commit changes both a test path and a non-test path. Test
        paths are listed explicitly in ways of working §3.1.
"""

from collections.abc import Iterable

TEST_PATH_PATTERNS: tuple[str, ...] = (
    "tests/**",
    "dbt/tests/**",
    "dbt/models/**/_unit_tests.yml",
    "terraform/tests/**",
)


def is_test_path(path: str) -> bool:
    raise NotImplementedError


def classify_commit(paths: Iterable[str]) -> str:
    """'test', 'code', 'mixed', or 'empty'."""
    raise NotImplementedError


def evaluate(commits: Iterable[tuple[str, list[str]]]) -> list[str]:
    """One problem per mixed commit, given (sha, changed paths) pairs."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
