"""Failure-mode coverage check (backlog B11, ADR 0002 §5, data contract §1).

Reads:  docs/data_contract.md (the FM-nn, R-nn and M-nn tables), test files
        (pytest markers, dbt `tags`), and scripts/coverage_baseline.txt, all
        relative to the current directory (run it from the repo root).
Fails:  if a live ID has no test and isn't on the baseline, or if the
        baseline lists an ID that now has a test, or that isn't live. The
        baseline can only shrink; v1 requires it to be empty.
"""

import ast
import re
import sys
import textwrap
from collections.abc import Iterable
from pathlib import Path

CONTRACT = Path("docs") / "data_contract.md"
BASELINE = Path("scripts") / "coverage_baseline.txt"
TEST_GLOBS = ("tests/**/*.py", "dbt/tests/**/*.sql", "dbt/**/*.yml")
_MARKER_NAMES = frozenset({"failure_mode", "metamorphic"})

_ID = r"(?:FM|R|M)-\d{2}"
_ID_ONLY = re.compile(rf"^{_ID}$")
# A definition is a table row whose first cell is the ID.
_ROW = re.compile(rf"^\|\s*({_ID})\s*\|(.*)$", re.MULTILINE)
_ID_ANYWHERE = re.compile(rf"\b({_ID})\b")
_DECORATOR_MARKER = re.compile(
    rf"""^\s*@pytest\.mark\.(?:failure_mode|metamorphic)\(\s*["']({_ID})["']""",
    re.MULTILINE,
)
# Status markers are italic (single asterisk): `*retired*`, `*Pending: …*`,
# `*pending*`. Bold words like `**pending**` are prose, not markers.
_RETIRED = re.compile(r"(?<!\*)\*retired\b(?!\*\*)", re.IGNORECASE)
_PENDING = re.compile(r"(?<!\*)\*pending\b(?!\*\*)", re.IGNORECASE)
# dbt: `tags=[...]` in SQL config, `tags: [...]` inline in YAML.
_INLINE_TAGS = re.compile(r"tags\s*[:=]\s*\[([^\]]*)\]")
_BLOCK_TAGS = re.compile(r"^(\s*)tags:\s*$")
_BLOCK_ITEM = re.compile(r"^(\s*)-\s*['\"]?([^'\"\s#]+)")
_YAML_COMMENT = re.compile(r"(^|\s)#.*$")


def parse_contract_ids(contract_text: str) -> dict[str, str]:
    """Map each FM/R/M ID in the contract's tables to 'live', 'pending' or 'retired'."""
    ids: dict[str, str] = {}
    for match in _ROW.finditer(contract_text):
        rest = match.group(2)
        if _RETIRED.search(rest):
            status = "retired"
        elif _PENDING.search(rest):
            status = "pending"
        else:
            status = "live"
        ids[match.group(1)] = status
    return ids


def _is_pytest_marker(func: ast.expr) -> bool:
    """True for `pytest.mark.failure_mode` / `pytest.mark.metamorphic`."""
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _MARKER_NAMES
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "mark"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "pytest"
    )


def _python_markers(source: str) -> set[str]:
    # Walking the syntax tree finds markers wherever they're applied
    # (decorators, `pytestmark`, `pytest.param(marks=...)`) and never inside
    # string literals. Source that doesn't parse (a fragment, or a file with a
    # syntax error, which pytest would reject anyway) falls back to matching
    # decorator lines, so a typo elsewhere doesn't hide the file's coverage.
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return set(_DECORATOR_MARKER.findall(source))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_pytest_marker(node.func)):
            continue
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.update(_ID_ONLY.findall(first.value))
    return found


def _dbt_tags(text: str) -> set[str]:
    lines = [_YAML_COMMENT.sub("", line) for line in text.splitlines()]
    found: set[str] = set()
    for tag_list in _INLINE_TAGS.findall("\n".join(lines)):
        found.update(_ID_ANYWHERE.findall(tag_list))
    for index, line in enumerate(lines):
        block = _BLOCK_TAGS.match(line)
        if block is None:
            continue
        for item_line in lines[index + 1 :]:
            item = _BLOCK_ITEM.match(item_line)
            if item is None or len(item.group(1)) <= len(block.group(1)):
                break
            if _ID_ONLY.match(item.group(2)):
                found.add(item.group(2))
    return found


def find_covered_ids(files: Iterable[tuple[Path, str]]) -> set[str]:
    """IDs referenced by a pytest marker or a dbt `tags` list in the given files."""
    covered: set[str] = set()
    for path, text in files:
        covered |= _python_markers(text) if path.suffix == ".py" else _dbt_tags(text)
    return covered


def parse_baseline(baseline_text: str) -> set[str]:
    """IDs listed in the baseline file, ignoring blank lines and `#` comments."""
    entries = (line.split("#", 1)[0].strip() for line in baseline_text.splitlines())
    return {entry for entry in entries if entry}


def evaluate(ids: dict[str, str], covered: set[str], baseline: set[str]) -> list[str]:
    """Return one human-readable problem per violation; empty means pass."""
    live = {i for i, status in ids.items() if status == "live"}
    problems = [
        f"{i}: live in the contract but has no test and isn't on the baseline"
        for i in sorted(live - covered - baseline)
    ]
    problems += [
        f"{i}: has a test now; remove it from scripts/coverage_baseline.txt"
        for i in sorted(baseline & covered & live)
    ]
    problems += [
        f"{i}: on the baseline but not a live contract ID"
        for i in sorted(baseline - live)
    ]
    problems += [
        f"{i}: referenced by a test but not defined in the contract"
        for i in sorted(covered - set(ids))
    ]
    return problems


def _test_files(root: Path) -> list[tuple[Path, str]]:
    seen: set[Path] = set()
    files: list[tuple[Path, str]] = []
    for pattern in TEST_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path in seen or "dbt_packages" in path.parts:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            files.append((path.relative_to(root), text))
    return files


def main() -> int:
    root = Path.cwd()
    ids = parse_contract_ids((root / CONTRACT).read_text(encoding="utf-8"))
    covered = find_covered_ids(_test_files(root))
    baseline = parse_baseline((root / BASELINE).read_text(encoding="utf-8"))
    problems = evaluate(ids, covered, baseline)
    live = sum(1 for status in ids.values() if status == "live")
    print(
        f"{live} live IDs, {len(covered & set(ids))} covered, "
        f"{len(baseline)} on the baseline"
    )
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
