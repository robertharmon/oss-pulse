# ingest/

The hourly ingest service (Cloud Run): download one GH Archive hour, validate it with Great Expectations, write Zstandard Parquet to GCS, load it into `raw_gharchive_events`, and append a `raw_ingest_audit` row.

Stages follow `s<N>_<subject>_<input>_to_<output>.py` (CONVENTIONS §1). Spec: `docs/data_contract.md` §3–§4. Built in roadmap M3.
