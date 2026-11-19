"""No-mixed-commits check (backlog B11, ways of working §3.1).

Reads:  the commits between a PR's base and head (`git rev-list`), and the
        paths each one changes.
Fails:  if any commit changes both a test path and a non-test path. Test
        paths are listed explicitly in ways of working §3.1.

Usage:  python -m scripts.check_commit_paths <base-sha> <head-sha>
"""

import fnmatch
import shutil
import subprocess
import sys
from collections.abc import Iterable

TEST_PATH_PATTERNS: tuple[str, ...] = (
    "tests/**",
    "dbt/tests/**",
    "dbt/models/**/_unit_tests.yml",
    "terraform/tests/**",
)


def _matches(path: str, pattern: str) -> bool:
    # fnmatch's `*` already crosses `/`, so "tests/**" means "anything under
    # tests/". A `**/` can also match no folder at all, as in a glob.
    if fnmatch.fnmatchcase(path, pattern):
        return True
    return "**/" in pattern and fnmatch.fnmatchcase(path, pattern.replace("**/", "", 1))


def is_test_path(path: str) -> bool:
    return any(_matches(path, pattern) for pattern in TEST_PATH_PATTERNS)


def classify_commit(paths: Iterable[str]) -> str:
    """'test', 'code', 'mixed', or 'empty'."""
    kinds = {"test" if is_test_path(p) else "code" for p in paths}
    if not kinds:
        return "empty"
    return kinds.pop() if len(kinds) == 1 else "mixed"


def evaluate(commits: Iterable[tuple[str, list[str]]]) -> list[str]:
    """One problem per mixed commit, given (sha, changed paths) pairs."""
    problems = []
    for sha, paths in commits:
        if classify_commit(paths) == "mixed":
            tests = sorted(p for p in paths if is_test_path(p))
            code = sorted(p for p in paths if not is_test_path(p))
            problems.append(
                f"commit {sha[:12]} mixes test paths {tests} with non-test paths {code}"
            )
    return problems


def _git(*args: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git not found on PATH")
    return subprocess.run(  # noqa: S603 - fixed git argv, no shell
        [git, *args], check=True, capture_output=True, text=True
    ).stdout


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: check_commit_paths <base-sha> <head-sha>", file=sys.stderr)
        return 2
    base, head = args
    shas = _git("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split()
    commits = [
        (sha, _git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).split())
        for sha in shas
    ]
    problems = evaluate(commits)
    print(f"{len(commits)} commits checked")
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
