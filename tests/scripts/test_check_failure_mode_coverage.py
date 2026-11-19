from pathlib import Path

import pytest

from scripts.check_failure_mode_coverage import (
    evaluate,
    find_covered_ids,
    main,
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


# --- Audit additions (spec: data contract §1, module and function docstrings) --


def test_only_a_rows_first_cell_defines_an_id() -> None:
    text = (
        "| ID | Failure | Signal | Handling |\n"
        "|---|---|---|---|\n"
        "| FM-03 | **Transient** | 5xx | Treated as FM-77 by the retry. |\n"
        "| R-02 | Rows balance, see M-09. |\n"
    )
    assert parse_contract_ids(text) == {"FM-03": "live", "R-02": "live"}


def test_lowercase_pending_marker_from_contract_section_1() -> None:
    # Contract §1: "one whose spec isn't written yet is marked *pending* with
    # the item that will write it."
    text = "| M-08 | Shuffle hours | *pending*: roadmap M5 |\n"
    assert parse_contract_ids(text) == {"M-08": "pending"}


def test_module_level_pytestmark_is_coverage() -> None:
    files = [
        (
            Path("tests/ingest/test_m.py"),
            'import pytest\n\npytestmark = pytest.mark.failure_mode("FM-05")\n',
        ),
        (
            Path("tests/metamorphic/test_n.py"),
            "import pytest\n\npytestmark = [pytest.mark.metamorphic('M-02')]\n",
        ),
    ]
    assert find_covered_ids(files) == {"FM-05", "M-02"}


def test_stacked_markers_and_param_marks_are_all_coverage() -> None:
    source = (
        "import pytest\n\n\n"
        '@pytest.mark.failure_mode("FM-03")\n'
        '@pytest.mark.failure_mode("FM-04")\n'
        "@pytest.mark.parametrize(\n"
        '    "code",\n'
        '    [500, pytest.param(0, marks=pytest.mark.failure_mode("FM-05"))],\n'
        ")\n"
        "def test_download(code: int) -> None: ...\n"
    )
    found = find_covered_ids([(Path("tests/ingest/test_dl.py"), source)])
    assert found == {"FM-03", "FM-04", "FM-05"}


def test_dbt_tags_in_block_lists_and_double_quotes_are_coverage() -> None:
    files = [
        (
            Path("dbt/models/staging/_unit_tests.yml"),
            "unit_tests:\n  - name: dedup\n    config:\n      tags:\n"
            "        - FM-10\n        - nightly\n",
        ),
        (Path("dbt/tests/r02.sql"), '{{ config(tags=["R-02"]) }}\nselect 1\n'),
    ]
    assert find_covered_ids(files) == {"FM-10", "R-02"}


def test_ids_in_yaml_comments_are_not_coverage() -> None:
    text = "unit_tests:\n  - name: x\n    # tags: [FM-10] once FM-10 is specced\n"
    files = [(Path("dbt/models/x/_unit_tests.yml"), text)]
    assert find_covered_ids(files) == set()


def test_baseline_listing_a_pending_id_is_a_problem() -> None:
    # Module docstring: fails if the baseline lists an ID "that isn't live".
    ids = {"FM-01": "live", "FM-16": "pending"}
    problems = evaluate(ids, covered={"FM-01"}, baseline={"FM-16"})
    assert len(problems) == 1
    assert "FM-16" in problems[0]


def test_each_violation_is_its_own_problem_and_names_its_id() -> None:
    ids = {"FM-01": "live", "R-01": "live", "FM-02": "retired"}
    problems = evaluate(ids, covered=set(), baseline={"FM-02", "FM-77"})
    # FM-01 and R-01: live, untested, not baselined. FM-02: baselined but
    # retired. FM-77: baselined but not in the contract. 4 problems.
    assert len(problems) == 4
    for an_id in ["FM-01", "R-01", "FM-02", "FM-77"]:
        assert sum(an_id in p for p in problems) == 1


def _mini_repo(root: Path, baseline: str) -> None:
    files = {
        "docs/data_contract.md": (
            "| ID | Failure | Signal | Handling |\n|---|---|---|---|\n"
            "| FM-01 | **Missing hour** | 404 | Retry. |\n"
            "| FM-02 | **Late hour** | 404 then 200 | Retry. |\n"
            "| FM-16 | **Lookup** | 429 | *Pending: spec in the M4 ADR.* |\n\n"
            "| ID | Statement |\n|---|---|\n"
            "| R-01 | Lines read equal rows loaded. |\n"
        ),
        "tests/ingest/test_x.py": (
            'import pytest\n\n\n@pytest.mark.failure_mode("FM-01")\n'
            "def test_x() -> None: ...\n"
        ),
        "dbt/tests/r01.sql": "{{ config(tags=['R-01']) }}\nselect 1\n",
        "scripts/coverage_baseline.txt": baseline,
    }
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)


def test_main_passes_when_the_repo_is_covered_or_baselined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mini_repo(tmp_path, "# uncovered\nFM-02\n")
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_fails_when_a_live_id_is_neither_tested_nor_baselined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mini_repo(tmp_path, "# uncovered\n")
    monkeypatch.chdir(tmp_path)
    assert main() != 0
