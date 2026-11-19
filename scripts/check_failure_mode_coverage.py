"""Failure-mode coverage check (backlog B11, ADR 0002 §5, data contract §1).

Reads:  docs/data_contract.md (the FM-nn, R-nn and M-nn tables), test files
        (pytest markers, dbt `tags`), and scripts/coverage_baseline.txt.
Fails:  if a live ID has no test and isn't on the baseline, or if the
        baseline lists an ID that now has a test, or that isn't live. The
        baseline can only shrink; v1 requires it to be empty.
"""

from collections.abc import Iterable
from pathlib import Path


def parse_contract_ids(contract_text: str) -> dict[str, str]:
    """Map each FM/R/M ID in the contract's tables to 'live', 'pending' or 'retired'."""
    raise NotImplementedError


def find_covered_ids(files: Iterable[tuple[Path, str]]) -> set[str]:
    """IDs referenced by a pytest marker or a dbt `tags` list in the given files."""
    raise NotImplementedError


def parse_baseline(baseline_text: str) -> set[str]:
    """IDs listed in the baseline file, ignoring blank lines and `#` comments."""
    raise NotImplementedError


def evaluate(ids: dict[str, str], covered: set[str], baseline: set[str]) -> list[str]:
    """Return one human-readable problem per violation; empty means pass."""
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
