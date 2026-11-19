from pathlib import Path

from scripts.check_failure_mode_coverage import (
    evaluate,
    find_covered_ids,
    parse_baseline,
    parse_contract_ids,
)

CONTRACT = """
| ID | Failure | Signal | Handling |
|---|---|---|---|
| FM-01 | **Missing hour** | 404 | Retry. |
| FM-02 | **Gone** | x | *retired* 2026-12-01: merged into FM-01. |
| FM-16 | **Lookup** | 429 | *Pending: spec in the M4 language ADR.* |

| ID | Statement |
|---|---|
| R-01 | Lines read equal rows loaded. |

| ID | Change to the input | Expected output |
|---|---|---|
| M-03 | Relabel actors | Gini unchanged. |

Prose mentioning FM-99 outside a table row is not an ID definition.
"""


def test_parses_ids_with_status() -> None:
    assert parse_contract_ids(CONTRACT) == {
        "FM-01": "live",
        "FM-02": "retired",
        "FM-16": "pending",
        "R-01": "live",
        "M-03": "live",
    }


def test_bold_words_in_a_row_are_not_status_markers() -> None:
    text = (
        "| R-07 | Each hour is **succeeded**, **pending** or **retired**. |\n"
        "| FM-30 | A **Pending:** label in bold | x | y |\n"
    )
    assert parse_contract_ids(text) == {"R-07": "live", "FM-30": "live"}


def test_finds_pytest_markers_and_dbt_tags() -> None:
    files = [
        (
            Path("tests/ingest/test_x.py"),
            '@pytest.mark.failure_mode("FM-01")\ndef test_a(): ...',
        ),
        (Path("tests/metamorphic/test_y.py"), "@pytest.mark.metamorphic('M-03')\n"),
        (Path("dbt/tests/r01.sql"), "{{ config(tags=['R-01', 'nightly']) }}\nselect 1"),
        (Path("dbt/models/x/_unit_tests.yml"), "    config:\n      tags: [FM-10]\n"),
    ]
    assert find_covered_ids(files) == {"FM-01", "M-03", "R-01", "FM-10"}


def test_ignores_ids_outside_markers_and_tags() -> None:
    files = [(Path("tests/test_z.py"), "# see FM-01 and R-01 in the contract\n")]
    assert find_covered_ids(files) == set()


def test_parse_baseline_skips_comments_and_blanks() -> None:
    text = "# uncovered IDs\nFM-01\n\n  R-01  # balancing count, M4\n"
    assert parse_baseline(text) == {"FM-01", "R-01"}


def test_passes_when_every_live_id_is_covered_or_baselined() -> None:
    ids = {"FM-01": "live", "R-01": "live", "FM-16": "pending", "FM-02": "retired"}
    assert evaluate(ids, covered={"FM-01"}, baseline={"R-01"}) == []


def test_fails_on_live_id_with_no_test_and_no_baseline_entry() -> None:
    problems = evaluate({"FM-01": "live"}, covered=set(), baseline=set())
    assert len(problems) == 1
    assert "FM-01" in problems[0]


def test_fails_when_baselined_id_is_now_covered() -> None:
    problems = evaluate({"FM-01": "live"}, covered={"FM-01"}, baseline={"FM-01"})
    assert len(problems) == 1
    assert "FM-01" in problems[0]


def test_fails_when_baseline_lists_unknown_or_non_live_id() -> None:
    ids = {"FM-01": "live", "FM-02": "retired"}
    problems = evaluate(ids, covered={"FM-01"}, baseline={"FM-02", "FM-77"})
    assert len(problems) == 2


def test_fails_when_test_references_unknown_id() -> None:
    problems = evaluate({"FM-01": "live"}, covered={"FM-01", "FM-42"}, baseline=set())
    assert len(problems) == 1
    assert "FM-42" in problems[0]


def test_markers_inside_string_literals_are_not_coverage() -> None:
    source = (
        "files = [\n"
        "    (Path('t.py'), '@pytest.mark.failure_mode(\"FM-01\")'),\n"
        "    (Path('u.py'), \"x = '@pytest.mark.metamorphic(\\\"M-03\\\")'\"),\n"
        "]\n"
    )
    assert find_covered_ids([(Path("tests/scripts/test_meta.py"), source)]) == set()


def test_marker_on_a_decorator_line_is_coverage() -> None:
    source = '    @pytest.mark.failure_mode("FM-04")\n    def test_b() -> None: ...\n'
    assert find_covered_ids([(Path("tests/ingest/test_b.py"), source)]) == {"FM-04"}
