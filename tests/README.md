# tests/

Python tests for ingest, the dashboard, the kill switch and the verifier scripts, run with pytest.

Layout mirrors the code (`tests/ingest/`, `tests/scripts/`, …). `tests/fixtures/` holds input data and `tests/expected/` hand-computed outputs; both are CODEOWNERS-protected. `tests/metamorphic/` holds M-nn tests, `tests/adversarial/` the red-team's. Test paths are listed in `docs/ways_of_working.md` §3.1.
