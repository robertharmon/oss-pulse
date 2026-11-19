"""Red-proof check (backlog B11, ways of working §3.1, ADR 0002 §5).

Reads:  a PR's commits (base..head), its changed Python test files at base
        and at head, and a pytest JUnit report produced by running the head
        versions of those tests against the code of the stubs commit.
Fails:  if any test function the PR adds or changes doesn't fail, in the
        test body, against the stubs: a pass, a skip, an import or setup
        error all count as "not red". The stubs commit is the parent of the
        PR's first tests-only commit (all paths are test paths, at least one
        a Python test file).

Usage:  python -m scripts.check_red_proof <base-sha> <head-sha>
"""

import ast
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from pathlib import Path

from scripts.check_commit_paths import is_test_path

# How pytest's JUnit report words a failure raised in the test body that
# proves behavior: a plain `assert` ("assert x == y"), an assert with a
# message ("AssertionError: ..."), a stub ("NotImplementedError") or
# pytest.raises that didn't raise ("Failed: DID NOT RAISE ...").
_RED_PREFIXES = (
    "assert ",
    "AssertionError",
    "NotImplementedError",
    "Failed: DID NOT RAISE",
)


def _test_functions(source: str) -> dict[str, str]:
    """Map test names (``test_x`` or ``TestC::test_x``) to a dump of their AST."""
    found: dict[str, str] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("test"):
                found[node.name] = ast.dump(node)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for item in node.body:
                if isinstance(
                    item, ast.FunctionDef | ast.AsyncFunctionDef
                ) and item.name.startswith("test"):
                    found[f"{node.name}::{item.name}"] = ast.dump(item)
    return found


def changed_test_functions(base_source: str | None, head_source: str) -> set[str]:
    """Names of test functions (``test_*``, incl. ``Class::test_*``) that are new or
    whose source differs between the base and head versions of one test file."""
    base = _test_functions(base_source) if base_source is not None else {}
    head = _test_functions(head_source)
    return {name for name, dump in head.items() if base.get(name) != dump}


def _is_python_test(path: str) -> bool:
    return is_test_path(path) and path.endswith(".py")


def find_stubs_commit(
    commits: Sequence[tuple[str, str, list[str]]],
) -> str | None:
    """Given (sha, parent_sha, changed paths) in order, the parent of the first
    commit whose paths are all test paths, at least one a Python test file;
    or None if there's none."""
    for _sha, parent, paths in commits:
        if (
            paths
            and all(is_test_path(p) for p in paths)
            and any(map(_is_python_test, paths))
        ):
            return parent
    return None


def evaluate_report(junit_xml: str, targets: Iterable[str]) -> list[str]:
    """Problems for targets (``path::name``) that weren't red in the JUnit report.

    Red means every case of the test failed with AssertionError,
    NotImplementedError or pytest's ``Failed`` (DID NOT RAISE), and at least
    one case ran. Errors, skips, passes and missing tests are problems.
    """
    cases = list(ET.fromstring(junit_xml).iter("testcase"))  # noqa: S314 - own report
    problems = []
    for target in targets:
        path, _, qualname = target.partition("::")
        cls, _, func = qualname.rpartition("::")
        classname = path.removesuffix(".py").replace("/", ".") + (
            f".{cls}" if cls else ""
        )
        matching = [
            c
            for c in cases
            if c.get("classname") == classname
            and c.get("name", "").split("[")[0] == func
        ]
        if not matching:
            problems.append(f"{target}: not found in the run against the stubs commit")
            continue
        for case in matching:
            failure = case.find("failure")
            message = failure.get("message", "") if failure is not None else ""
            if failure is None or not message.startswith(_RED_PREFIXES):
                outcome = _describe(case)
                name = case.get("name")
                problems.append(
                    f"{target} [{name}]: not red against the stubs ({outcome})"
                )
    return problems


def _describe(case: ET.Element) -> str:
    for tag in ("error", "skipped", "failure"):
        element = case.find(tag)
        if element is not None:
            return f"{tag}: {element.get('message', '')[:120]}"
    return "passed"


def _exe(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH")
    return path


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(  # noqa: S603 - fixed git argv, no shell
        [_exe("git"), *args], check=True, capture_output=True, text=True, cwd=cwd
    ).stdout


def _file_at(ref: str, path: str) -> str | None:
    result = subprocess.run(  # noqa: S603 - fixed git argv, no shell
        [_exe("git"), "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: check_red_proof <base-sha> <head-sha>", file=sys.stderr)
        return 2
    base, head = args
    shas = _git("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split()
    commits = [
        (
            sha,
            _git("rev-parse", f"{sha}^").strip(),
            _git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).split(),
        )
        for sha in shas
    ]
    changed = _git("diff", "--name-only", "--diff-filter=AM", base, head).split()
    test_files = [
        p for p in changed if _is_python_test(p) and Path(p).name.startswith("test")
    ]
    targets = sorted(
        f"{path}::{name}"
        for path in test_files
        for name in changed_test_functions(
            _file_at(base, path), _file_at(head, path) or ""
        )
    )
    if not targets:
        print("No new or changed Python tests in this PR; nothing to prove red.")
        return 0
    stubs = find_stubs_commit(commits)
    if stubs is None:
        print("::error::The PR changes tests but no tests-only commit proves them red.")
        return 1
    print(f"Proving {len(targets)} tests red against stubs commit {stubs[:12]}")
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "stubs"
        _git("worktree", "add", "--detach", str(tree), stubs)
        try:
            for path in test_files:
                target_file = tree / path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(_file_at(head, path) or "", encoding="utf-8")
            report = Path(tmp) / "red.xml"
            subprocess.run(  # noqa: S603 - fixed argv; runs the PR's own tests
                [
                    _exe("uv"),
                    "run",
                    "--frozen",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    f"--junitxml={report}",
                    *test_files,
                ],
                cwd=tree,
                check=False,
            )
            problems = evaluate_report(report.read_text(encoding="utf-8"), targets)
        finally:
            _git("worktree", "remove", "--force", str(tree))
    for problem in problems:
        print(f"::error::{problem}")
    print(f"{len(targets) - len(problems)} of {len(targets)} proven red")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
