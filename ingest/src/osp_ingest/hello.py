"""Walking-skeleton module (backlog D1): proves lint, type check and tests run.

Replaced by the real ingest stages in roadmap M3.
"""

import re

_PROJECT_HOUR = re.compile(r"(\d{4}-\d{2}-\d{2})-(\d{2})")


def gharchive_hour_url(hour: str) -> str:
    """Return GH Archive's URL for a project hour string like ``2026-11-10-05``.

    The project writes hours zero-padded; GH Archive's URLs use the unpadded
    hour (data contract §3.1), so ``-05`` becomes ``-5``.
    """
    match = _PROJECT_HOUR.fullmatch(hour)
    if match is None or int(match.group(2)) > 23:
        raise ValueError(f"not a YYYY-MM-DD-HH hour: {hour!r}")
    return f"https://data.gharchive.org/{match.group(1)}-{int(match.group(2))}.json.gz"
