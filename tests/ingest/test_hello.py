import pytest

from osp_ingest.hello import gharchive_hour_url


@pytest.mark.parametrize(
    ("hour", "expected_suffix"),
    [
        ("2026-11-10-00", "2026-11-10-0.json.gz"),
        ("2026-11-10-05", "2026-11-10-5.json.gz"),
        ("2026-11-10-09", "2026-11-10-9.json.gz"),
        ("2026-11-10-10", "2026-11-10-10.json.gz"),
        ("2026-11-10-23", "2026-11-10-23.json.gz"),
    ],
)
def test_url_uses_unpadded_hour(hour: str, expected_suffix: str) -> None:
    assert gharchive_hour_url(hour) == f"https://data.gharchive.org/{expected_suffix}"


@pytest.mark.parametrize("bad", ["2026-11-10-24", "2026-11-10-xx", "2026-11-10", "05"])
def test_rejects_malformed_hours(bad: str) -> None:
    with pytest.raises(ValueError, match="not a YYYY-MM-DD-HH hour"):
        gharchive_hour_url(bad)
