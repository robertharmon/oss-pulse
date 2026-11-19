"""Failure-mode coverage check (backlog B11, ADR 0002 §5, data contract §1).

Reads:  docs/data_contract.md (the FM-nn, R-nn and M-nn tables), test files
        (pytest markers, dbt `tags`), and scripts/coverage_baseline.txt.
Fails:  if a live ID has no test and isn't on the baseline, or if the
        baseline lists an ID that now has a test, or that isn't live. The
        baseline can only shrink; v1 requires it to be empty.
"""

import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "docs" / "data_contract.md"
BASELINE_PATH = REPO_ROOT / "scripts" / "coverage_baseline.txt"
TEST_GLOBS = ("tests/**/*.py", "dbt/tests/**/*.sql", "dbt/**/*.yml")

_ID = r"(?:FM|R|M)-\d{2}"
# A definition is a table row whose first cell is the ID.
_ROW = re.compile(rf"^\|\s*({_ID})\s*\|(.*)$", re.MULTILINE)
_MARKER = re.compile(rf"""\.(?:failure_mode|metamorphic)\(\s*["']({_ID})["']""")
_TAGS = re.compile(r"tags\s*[:=]\s*\[([^\]]*)\]")
_ID_IN_TAGS = re.compile(rf"\b({_ID})\b")
# Status markers are italic (single asterisk): `*retired*`, `*Pending: …*`.
# Bold words like `**pending**` are prose, not markers.
_RETIRED = re.compile(r"(?<!\*)\*retired\*(?!\*)", re.IGNORECASE)
_PENDING = re.compile(r"(?<!\*)\*pending:", re.IGNORECASE)


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


def find_covered_ids(files: Iterable[tuple[Path, str]]) -> set[str]:
    """IDs referenced by a pytest marker or a dbt `tags` list in the given files."""
    covered: set[str] = set()
    for path, text in files:
        if path.suffix == ".py":
            covered.update(_MARKER.findall(text))
        else:
            for tag_list in _TAGS.findall(text):
                covered.update(_ID_IN_TAGS.findall(tag_list))
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


def _test_files() -> list[tuple[Path, str]]:
    seen: set[Path] = set()
    files: list[tuple[Path, str]] = []
    for pattern in TEST_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path in seen or "dbt_packages" in path.parts:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            files.append((path.relative_to(REPO_ROOT), text))
    return files


def main() -> int:
    ids = parse_contract_ids(CONTRACT_PATH.read_text(encoding="utf-8"))
    covered = find_covered_ids(_test_files())
    baseline = parse_baseline(BASELINE_PATH.read_text(encoding="utf-8"))
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
