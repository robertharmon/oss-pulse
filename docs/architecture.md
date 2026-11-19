# oss-pulse — Architecture

> How the pieces committed to in [ADR 0001](adr/0001-tech-stack.md) fit
> together. A reader of this doc should be able to trace a single
> GitHub event from GH Archive to a chart on the Streamlit dashboard
> without opening any other file.
>
> This doc describes the **target** architecture. None of it is built yet
> ([`roadmap.md`](roadmap.md)). Where a detail is still open, it says
> which document will decide it. When this doc and a more specific one
> disagree, the specific one wins: the [data contract](data_contract.md)
> for tables and failure modes, the [access matrix](access_matrix.md) for
> permissions, the [cost model](cost_model.md) for cadence and retention.

---

## 1. The system in one paragraph

Once an hour, a Cloud Scheduler job calls the **ingest** Cloud Run
service. Ingest downloads the previous hour's GH Archive file (one
gzipped file of line-delimited JSON, about 2–14 MB, holding every public
GitHub event for that hour), validates the batch with Great Expectations,
writes it to GCS as a Zstandard-compressed Parquet file, loads it into a
raw BigQuery table with a free load job, and records the attempt in an
audit table. Once a day, at 01:30 UTC, a second Scheduler job starts
the **dbt** Cloud Run job. It runs `dbt build` for yesterday, plus at most
four earlier days that changed or failed since their last build. Both run
as Cloud Run jobs ([ADR 0003](adr/0003-ingest-and-build-as-cloud-run-jobs.md)). That transforms
raw events through staging and core tables into four mart tables:
trending repos, language share, contributor concentration, and
time-of-day activity. A Streamlit app on Streamlit Community Cloud reads
the marts and renders one chart each, caching results for an hour. Any
`ERROR` log from either one fires a Slack alert. Prod resources are
defined in Terraform; the exceptions, which the author sets up by hand,
are listed in §2 under "Infra".

## 2. The diagram

```
                      ┌─────────────────────────────┐
                      │  https://data.gharchive.org │
                      │  public, no auth; one       │
                      │  .json.gz per hour, 2–14 MB │
                      │  live at :05 past the hour  │
                      └──────────────┬──────────────┘
                                     │ HTTPS GET (unpadded hour in URL)
                                     ▼
 ┌──────────────────┐ hourly  ┌──────────────────────────────────┐
 │ Cloud Scheduler  │────────▶│ Cloud Run: ingest                │
 │ job 1: ingest    │         │  1. fetch hour (+ retry missing  │
 │ (minute set by   │         │     hours from the last 24)      │
 │  the ingest ADR) │         │  2. validate (Great Expectations)│
 │                  │         │  3. write Parquet (Zstandard)    │
 │ job 2: dbt       │         │  4. load job → raw (hour, trunc.)│
 │ 01:30 UTC daily  │         │  5. append audit row (load job)  │
 └────────┬─────────┘         └──────┬──────────────┬────────────┘
          │ daily                    │ writes       │ loads
          │                          ▼              ▼
          │          ┌───────────────────────┐ ┌───────────────────────────┐
          │          │ GCS                   │ │ BigQuery osp_raw_<env>    │
          │          │ osp-raw-events-<env>  │ │  raw_gharchive_events     │
          │          │  gharchive/year=/     │ │   hourly partitions,      │
          │          │  month=/day=/hour=    │ │   clustered on repo_id,   │
          │          │ 14 days, soft delete  │ │   kept 3 days             │
          │          │ off (recovery copy)   │ │  raw_ingest_audit (kept)  │
          │          └───────────────────────┘ └─────────────┬─────────────┘
          │                                                  │ reads
          ▼                                                  │ (BigQuery only)
 ┌──────────────────────────────────┐                        │
 │ Cloud Run job: dbt               │◀───────────────────────┘
 │  `dbt build` for the build's     │
 │  window: yesterday + catch-up    │
 │  days (data contract §1)         │
 └──────────────┬───────────────────┘
                │ builds
                ▼
 ┌────────────────────────────────────────────────────────────┐
 │ BigQuery osp_staging_<env>                                 │
 │   stg_events (a view; latest successful attempt per hour,  │
 │   suppressions, dedupe), stg_repos, stg_actors             │
 │                         │                                  │
 │                         ▼                                  │
 │ BigQuery osp_analytics_<env>                               │
 │   fct_events (400 days), dim_repos, dim_actors (kept)      │
 │   mart_trending_repos, mart_contributor_concentration      │
 │     (daily snapshots on as_of_date, 30 days)               │
 │   mart_language_share, mart_time_of_day_activity           │
 └────────────────────────────┬───────────────────────────────┘
                              │ SELECT, once per chart per hour
                              │ (read-only key in Streamlit secrets)
                              ▼
 ┌────────────────────────────────────────────────────────────┐
 │ Streamlit Community Cloud: dashboard/app.py                │
 │   4 charts, 1 per mart; st.cache_data(ttl=3600)            │
 └────────────────────────────────────────────────────────────┘

 ─────────────────────────────── cross-cutting ───────────────────────────────

 Alerting:   any ERROR log from ingest or dbt → Cloud Logging log-based
             alert policy → Slack notification channel (created by hand,
             outside Terraform). CI failures on main/build/agentic → Slack
             through the `ci-alerts` GitHub environment's secret.

 Language:   a small lookup job fills dim_repos.primary_language from
             GitHub's API (weekly refresh). Its design and schedule are
             decided in the M4 language ADR.

 Infra:      Terraform defines prod's buckets, datasets, service accounts
             and grants, empty secret shells, ingest and dbt on Cloud Run,
             both Scheduler jobs, the alert policy, and the Artifact
             Registry repo with its cleanup policy. Set up by hand by the
             author instead (docs/author_setup.md): the GCP projects and
             billing; budgets, the kill-switch function, its Pub/Sub topic
             and its billing grants; the BigQuery query quotas; the
             Terraform state bucket; secret values; the Slack channel; the
             Streamlit app; and everything in dev (its bucket, datasets,
             builder and CI identities).

 Deploy:     no Dockerfile (DECISIONS §10). `gcloud run deploy --source`
             (`gcloud run jobs deploy --source` for ingest and dbt) has
             Cloud Build build each image with buildpacks and store it
             in Artifact Registry (keep the 2 newest). Deploys run from
             `main` only, through the author-approved `prod-deploy`
             GitHub environment.

 Spend:      both projects have a billing kill switch, a 10 GiB/day query
             quota and budget alerts (DECISIONS §1, cost model §7).
```

## 3. Component responsibilities

Each component has one job. If a change feels like it belongs to two,
that's a signal to re-read this section before writing it.

| Component | Owns | Does NOT own |
|---|---|---|
| **GH Archive** (external) | The source of truth for public GitHub events: one `.json.gz` per UTC hour, at `https://data.gharchive.org/<YYYY-MM-DD-H>.json.gz` with an **unpadded** hour. Measured: every hour probed has been present, live at `:05:03`–`:05:04`. | Any reliability promise. Missing or late hours are handled downstream (contract §3.3). |
| **Cloud Scheduler** | Two prod jobs: hourly ingest, daily dbt at 01:30 UTC. Calling each service with its identity. | Retries (the job's retry count is 0; ingest retries inside its own run) and any other logic. |
| **Cloud Run: ingest** | Fetching an hour (and retrying recent hours that have no success), validating it, writing Parquet to GCS, loading it into raw with `WRITE_TRUNCATE` on the hour, and appending one `raw_ingest_audit` row per attempt. Fails fast; follows the retry/alert rule in contract §3.3. | Transformation (dbt), scheduling (Scheduler), and triggering dbt. |
| **GCS: `osp-raw-events-<env>`** | The recovery copy of each hour's Parquet, laid out `gharchive/year=/month=/day=/hour=`. 14-day lifecycle (dev: 7), soft delete off. Reloading from it is a free load job. | Serving queries. |
| **BigQuery: `osp_raw_<env>`** | `raw_gharchive_events`: one row per GH Archive event as sent, with `payload` kept as JSON, partitioned by hour and clustered on `repo_id`, kept 3 days. `raw_ingest_audit`: one row per ingest attempt, kept. | Business logic, aggregation, deduplication. |
| **Cloud Run: dbt** | Running `dbt build` for the build's window (yesterday plus catch-up days, contract §1), with every test, once a day. Whether it's a Cloud Run service or job is decided in the ingest ADR. | Scheduling. Reading GCS (it reads raw through BigQuery only). |
| **BigQuery: `osp_staging_<env>`** | `stg_events`: each hour's latest successful attempt, with suppressed, out-of-range and duplicate rows dropped and counted, plus the extracted `payload_action`; kept 3 days. `stg_repos`, `stg_actors`. | Business metrics. |
| **BigQuery: `osp_analytics_<env>`** | `fct_events` (one row per event with boolean flags, 400 days), `dim_repos` and `dim_actors` (kept), and the four marts that answer the README's questions. | Raw event text. |
| **Language lookup** | Filling `dim_repos.primary_language` from GitHub's API. | Anything else. Details in the M4 language ADR. |
| **Streamlit app** | Four charts, one per mart. Loads each mart once per refresh, filters in pandas, caches an hour, shows "data unavailable" instead of a stack trace. | Transformation beyond chart-level filtering. If logic creeps in, it belongs in a mart. |
| **Secret Manager** (prod) | The record copy of the Slack webhook, and the language lookup's GitHub token. | The dashboard key, which lives only in Streamlit's secrets (`security.md` §3.1). Non-secret config. |
| **Cloud Logging + alert policy** | Turning any `ERROR` log from ingest or dbt into a Slack message. | Dashboards of ops metrics. |
| **Terraform** | Every GCP resource listed under "Infra" in §2. | What's listed there as outside it. |

## 4. Trace one record end-to-end

A single GitHub event, say a `WatchEvent` (a star) by actor `octocat` on
repo `octocat/hello-world` at `2026-10-05T14:23:17Z`, walks the pipeline
like this. The ingest minute is shown as `:15`, the likeliest choice; the
ingest ADR fixes it.

### 4.1 Birth (14:23:17 UTC)

GitHub's public events feed emits the event. GH Archive writes it as one
JSON line into the hour's file:

```json
{"id":"47301238871","type":"WatchEvent","actor":{"id":583231,"login":"octocat",...},
 "repo":{"id":1296269,"name":"octocat/hello-world","url":"..."},
 "payload":{"action":"started"},"public":true,"created_at":"2026-10-05T14:23:17Z"}
```

The file closes at 15:00 and goes live at about 15:05 as
`https://data.gharchive.org/2026-10-05-14.json.gz`.

### 4.2 Ingest (15:15 UTC)

The hourly Scheduler job calls ingest for hour `2026-10-05-14`. Ingest:

1. **Downloads** the file, converting the project's padded hour (`-14`)
   to GH Archive's unpadded form (the same for hours 10–23, different for
   0–9). It checks the bytes against `Content-Length`, and retries the
   download up to 3 times on a 5xx or a truncated file.
2. **Validates** the batch in memory with the Great Expectations suite:
   required fields present, every `created_at` inside hour 14, accepted
   types. A failure stops the hour here and logs `ERROR`.
3. **Writes** `gs://osp-raw-events-prod/gharchive/year=2026/month=10/day=05/hour=14.parquet`.
   Our event is one row: `event_id="47301238871"`, `event_type="WatchEvent"`,
   `actor_id=583231`, `repo_id=1296269`, `payload={"action":"started"}`,
   `created_at=2026-10-05 14:23:17`, `event_hour=2026-10-05 14:00`, and
   the attempt's `ingest_run_id`.
4. **Loads** the file into `osp_raw_prod.raw_gharchive_events`, partition
   `2026100514`, with `WRITE_TRUNCATE`, so a replay replaces the hour
   instead of duplicating it. The load is free.
5. **Records** the attempt in `raw_ingest_audit`: lines read = Parquet
   rows = rows loaded, outcome `success`.

### 4.3 Transform (next day, 01:30 UTC)

The daily Scheduler job calls dbt, which builds 2026-10-05 (and any
catch-up days):

1. **`stg_events`** reads hour 14's rows from its latest successful
   attempt, drops nothing for our event, and extracts
   `payload_action = 'started'`.
2. **`stg_repos`, `stg_actors`, then `dim_repos`, `dim_actors`** record
   (or update) `octocat/hello-world` and `octocat`.
3. **`fct_events`** gets one row with `is_star = true`.
4. **Marts** rebuild for `as_of_date = 2026-10-05`:
   - `mart_trending_repos`: `octocat/hello-world`'s `stars_7d` goes up
     by 1;
   - `mart_time_of_day_activity`: the (`primary_language` of
     hello-world, hour 14, `star`) cell goes up by 1;
   - `mart_language_share` and `mart_contributor_concentration`: no
     change (a star isn't a PR).
5. **Tests** run: uniqueness and relationships, the balancing counts
   (R-01…R-07), and freshness. Any failure exits non-zero, logs `ERROR`,
   and alerts; the marts keep their last good state. The one exception is
   a new event type (FM-07), which alerts without failing the build.

### 4.4 Serve (on the next page view)

The dashboard queries each mart once per hour at most. For the two
snapshot marts it asks for the newest partition by literal date
(2026-10-05 here); between midnight and the end of the daily build that
partition doesn't exist yet, so it falls back once to the day before
(FM-20). The other two marts have no date partition and are read whole.
It renders:
- **Trending repos this week:** hello-world's bar is 1 taller.
- **Time-of-day activity:** its cell is a little brighter.

**Latency:** an event becomes visible between about 1.5 hours later (one
created just before midnight UTC, built at 01:30) and about 25.5 hours
later (one created just after midnight, which waits for the next day's
build), plus up to an hour of dashboard cache. Our 14:23 star shows up
about 11 hours later. That's the
accepted price of a once-a-day build (cost model §4.2).

## 5. Data flow summary

| Stage | Interface | What crosses | Fail-fast check |
|---|---|---|---|
| 1. GH Archive → ingest | HTTPS GET | gzipped JSONL | 2xx; bytes = `Content-Length`; non-empty (FM-01, 03, 04, 05) |
| 2. Ingest validation | In memory | parsed events | Great Expectations suite (FM-06, 09, 12) |
| 3. Ingest → GCS | GCS write | Zstandard Parquet | Parquet rows = lines read (FM-14) |
| 4. GCS → raw | BigQuery load job | rows | `REQUIRED` schema; rows loaded = Parquet rows (FM-14) |
| 5. Raw → marts | `dbt build` (daily) | tables | Tests, balancing counts R-01…R-07 |
| 6. Marts → Streamlit | BigQuery `SELECT` | small result sets | Mart and partition exist, else "data unavailable" (FM-20) |

If ingest fails for an hour, the hour is retried on the next runs and
alerts per contract §3.3. A replay is a manual call to ingest for that hour
(RUNBOOK §3.1), and the next daily build catches its day up (FM-17). A
replay only works while the whole day is still in raw: ingest refuses a
day whose first hour is more than 70 hours old (FM-13); older days go
through the backfill path (ADR 0003 §3).

## 6. Failure boundaries

The full list, with IDs that tests reference, is
[contract §3.3 and §4.6](data_contract.md). In short:

| Failure | Stops at | How it's noticed | Recovery |
|---|---|---|---|
| Hour missing, late, truncated, or a 5xx (FM-01…05) | Ingest | 3rd failed scheduled attempt logs `ERROR` → Slack | Retried automatically; then a replay once GH Archive publishes (RUNBOOK §3.1–§3.2). An hour still unpublished a day later is lost, and each lost hour gets a RUNBOOK Part 2 entry. |
| Ingest stops running (Scheduler job paused or deleted) | Nowhere: nothing runs, so nothing logs `ERROR` | **Up to ~24h late:** the daily build's raw freshness test fails | Re-enable the job, then replay the gap. A metric-absence alert would close this gap (roadmap §6) |
| Bad content in a file (FM-06, 09, 12) | Ingest, before the load | `ERROR` on the first attempt → Slack | A PR fixing the data handling or the expectation, then a replay |
| Ingest killed mid-run (FM-18) | Ingest | Cloud Run's crash log → Slack | The hour has no success, so the next run retries it |
| dbt build or test failure (FM-19) | dbt | Non-zero exit → `ERROR` → Slack | Fix via PR (RUNBOOK §3.3); the next build catches the day up |
| New event type (FM-07) | Nowhere (doesn't block) | A warned test tagged `alert` → `ERROR` → Slack | Add the type to the contract's accepted list |
| Query quota exceeded (FM-15) | dbt or dashboard | `ERROR` → Slack; dashboard shows "data unavailable" | Wait for the reset; find what used the quota |
| Dashboard can't load a mart (FM-20) | Dashboard | "Data unavailable" to the viewer | RUNBOOK §3.6 |
| Spend over budget | Whole project | Kill switch unlinks billing; budget email | RUNBOOK §3.5 |

**Nothing retries without a record.** Ingest retries downloads and
recent hours on a fixed rule and records every attempt in
`raw_ingest_audit`; the daily build catches up days that changed or
failed, found from that same table.

## 7. Security boundaries

A summary. The authority is the [access matrix](access_matrix.md); the
policies are in the [security doc](security.md).

- **Each job has its own service account,** with grants only on what it
  touches:
  - ingest writes the bucket and the raw dataset;
  - dbt reads raw and writes staging and analytics, through BigQuery
    only, never GCS;
  - the Scheduler identity can only invoke ingest and dbt;
  - the dashboard identity reads `osp_analytics_<env>` and runs queries.
- **A per-user daily query quota** applies to every identity alike
  (dbt's included), set so a leaked dashboard key can't use up the day.
- **No key files, with one exception.** Cloud Run uses attached
  identities; GitHub Actions uses Workload Identity Federation pinned to
  the repo's numeric ID. The exception is the dashboard's read-only key,
  which lives only in Streamlit's secrets, because Streamlit Community
  Cloud can't use federation.
- **Prod is guarded outside IAM, too.** Terraform apply and deploys run
  only from `main`, through GitHub Environments that need the author's
  approval.
- **Agents have no prod credentials at all.** The build agent's bot
  identity reaches only BigQuery and one bucket in the dev project.
- **Humans:** the author is Owner of both projects (a solo project can't
  avoid that), and keeps that login off the agent's machine. There's no
  separate reviewer identity.
- **All pipeline data is public** (GH Archive). Handles are public but
  identifiable, so the dashboard shows aggregates and repo names, never
  individual actors (`security.md` §2.2).

## 8. What this doc doesn't cover

- **Why these tools:** [ADR 0001](adr/0001-tech-stack.md).
- **How agents build it, and the dev/prod split:** [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md).
- **Locked operating decisions:** [`DECISIONS.md`](../DECISIONS.md).
- **Tables, columns, failure modes, balancing counts:** [`data_contract.md`](data_contract.md).
- **Who can access what:** [`access_matrix.md`](access_matrix.md).
- **Credentials, data classes, disclosure:** [`security.md`](security.md).
- **Cadence, retention, quotas, spend:** [`cost_model.md`](cost_model.md).
- **What to do when something breaks:** [`RUNBOOK.md`](../RUNBOOK.md).
- **Runtime shape, schedule minute, retries, backfill:**
  [ADR 0003](adr/0003-ingest-and-build-as-cloud-run-jobs.md).

## 9. Review date

Revisit when:
- the ingest ADR lands (fill in the minute and the dbt runtime shape);
- the first prod run completes at the cutover (replace §4's illustrative
  timings with measured ones);
- a component boundary moves, or a new source or environment is added
  (both need an ADR, DECISIONS §11).

Otherwise, re-read alongside ADR 0001 at its 2027-04-05 checkpoint.

## 10. Change log

| Date | Change |
|---|---|
| 2026-10-05 | Initial version (A5). |
| 2026-11-18 | Drift fix (roadmap M1): hourly ingest plus a daily dbt build from its own Scheduler job; ingest no longer invokes dbt; Great Expectations in ingest; Zstandard Parquet; retention per table instead of "keep forever"; measured file sizes and publication time; no `PushEvent` in the trace; retries inside ingest, not Cloud Run or Scheduler; no Dockerfile story (DECISIONS §10); `raw_ingest_audit`, the language lookup and the kill switch added; security summary aligned with the access matrix (dbt never reads GCS, no reviewer identity, author is Owner, dashboard key in Streamlit secrets); pointers to the docs that now exist. |
| 2026-11-18 | ADR 0003 applied: ingest and dbt are Cloud Run jobs; `stg_events` is a view; build window capped at 4 catch-up days. |
