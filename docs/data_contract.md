# oss-pulse — Data Contract

> What the pipeline promises to its producers and consumers. Each table
> below has a **grain** (what one row means), a **freshness** target
> (how stale the data can get before it counts as broken), and a
> **column list** (what downstream code may rely on). Each upstream has
> known SLAs and failure modes. Each downstream consumer is named.
>
> This doc is the authority for "can I rely on column X being there?"
> If the answer isn't in here, it isn't a promise — it's an
> implementation detail that may move without warning.
>
> **Status.** All tables below are *planned* — the pipeline is in the
> foundation phase ([`../FOUNDATION_BACKLOG.md`](../FOUNDATION_BACKLOG.md)).
> This file exists so every mart PR has a contract to be consistent with
> before the SQL is written. A table's entry is **binding** the moment the
> table lands on `main`; before that, treat it as a design proposal and
> change freely.

---

## 1. How to use this doc

Three audiences, three questions:

- **A mart author** writing a new model: find the mart's entry in §5,
  satisfy its grain / columns / freshness, add tests that enforce them.
- **A dashboard author** writing a chart: read the mart's §5 entry; the
  listed columns are stable, anything else is not. If a chart needs a
  column that isn't listed, add it to the contract *first*, model
  *second*.
- **A reader after a failure**: §3 (upstream) and §7 (change-management)
  tell you what's expected to break on its own vs. what should be
  escalated.

**Reading order of a table entry:** grain → freshness → column list →
tests → notes. The grain is the most load-bearing field; most contract
bugs are "two rows where the grain said one."

**Rules that apply to every entry** (decided in
[`cost_model.md`](cost_model.md) §8, 2026-11-18):

- **`not_null` is a schema constraint, not a test query.** Raw columns
  marked non-nullable are `REQUIRED` in the BigQuery schema, so the load
  job rejects a null. dbt models use `contract: enforced` with `not_null`
  constraints. Wherever an entry lists `not_null`, read it this way. Every
  other test (`unique`, `relationships`, ranges, accepted values,
  singular tests) runs as a dbt test.
- **Cadence.** Ingest loads raw hourly. Everything downstream is built
  once a day by `dbt build` at 01:30 UTC, for the previous UTC day.
- **Retention** is set per table below. Long-lived tables (`fct_events`,
  dimensions, snapshot marts) set `full_refresh: false`, because a full
  refresh would rebuild them from 3 days of staging and wipe the rest.
- **Stable IDs.** Failure modes (`FM-nn`, §3.3 and §4.6), reconciliation
  counts (`R-nn`, §5.8) and metamorphic relations (`M-nn`, §5.9) each have
  an ID that tests reference by marker or tag. An ID is never renumbered
  or reused. A retired one stays in its table, marked *retired*; one whose
  spec isn't written yet is marked *pending* with the item that will write
  it. CI fails if any other ID has no test (failure-mode coverage, backlog
  B11).
- **Which days a build covers.** The daily build at 01:30 UTC builds
  yesterday (UTC), **plus every day still in raw (§4.1) that has a
  successful ingest attempt newer than that day's last successful build,
  or that has never built successfully.** This catches late hours and
  failed builds without re-reading days that didn't change (FM-17, FM-19).
  "The build's window" below means exactly those days.
- **Fixtures and expiration.** In CI and fixture runs, the dbt target
  turns partition expiration off, so fixtures can carry fixed past dates.
  The B11 retention check verifies the prod target's settings, not CI's.
  Mart-level tests may seed `fct_events` directly when they need more
  history than staging holds.

---

## 2. Vocabulary

Terms used throughout. Project vocabulary is enforced per
[`../CONVENTIONS.md`](../CONVENTIONS.md) §1 — no adjacent synonyms.

- **Event** — one record from GH Archive. Every row at the raw and
  staging layers is an event. Never "activity", never "action".
- **Repo** — a GitHub repository. Never "project" (that collides with
  GH's own Projects feature) or "repository" (verbose, inconsistent).
- **Actor** — the GitHub user who performed an event. Never "user"
  (ambiguous with "dashboard user") or "author" (reserved for commit
  authorship inside push events).
- **Hour** — the UTC hour of an event's `created_at`, written `YYYY-MM-DD-HH`
  (zero-padded) everywhere inside this project. GH Archive's URLs use an
  **unpadded** hour instead; see §3.1.
  All partitioning, scheduling, and SLAs are UTC-hour-aligned.
- **Grain** — what one row of a table represents. "One row per event",
  "one row per repo per day", etc.
- **Freshness** — the maximum acceptable age of the newest row,
  measured from now in UTC. A freshness target of `2h` means at any
  moment the newest row should be within 2 hours of now.
- **Mart** — a table in `osp_analytics_<env>` prefixed `mart_`.
  Consumer-shaped (one mart per dashboard chart / README question).

---

## 3. Upstream — GH Archive

### 3.1 Source

- **URL pattern:** `https://data.gharchive.org/<YYYY-MM-DD-H>.json.gz`,
  where `H` is the hour **without zero-padding** (`0`–`23`). So 05:00 UTC
  is `2026-11-10-5.json.gz`; `2026-11-10-05.json.gz` returns HTTP 404.
  Ingest must convert the project's padded hour to this form; a test
  covers hours 0–9.
- **Format:** gzipped line-delimited JSON. One JSON object per line, one
  event per object.
- **Access:** public, unauthenticated, HTTPS.
- **Schema reference:** <https://www.gharchive.org/#schema>. GitHub's
  own event-type reference:
  <https://docs.github.com/en/webhooks-and-events/events/github-event-types>.

### 3.2 SLA (measured, not contractual)

GH Archive is a free public service with no stated SLA. Four of the
rows below are **measured** from a small sample (see §3.2.1); the
availability row is a design assumption to be replaced with telemetry
once the pipeline runs in Phase D.

| Property | Value | Source | Designed-for |
|---|---|---|---|
| Hourly file publication delay | ~5 min after the hour closes (file's `Last-Modified` at `:05:03–:05:04` past the next hour, 6/6 published hours sampled) | measured | **Current `5 * * * *` cron gives ~0 min margin — see note below** |
| File size (gzipped) | ~6.5–14.2 MB per hour (7 published hours sampled; mid-day UTC runs ~6.5–7.7 MB, off-peak samples ran larger) | measured | Trivially fits in Cloud Run memory; still stream for forward-compatibility if volumes grow |
| File size (decompressed) | ~30–36 MB per hour (5 hours decompressed; the 14 MB gzipped sample was HEAD-only) | measured | Same |
| Row count per hour | ~5,000–7,700 events per hour (5 hours line-counted, range 5,171–7,736) | measured | Load path easily handles 10× this; no batching needed |
| Availability | **72 of 72 hours present** (every hour of 2026-10-06, 2026-10-07 and 2026-11-09, probed with unpadded URLs on 2026-11-11). The earlier "~55% present" figure was a measurement error (see §3.2.1). | measured | A missing hour is rare: treat it as an alerting failure, not routine; see §3.3 |
| Schema stability | GitHub's event schema has been stable for years but is **not versioned** | public knowledge | See §3.3 for how we detect drift |

**Scheduler-margin note.** The architecture ([`architecture.md`](architecture.md)
§4.2) specifies a `5 * * * *` cron (fires at :05 past the hour). With
GH Archive's measured publication delay of ~5 min, the scheduler fires
roughly when the file goes live — leaving effectively no margin for
GH Archive clock drift or slow publication. This is tracked as an
open question in §8; it may want to move to `15 * * * *` or similar
once Phase D produces real latency data.

#### 3.2.1 How these numbers were measured

All measurements taken on **2026-10-07**. Two passes:

1. **Core SLA** — HEAD requests against 2026-10-07 hours 14–19 UTC (6/6
   present); downloads + decompress + line-count on hours 14, 15, 17,
   18. This is the data behind the delay, size, and row-count rows.
2. **Schema + off-peak** — a 32,602-row scan across those four hours
   plus 2026-10-06-22 (one more line-counted file) covering top-level
   field presence, event-type distribution, and payload shape
   (see §3.3, §4.3, §5.1). Additional HEAD probes on 11 off-peak hours
   on 2026-10-06 and 2026-10-07 — 11 of 17 total probed hours
   returned 200; the rest 404'd. **Correction (2026-11-11):** those
   probes used zero-padded hours (`-05`), which GH Archive doesn't
   serve. The 404s are consistent with exactly that, and re-probing all
   24 hours of both days with unpadded URLs returned 24/24 each.
3. **Re-check (2026-11-11)** — full-day HEAD probes (unpadded) on
   2026-10-06, 2026-10-07 and 2026-11-09: 72/72 present. Downloaded
   2026-11-10 hours 15–17: 2.0–2.4 MB gzipped, 9,017 events total
   (~3,000/hour), below the October ranges above. Volumes are drifting
   down; the ranges above are kept as the October baseline.

Measurement scripts aren't checked in — PowerShell one-liners,
re-runnable against any hour. This is a one-day sample, not a
distribution; the intent is to replace guesses with order-of-magnitude
truth, not to characterise GH Archive across the year.

The gzipped size and event count here are substantially lower than
pre-2024 community reports describing GH Archive hours as 100 MB+
gzipped with millions of events. The ingest design should not assume
historical volumes without re-measuring. The complete absence of
`PushEvent` in the sample is likely the biggest single contributor
to that drop; see §4.3 and §5.

### 3.3 Known failure modes (upstream)

Fail-fast at ingest ([`../DECISIONS.md`](../DECISIONS.md) §6). Every
attempt at an hour is recorded in `raw_ingest_audit` (§4.5), with the
failure mode's ID when it fails. Pipeline-internal failure modes are in
§4.6.

**Retry and alert rule.** Each scheduled run ingests the previous hour,
and also retries every hour from the last 24 that has no success and
fewer than 3 failed scheduled attempts since its last success.
- **Availability failures** (FM-01, FM-03, FM-04, FM-05) may fix
  themselves. Attempts 1 and 2 log `WARNING`, so they don't page; the
  third logs `ERROR`, which alerts. Then scheduled retries stop, and the
  author replays by hand (RUNBOOK §3.1).
- **Content failures** (FM-06, FM-09, FM-12) fail the same way on the same
  file every time. They log `ERROR` on the first attempt, and aren't
  retried until a fix is merged and the hour is replayed.
- **Precedence** when one file has several problems: the first failing
  check in the order FM-09, FM-06, FM-12 is the one recorded.

| ID | Failure | Signal | Handling |
|---|---|---|---|
| FM-01 | **Missing hour (404).** Rare: §3.2 found 72/72 hours present. | HTTP 404 at the hourly URL | Availability failure (rule above). An hour still missing after 3 attempts is recorded, and downstream counts simply exclude it; R-07 accounts for it. |
| FM-02 | **Late hour** (published after the scheduled fetch) | 404 on one run, 200 on a later one | Picked up by the next run's retry. If the hour's day was already built, the next daily build rebuilds that day (FM-17). |
| FM-03 | **Transient download failure:** HTTP 5xx, timeout, connection reset | Error on the GET | Ingest retries the download 3× with backoff within the run. Still failing: an availability failure (rule above). The Scheduler job itself doesn't retry. |
| FM-04 | **Truncated download** | Bytes received ≠ `Content-Length`, or a gzip end-of-stream / JSON parse error mid-file | Treated as FM-03: the file is re-downloaded, never partly loaded. Observed 2026-11-18 on our side: one download stopped at 1.76 of 4.57 MB, and the retry was complete. |
| FM-05 | **Zero-byte file** | `Content-Length: 0` or an empty decoded body | Availability failure (GH Archive may republish). |
| FM-06 | **Missing or null required field** | A record lacks `id`, `type`, `actor`, `repo` or `created_at`, or a `REQUIRED` raw column would be null | Content failure. The Great Expectations suite catches it before the load; the `REQUIRED` schema is the backstop. |
| FM-07 | **New event type** | `event_type` not in §4.3 | Doesn't block anything. The `accepted_values` test on `stg_events.event_type` runs at severity `warn` with the tag `alert`, and the dbt service logs `ERROR` for any warned test tagged `alert`. So it alerts within a day without freezing the marts. Adding the value is then a routine contract change (§7.3). |
| FM-08 | **New field inside `payload`** | Unknown key in the JSON | No action. `payload` is kept verbatim; new fields are invisible downstream until a model extracts them. A test asserts that unknown keys don't break staging. |
| FM-09 | **Event outside its file's hour** | `created_at` truncated to the hour ≠ the file's hour | Content failure. The hour-scoped load would reject the row anyway. Not observed: 0 of 9,291 events across 3 hours of 2026-11-17. A consequence used by FM-10: copies of one event always share an hour. |
| FM-10 | **Duplicate `event_id` within an hour** | Same `event_id` on two rows of one file | Raw keeps both (raw has no `unique` test). `stg_events` keeps one and counts the rest (R-02). Because of FM-09, duplicates can't span hours or days, so deduplicating within each built day is complete. Not observed in the same sample. |
| FM-11 | **Out-of-range `created_at`** | Outside `2015-01-01` … now + 1h | Defense in depth: FM-09 stops this at ingest in normal operation, so only seeded or backfilled raw can reach it. `stg_events` drops such rows and counts them (R-02). |
| FM-12 | **Batch fails another data-quality expectation** (types, accepted values, row-count range) | Great Expectations suite | Content failure. Fixed by a PR (data or expectation), then replayed. |

### 3.4 What we do *not* promise upstream

- We do not re-publish or redistribute GH Archive data.
- We do not guarantee lower latency than GH Archive itself.
- We make no attempt to reconstruct missing hours from GitHub's live
  events API; a lost hour is lost.

---

## 4. Raw and staging layers

Internal tables. Dashboards and external consumers never read these.
Mart authors use `stg_*` as the only sanctioned source; `raw_*` is for
backfill, debugging, and schema-drift detection.

### 4.1 `osp_raw_<env>.raw_gharchive_events`

- **Grain:** one row per GH Archive event.
- **Writer:** ingest Cloud Run service.
- **Readers:** dbt (staging only); human developer for debugging.
- **Partitioning:** hourly, on `event_hour` (DATE-TRUNC of
  `created_at` to hour-aligned timestamp, declared as a BigQuery
  time-unit partition on `created_at`).
- **Clustering:** `repo_id`.
- **Retention:** 3 days (partition expiration). GCS keeps each hour's
  Parquet for 14 days, and reloading from it is a free load job. Loading
  an hour older than 3 days into this table deletes it on arrival, so
  backfills need their own path (cost model §5.3).
- **Freshness target:** newest `event_hour` within 2h of now (allows
  for the scheduler offset + ingest runtime + alert fatigue margin).
  Checked by the daily build's source-freshness test, so a stalled ingest
  can go unnoticed for up to ~24h. Ingest *failures* still alert within
  the hour.
- **Columns:**

  | Column | Type | Nullable | Notes |
  |---|---|---|---|
  | `event_id` | STRING | No | GH Archive `id`. Primary key. |
  | `event_type` | STRING | No | GH Archive `type`. See §4.3 for the accepted-values list. |
  | `actor_id` | INT64 | No | GH Archive `actor.id`. |
  | `actor_login` | STRING | Yes | GH Archive `actor.login`. Can lag renames. |
  | `repo_id` | INT64 | No | GH Archive `repo.id`. Clustering key. |
  | `repo_name` | STRING | Yes | GH Archive `repo.name`. Format: `owner/name`. Can lag renames. |
  | `org_id` | INT64 | Yes | GH Archive `org.id` when present. ~43% of events have an `org` (events on org-owned repos). |
  | `org_login` | STRING | Yes | GH Archive `org.login` when present. |
  | `is_public` | BOOL | No | GH Archive `public`. 100% of sampled events are `true`; retained because the field is always sent and could meaningfully be `false` in theory. |
  | `payload` | JSON | Yes | Entire GH Archive `payload` object, preserved verbatim. |
  | `created_at` | TIMESTAMP | No | GH Archive `created_at`. Event time. |
  | `event_hour` | TIMESTAMP | No | `TIMESTAMP_TRUNC(created_at, HOUR)`. Partition key. |
  | `ingest_run_id` | STRING | No | UUID of the ingest invocation that landed the row. Enables backfill audit. |
  | `ingested_at` | TIMESTAMP | No | When the row landed in BigQuery. |

- **Tests:** `not_null` on every non-nullable column (as `REQUIRED`
  columns; ingest's pyarrow schema marks them `nullable=False` to match);
  freshness check per the target above. **No `unique` test on raw:** raw
  keeps what GH Archive sent, duplicates included (FM-10); uniqueness is
  enforced in staging.

### 4.2 `osp_staging_<env>.stg_events`

- **Grain:** one row per deduplicated event — `event_id` is unique.
- **Writer:** dbt. Reads `raw_gharchive_events`.
- **Readers:** dbt (fact/mart layer); never read by dashboards.
- **Materialization:** incremental on `event_hour`, `insert_overwrite`
  strategy (dbt's `merge` would scan the whole table every build).
- **Retention:** 3 days (partition expiration), like raw. It carries the
  full `payload`, so it's as large as raw.
- **Freshness target:** 28h. Built once a day for the previous UTC day;
  just before the next build finishes, the newest `event_hour` is ~26.6h
  old.
- **Columns:** same shape as raw, plus `payload_action`, with these
  transformations:
  - `event_type` is `accepted_values`-tested (see §4.3).
  - `created_at` is cast and verified to be within a sane window
    (`BETWEEN TIMESTAMP("2015-01-01") AND CURRENT_TIMESTAMP() +
    INTERVAL 1 HOUR`); rows outside the window are dropped and
    counted in a load-audit view.
  - **Only rows from each hour's latest successful ingest attempt** are
    read (joined on `ingest_run_id` to `raw_ingest_audit`). Rows left by
    a failed attempt (FM-14) are ignored.
  - Then, in this order, each row is dropped by the first rule it meets:
    1. **suppressed:** its `actor_id` is on the `actor_suppressions` seed,
       or its `repo_id` is on the `repo_suppressions` seed (removal
       requests, [`security.md`](security.md) §2.2);
    2. **out of range:** `created_at` outside the window below (FM-11);
    3. **duplicate:** a second or later row with an `event_id` already
       kept for that day (FM-10).
  - `payload` stays as JSON.
  - `payload_action` (STRING, nullable) is extracted from
    `payload.action` here, once. `fct_events` reads it instead of the JSON,
    which may bill the whole `payload` column on every read.
- **Tests:** `not_null` on `event_id`, `event_type`, `repo_id`,
  `actor_id`, `created_at`; `unique` on `event_id`; `accepted_values`
  on `event_type` (severity `warn`, tag `alert`; FM-07).

### 4.3 Accepted `event_type` values

The dbt `accepted_values` test on `stg_events.event_type` whitelists
these. A new value appearing in raw fails the test (loud signal that
GitHub added an event type).

```
CommitCommentEvent, CreateEvent, DeleteEvent, DiscussionEvent,
ForkEvent, GollumEvent, IssueCommentEvent, IssuesEvent, MemberEvent,
PublicEvent, PullRequestEvent, PullRequestReviewEvent,
PullRequestReviewCommentEvent, PushEvent, ReleaseEvent,
SponsorshipEvent, WatchEvent
```

Measured presence in the §3.2.1 sample (32,602 rows across 5 hours):
`CreateEvent`, `DeleteEvent`, `PushEvent`, `SponsorshipEvent` — **0
rows each.** The first three are historically very common; their
absence from the current public events feed is a material finding and
drives the mart-contract changes in §5. They stay on the whitelist so
that if GitHub restores them, their reappearance is silently accepted
rather than firing a test failure.

Updating the list is a contract change — see §7.

### 4.4 `stg_repos`, `stg_actors`

- **`stg_repos`** — one row per unique `repo_id` seen across the
  staging window. Columns: `repo_id` (PK), `repo_name`,
  `first_seen_at`, `last_seen_at`.
- **`stg_actors`** — one row per unique `actor_id`. Columns:
  `actor_id` (PK), `actor_login`, `first_seen_at`, `last_seen_at`.
- **Freshness:** 28h.
- **Tests:** `not_null` on PK; `unique` on PK; relationship test from
  `stg_events` to each.

Both exist so dim tables don't scan `raw_gharchive_events` directly.

---

### 4.5 `osp_raw_<env>.raw_ingest_audit`

- **Grain:** one row per ingest attempt for one hour. An hour can have
  several rows: failed attempts, then a success, and later replays.
- **Writer:** ingest, with a **load job** (append), never DML
  ([`cost_model.md`](cost_model.md) §4.4). The row is written at the end
  of the attempt, so an attempt killed before then leaves no row (FM-18).
- **Readers:** ingest itself, to find hours to retry and count their
  attempts, using `tabledata.list` (free) rather than a query; staging
  (latest success per hour, §4.2); the build's day selection (§1); dbt
  reconciliation tests (R-01, R-07); the author when investigating.
- **Retention:** kept. It's tiny (≈ 730 rows a month), and it can't be
  re-derived if lost (RUNBOOK §3.5).
- **Columns:**

  | Column | Type | Nullable | Notes |
  |---|---|---|---|
  | `ingest_run_id` | STRING | No | UUID of this attempt. Primary key. Matches `raw_gharchive_events.ingest_run_id` for loaded rows. |
  | `event_hour` | TIMESTAMP | No | The hour this attempt targeted. |
  | `trigger` | STRING | No | `schedule`, `replay` or `backfill`. |
  | `attempt_number` | INT64 | No | For `schedule` attempts: 1, 2 or 3, counting failed scheduled attempts since the hour's last success. 1 for `replay` and `backfill`. |
  | `started_at` | TIMESTAMP | No | |
  | `finished_at` | TIMESTAMP | No | |
  | `outcome` | STRING | No | `success`, `missing` (FM-01), `failed` (anything else). |
  | `failure_mode` | STRING | Yes | The `FM-nn` ID when `outcome != 'success'`. |
  | `http_status` | INT64 | Yes | Last HTTP status from GH Archive. |
  | `bytes_downloaded` | INT64 | Yes | Compressed bytes received. |
  | `lines_read` | INT64 | Yes | Events read from the file. |
  | `parquet_rows` | INT64 | Yes | Rows written to the Parquet file. |
  | `rows_loaded` | INT64 | Yes | From the load job's statistics. |
  | `gcs_uri` | STRING | Yes | The Parquet file written, on success. |
  | `bq_load_job_id` | STRING | Yes | The raw load job, on success. |
  | `error_message` | STRING | Yes | First 1,000 characters. Never contains credentials. |

- **Tests:** `unique` on `ingest_run_id`; `accepted_values` on `trigger`
  and `outcome`; `accepted_values` on `failure_mode`, listing only the IDs
  ingest can record (FM-01, FM-03, FM-04, FM-05, FM-06, FM-09, FM-12,
  FM-13, FM-14); R-01, R-07.

### 4.6 Pipeline failure modes

Failures inside our own pipeline, numbered with §3.3 (IDs are unique
across both tables).

| ID | Failure | Signal | Handling |
|---|---|---|---|
| FM-13 | **Replay of an hour whose day is too old to rebuild** | The target day's first hour is more than 70 hours old (raw keeps 72; 2 hours' margin for the rebuild) | Ingest refuses with a clear error instead of loading into a day that can no longer be rebuilt whole. Use the backfill path ([`cost_model.md`](cost_model.md) §5.3). |
| FM-14 | **Rows don't reconcile at ingest** | `lines_read` ≠ `parquet_rows` (checked before the load), or `parquet_rows` ≠ `rows_loaded` (after) | The attempt is recorded `failed` and logs `ERROR`. A mismatch before the load stops it; rows from a mismatch after the load stay in raw, but staging ignores them (§4.2), and the next attempt's `WRITE_TRUNCATE` replaces them. |
| FM-15 | **BigQuery quota exceeded** | `quotaExceeded` on a query | The build fails and logs `ERROR`. It isn't retried before the quota resets (midnight Pacific). Ingest is unaffected (loads aren't queries). The day is caught up by the next build (§1). |
| FM-16 | **Language lookup fails or is rate-limited** | GitHub API 403/429/5xx | *Pending: spec in the M4 language ADR.* Intended handling: repos keep their last known language, or NULL (`(unknown)`), are retried next run, and the dbt build never fails because of it. |
| FM-17 | **Hour loaded after its day was built** (a late hour 23, a replay) | A success in `raw_ingest_audit` newer than the day's last successful build | The next daily build rebuilds that day (§1). Nothing is lost while the day is still in raw (FM-13 guards the edge). |
| FM-18 | **Ingest killed mid-attempt** (timeout, out of memory) | Cloud Run logs the crash; the attempt leaves no audit row | Cloud Run's crash log is an `ERROR`, which alerts. The hour has no success, so the next run retries it (§3.3 rule). Any rows it loaded are ignored by staging (no success row). |
| FM-19 | **dbt build fails or times out** | Non-zero exit or request timeout | Logs `ERROR`, which alerts. Marts stay at their last good state. The day is caught up by the next build (§1); a fix goes through a PR (RUNBOOK §3.3). |
| FM-20 | **Dashboard can't load a mart** | Query error, quota exceeded, or no partition for the expected date | The chart shows "data unavailable" (DECISIONS §6). For the snapshot marts, the dashboard asks for yesterday's partition and falls back once to the day before. RUNBOOK §3.6. |

## 5. Marts — the four contract-bearing tables## 5. Marts — the four contract-bearing tables

Marts are the only tables the dashboard reads. Each mart answers one
README question (`../README.md` §"The questions it answers") and
feeds one chart.

**Rule:** no mart lands without an entry in this section first. The
entry defines the grain, the columns the dashboard may rely on, the
freshness target, and the tests that enforce them.

### 5.1 `fct_events` — fact table (not a mart, but contract-bound)

Not consumed by the dashboard directly, but marts build on it, so its
contract matters.

- **Grain:** one row per event (`event_id` unique).
- **Freshness:** 28h.
- **Materialization:** incremental, `insert_overwrite` on daily
  partitions of `event_hour`; `full_refresh: false`.
- **Retention:** 400 days (partition expiration). Covers the 90-day
  concentration window and 13 months of the language chart.
- **Columns:** `event_id` (PK), `event_type`, `event_hour`,
  `created_at`, `actor_id` (FK → `dim_actors`), `repo_id` (FK →
  `dim_repos`), plus event-type-specific flags extracted from
  `payload`:
  - `is_star` (BOOL) — `event_type = 'WatchEvent'`.
  - `is_pr_opened` (BOOL) — `event_type = 'PullRequestEvent'` AND
    `payload.action = 'opened'`. (All `payload.action` conditions in this
    list read `stg_events.payload_action`.)
  - `is_pr_merged` (BOOL) — `event_type = 'PullRequestEvent'` AND
    `payload.action = 'merged'`. In this schema, "merged" and "closed"
    are distinct `action` values on PullRequestEvent; `merged` fires
    only when a PR is actually merged. Re-measured 2026-11-11 across
    hours 2026-11-10-15..17 (9,017 events, 4,009 PullRequestEvents):
    `merged` = 1,428, `opened` = 1,595, `closed` = 76. Note the event's
    `actor` on a `merged` action is the person who merged the PR (often
    a maintainer), not the PR's author.
  - `is_pr_closed_unmerged` (BOOL) — `event_type = 'PullRequestEvent'`
    AND `payload.action = 'closed'`. Measured on a sample
    PullRequestEvent, `payload.pull_request.merged` was not present
    (only 5 keys on the pull_request object: `url`, `id`, `number`,
    `head`, `base`), so we rely on the top-level `action` discriminator.
  - `is_issue_opened` (BOOL) — `event_type = 'IssuesEvent'` AND
    `payload.action = 'opened'`.
  - `is_issue_closed` (BOOL) — `event_type = 'IssuesEvent'` AND
    `payload.action = 'closed'`.
  - `is_fork` (BOOL) — `event_type = 'ForkEvent'`.

  Not included: `is_push` / `push_commit_count`. `PushEvent` is absent
  from the current public events feed (0 of 32,602 sampled rows); the
  columns can't be populated. See §4.3 and §5.3 / §5.5 / §5.6 for the
  mart-level consequences.

- **Tests:** `not_null` on PK and FKs; `unique` on `event_id`;
  `relationships` on `actor_id` and `repo_id`.

### 5.2 `dim_repos`, `dim_actors` — dimensions

- **`dim_repos`** — `repo_id` (PK), `repo_name`, `primary_language`
  (STRING, nullable — see §5.6 for how it's derived), `first_seen_at`,
  `last_seen_at`.
- **`dim_actors`** — `actor_id` (PK), `actor_login`, `first_seen_at`,
  `last_seen_at`.
- **Freshness:** 28h.
- **Retention:** kept; `full_refresh: false`. `fct_events` has no
  `repo_name` or `actor_login`, so a lost dimension can only be rebuilt by
  backfilling from GH Archive.
- **Tests:** `not_null` and `unique` on PK.

### 5.3 `mart_trending_repos`

**Answers:** README Q1 — repos with the largest week-over-week increase
in stars or PRs. (README originally said "stars, PRs, or pushes";
`pushes_*` columns are omitted because `PushEvent` is absent from the
feed — see §4.3. README wording drift tracked in §8.)

- **Grain:** one row per `(repo_id, as_of_date)` — a daily snapshot of
  each repo's 7-day rolling counts.
- **Freshness:** 28h (recomputed daily for the previous full UTC day).
- **Partitioning:** `as_of_date`. **Retention:** 30 days of snapshots
  (partition expiration); `full_refresh: false`.
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `repo_id` | INT64 | FK → `dim_repos`. |
  | `repo_name` | STRING | Copied from `dim_repos` at build time, so the dashboard reads marts only (§6.1). |
  | `as_of_date` | DATE | Snapshot day. |
  | `stars_7d` | INT64 | WatchEvent count over 7 days ending `as_of_date`, inclusive (`as_of_date` and the 6 days before). Every `*_7d`, `*_30d` and `*_90d` window in §5 is inclusive the same way. |
  | `prs_opened_7d` | INT64 | `fct_events.is_pr_opened` count over same window. |
  | `prs_merged_7d` | INT64 | `fct_events.is_pr_merged` count over same window. |
  | `stars_delta_wow` | INT64 | `stars_7d` minus the same figure 7 days earlier. |
  | `prs_opened_delta_wow` | INT64 | Same shape for `prs_opened_7d`. |
  | `prs_merged_delta_wow` | INT64 | Same shape for `prs_merged_7d`. |
- **Tests:** `not_null` on all columns; `unique` on
  `(repo_id, as_of_date)`.

### 5.4 `mart_language_share`

**Answers:** README Q2 — percentage of unique contributors touching
each language, month over month.

- **Grain:** one row per `(month, language)`. `month` is a `DATE` set
  to the first day of the month.
- **Freshness:** 28h — the mart updates once per day; the dashboard
  shows the latest complete month plus the running partial month.
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `month` | DATE | First day of the month, UTC. |
  | `language` | STRING | `dim_repos.primary_language` of the touched repo. NULL grouped as `(unknown)`. |
  | `distinct_contributors` | INT64 | Count of distinct `actor_id` with any `fct_events.is_pr_opened` or `fct_events.is_pr_merged` event on a repo whose `primary_language` = `language`. (Originally defined on `PushEvent`, which is absent from the feed — see §4.3.) |
  | `total_contributors_this_month` | INT64 | Denominator — count of distinct `actor_id` with any `is_pr_opened` or `is_pr_merged` event this month, across all languages. Shares across languages can sum to more than 100% because one actor can touch repos in several languages. |
  | `share_pct` | FLOAT64 | `distinct_contributors / total_contributors_this_month * 100`. 0–100. |
- **Tests:** `not_null` on `month`, `language`,
  `distinct_contributors`, `share_pct`; `unique` on
  `(month, language)`; `share_pct between 0 and 100` (dbt
  `accepted_range`).

### 5.5 `mart_contributor_concentration`

**Answers:** README Q3 — "contributor concentration per repo." Original
wording called for Gini of **commits per author**, derived from
`PushEvent`. With `PushEvent` absent from the feed (§4.3), the nearest
buildable metric is Gini of **PR-opening events per actor** per repo
— a reasonable proxy for how concentrated contribution activity is,
with the caveat that it measures contributors-who-propose-changes
rather than contributors-who-commit. README wording drift tracked in §8.

- **Grain:** one row per `(repo_id, as_of_date)`. Daily snapshot.
- **Freshness:** 28h.
- **Partitioning:** `as_of_date`. **Retention:** 30 days of snapshots
  (partition expiration); `full_refresh: false`.
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `repo_id` | INT64 | FK → `dim_repos`. |
  | `repo_name` | STRING | Copied from `dim_repos` at build time, so the dashboard reads marts only (§6.1). |
  | `as_of_date` | DATE | Snapshot day. |
  | `distinct_pr_openers_90d` | INT64 | Distinct `actor_id` with `is_pr_opened = true` on this repo over trailing 90 days. |
  | `total_prs_opened_90d` | INT64 | Count of `is_pr_opened` events on this repo over trailing 90 days. |
  | `gini` | FLOAT64 | Gini coefficient of PR-opens per actor over trailing 90 days, among actors who opened at least one PR, using the uncorrected mean-difference formula G = Σᵢ Σⱼ \|xᵢ − xⱼ\| / (2 n² x̄). Worked case: opens (3, 1) → 0.25. 0 = perfectly even. With *n* openers it approaches (*n*−1)/*n* when one actor opens almost every PR and each other actor opens one. So a repo with a single opener has `gini = 0`, and values near 1 need many openers with one dominating. |
- **Tests:** `not_null` on all columns; `unique` on
  `(repo_id, as_of_date)`; `gini between 0 and 1`;
  `distinct_pr_openers_90d >= 1` (singular test — a row shouldn't exist
  for a repo with no PR openers in the window).

### 5.6 `mart_time_of_day_activity`

**Answers:** README Q4 — PR / issue / star distribution by hour, split
by primary language of the repo. (README originally said "commit and
PR" distribution; `commit` would require `PushEvent`, which is absent
from the feed. README wording drift tracked in §8.)

- **Grain:** one row per `(language, hour_of_day, event_type_bucket)`.
  `hour_of_day` is 0–23 UTC.
- **Freshness:** 28h.
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `language` | STRING | `dim_repos.primary_language`. NULL grouped as `(unknown)`. |
  | `hour_of_day` | INT64 | 0–23. UTC. |
  | `event_type_bucket` | STRING | One of `pr_opened`, `pr_merged`, `issue_opened`, `star`. |
  | `event_count_30d` | INT64 | Count of events in that bucket over trailing 30 days. |
  | `pct_of_language_30d` | FLOAT64 | `event_count_30d` as a percent of the language's total events in `event_type_bucket` over the same window. 0–100. |
- **Tests:** `not_null` on all columns; `unique` on
  `(language, hour_of_day, event_type_bucket)`; `hour_of_day between
  0 and 23`; `pct_of_language_30d between 0 and 100`;
  `event_type_bucket in ('pr_opened', 'pr_merged', 'issue_opened', 'star')`.

### 5.7 Where `primary_language` comes from

`dim_repos.primary_language` is the main unknown in the mart contracts
above — GH Archive events don't carry language. Two options, chosen at
`dim_repos` build time:

- **Option A (default): GitHub REST API lookup**, one call per repo
  per week, cached in `dim_repos`. Needs a GitHub token in Secret
  Manager; rate-limited to 5000/hour authenticated.
- **Option B (fallback if rate limits bite): leave `primary_language`
  NULL** and let the mart group NULLs as `(unknown)`. The dashboard
  still works, with an "unknown" slice in each chart.

Which option is live is recorded in the first dbt PR that lands
`dim_repos`. Changing it is a contract-affecting change (§7).

---

### 5.8 Reconciliation counts (must balance)

Each is a dbt singular test, tagged with its ID, that runs in every build:
in CI on fixtures and in prod daily. It checks **the build's window**
(§1) only. A mismatch fails the build.

| ID | Statement |
|---|---|
| R-01 | For the latest successful attempt of every hour in the window: `lines_read = parquet_rows = rows_loaded` = the count of `raw_gharchive_events` rows with that `ingest_run_id`. (Earlier attempts' rows were overwritten, so they aren't checked.) |
| R-02 | For every `event_hour` in the window: the raw rows of the hour's latest successful attempt = `stg_events` rows + suppressed + out of range + duplicates, where each dropped row is counted once, under the first rule it met (§4.2). |
| R-03 | For every `event_hour` in the window: `fct_events` rows = `stg_events` rows. |
| R-04 | For every `as_of_date` built in this run: the sums of `stars_7d`, `prs_opened_7d` and `prs_merged_7d` over `mart_trending_repos` = the counts of `is_star`, `is_pr_opened` and `is_pr_merged` in `fct_events` over the same 7 days. (So every repo with any of those events in the window has a row.) |
| R-05 | For every `as_of_date` built in this run: the sum of `total_prs_opened_90d` over `mart_contributor_concentration` = the count of `is_pr_opened` in `fct_events` over the same 90 days. |
| R-06 | For each `event_type_bucket`: the sum of `event_count_30d` over `mart_time_of_day_activity` = the count of that bucket's events in `fct_events` over the same 30 days. And for each `(language, event_type_bucket)`, `pct_of_language_30d` sums to 100 (±0.01) over the 24 hours. |
| R-07 | Every hour in the window, and every hour from the last 24, is in exactly one state: **succeeded** (has a success); **given up** (3 failed scheduled attempts since its last success, which alerted); or **pending** (fewer than 3 attempts, and younger than 3 hours). An hour in none of these is silently missing, and fails the test. |

### 5.9 Metamorphic relations (change the input, predict the output)

Each is a test that runs the pipeline (ingest or dbt) twice on fixtures,
the second time with the input changed in a known way, and compares the
outputs. Tagged with its ID. "A checksum" of a table means a checksum over
every column except `ingest_run_id` and `ingested_at`, which change on every
load by design.

| ID | Change to the input | Expected output |
|---|---|---|
| M-01 | Ingest the same hour a second time | Raw, staging, fact and marts have the same row counts and checksums. |
| M-02 | Add +1 day to every `created_at`, and to `run_date` | Every `event_hour` and `as_of_date` moves by one day; every measure is unchanged. Fixtures stay inside one calendar month both before and after the shift (so `month` doesn't change), and end at least 2 days before now (so the shift stays inside staging's time window). |
| M-03 | Relabel actors with a one-to-one mapping of `actor_id`s | `gini`, distinct-contributor counts and shares are unchanged. |
| M-04 | On one repo, give every PR opener the same number of PR opens | That repo's `gini = 0`. |
| M-05 | Multiply every actor's PR opens on a repo by the same factor | That repo's `gini` is unchanged. |
| M-06 | Duplicate every row within its hour (same `event_id`) | Staging, fact and marts are unchanged; R-02 counts the duplicates (FM-10). |
| M-07 | Add events for one repo only | Only that repo's rows change in `mart_trending_repos` and `mart_contributor_concentration`. |

## 6. Downstream — Streamlit dashboard## 6. Downstream — Streamlit dashboard

### 6.1 Consumer

- **App:** `dashboard/app.py` on Streamlit Community Cloud.
- **Reads:** the four `mart_*` tables in §5. Nothing else.
- **Auth:** `osp-dashboard-<env>` service account, `roles/bigquery.
  dataViewer` on `osp_analytics_<env>` only (per
  [`architecture.md`](architecture.md) §7).
- **Access pattern:** each chart loads its mart once per refresh. For
  the snapshot marts that's the latest `as_of_date` partition, selected
  by a literal date (a `MAX(as_of_date)` subquery would scan every
  partition). Sorting, top-N and date-range filtering happen in pandas.
  Results are cached with `st.cache_data(ttl=3600)`, shared by all
  viewers. Queries avoid `CURRENT_DATE()`, which disables BigQuery's free
  result cache.

### 6.2 SLA to the viewer

- **Freshness:** 28h for every chart (all four marts build daily), plus
  up to 1h of dashboard cache.
- **Availability:** Streamlit Community Cloud's own SLA — effectively
  "usually up, no promises." No alerting on dashboard downtime.
- **Degradation:** per `../DECISIONS.md` §6, a missing mart renders as
  a "data unavailable" placeholder, not a stack trace.

### 6.3 What the dashboard may NOT do

- No business logic beyond chart-level filtering (sort, top-N, date
  range). If a chart needs a column that doesn't exist in the mart,
  the fix is a contract update and a mart change — not a dashboard
  patch.
- No writes to BigQuery. The SA role above denies writes.

---

## 7. Change management

### 7.1 Classes of change

Three classes, each with a different review bar.

| Class | Examples | Requires |
|---|---|---|
| **Additive** | New non-nullable column with a safe default, new row-grouping that keeps grain, new mart entry | A single PR touching this doc + the dbt change. Dashboard untouched unless it opts in. |
| **Changing** | Renaming a column, changing a type, tightening a nullable to non-nullable, changing a mart's grain or freshness target | PR must update this doc, the dbt change, every dashboard chart that reads the column, and the DECISION_LOG entry for the subsystem. A one-release deprecation window where both old and new exist. |
| **Removing** | Dropping a column, dropping a mart | A deprecation PR that marks the column/mart deprecated here and emits a `dbt_utils.deprecated_relation` warning, then a second PR one release later that removes it. |

A "release" for a solo project is a merge to `main` that touches the
affected table.

### 7.2 Deprecation marker

When a column or table is deprecated:

- Add `**Deprecated: <YYYY-MM-DD>, remove after <YYYY-MM-DD + 14 days>**`
  on the first line of its entry here.
- Add a `-- DEPRECATED: <reason>` comment in the dbt model.
- Open a tracking item in `../OPEN_LOOPS.md` with the removal date.

### 7.3 What never changes without an ADR

- The grain of `stg_events` or `fct_events`.
- The set of mart tables listed in §5 (adding or removing a mart
  changes the dashboard story — ADR territory).
- The `event_type` accepted-values list (adding a value is routine;
  removing one is an ADR because it changes the project's event
  coverage).
- The partition / cluster keys on raw.

Changes to any of the above require an ADR under `docs/adr/` before
the model changes.

---

## 8. Open questions

Known gaps this doc doesn't yet answer. Each is tracked for later.

- **Scheduler offset.** The `5 * * * *` cron fires at the same minute
  GH Archive publishes (see §3.2 note). Likely needs to move later
  — `15 * * * *` is the obvious first try — but the right value needs
  one real pipeline-latency measurement from Phase D before it's
  locked. Tracked for the first ingest ADR.
- **README wording drift.** Resolved 2026-11-18: the README's four
  questions now match §5.
- **Backfill window.** How far back do we backfill when first lighting
  the pipeline? Likely answered by the first ingest ADR. Constraints from
  [`cost_model.md`](cost_model.md) §5.3: raw's 3-day expiration means a
  separate backfill path, and 90 days takes about a week of query quota.
- **PII posture.** Resolved 2026-11-18 in
  [`security.md`](security.md) §2.2: handles are public but identifiable;
  the dashboard never shows an individual actor, and removal requests are
  honored by hand.
- **GitHub token for language lookup (§5.7).** Resolved 2026-11-18 in
  [`security.md`](security.md) §3.2: a no-permission fine-grained token
  from the bot account, one-year expiry, in prod Secret Manager. Whether
  option A is used at all is still decided when `dim_repos` is built.

---

## 9. Change log

| Date | Change |
|---|---|
| 2026-10-07 | Initial version. Covers upstream (GH Archive), raw + staging layers, four mart contracts, Streamlit consumer, change-management rules. Closes A7. |
| 2026-10-07 | §3.2 replaced order-of-magnitude guesses with measurements from a 6-hour sample on 2026-10-07; added §3.2.1 (method) and a scheduler-margin note. Added §8 item for the scheduler offset. |
| 2026-10-07 | Follow-up measurement run (32,602 rows across 5 hours + 11 off-peak HEADs) drove: §3.2 availability downgraded to ~55% measured, file-size and row-count ranges widened; §3.3 missing-hour upgraded from edge case to hot path (non-alerting by default); §4.1 added `org_id`, `org_login`, `is_public`; §4.3 added `DiscussionEvent` to the whitelist and noted PushEvent/CreateEvent/DeleteEvent/SponsorshipEvent as absent-but-whitelisted; §5.1 removed `is_push`/`push_commit_count`, re-derived PR flags from `payload.action` (the measured discriminator); §5.3 replaced `pushes_*` columns with `prs_opened_*` + `prs_merged_*`; §5.5 redefined the mart around PR-opening actors (PushEvent-based commit metric unbuildable); §5.6 replaced `push` bucket with `issue_opened` + `star`; §8 added README-wording-drift item. |
| 2026-11-11 | §3.1 URL pattern corrected to an unpadded hour (`-5`, not `-05`); §2 notes the project's own hour stays padded. §3.2 availability corrected from ~55% to 72/72 present: the earlier 404s came from padded URLs (§3.2.1 correction + re-check). §3.3 missing hour downgraded from routine to rare, now alerting after 3 failed attempts instead of a trailing-24h miss-rate threshold. |
| 2026-11-11 | §5.4 `distinct_contributors` / `total_contributors_this_month` redefined on PR-opened or PR-merged events (the old definition still referenced the absent `PushEvent`); noted shares can sum past 100%. §5.1 `is_pr_merged` re-verified against 3 fresh hours (`merged` action confirmed present) and noted that a merge event's actor is the merger, not the author. |
| 2026-11-18 | §8 README wording drift marked resolved (README reworded to match §5). |
| 2026-11-18 | Applied the cost model's approved decisions ([`cost_model.md`](cost_model.md) §8): `not_null` becomes a schema constraint (§1, §3.3, §4.1); daily dbt cadence with 28h freshness on everything below raw, including the three marts that had 24h (§4.2–§5.6, §6.2); retention per table (raw and `stg_events` 3 days, `fct_events` 400 days, snapshot marts 30 days, dims kept) with `full_refresh: false` on long-lived tables; `insert_overwrite` incrementals; `stg_events.payload_action` added; snapshot marts partitioned on `as_of_date`; dashboard loads each mart once and caches (§6.1). |
| 2026-11-18 | §8 PII posture and language-lookup token marked resolved by `security.md` §2.2 and §3.2. |
| 2026-11-18 | §5.3, §5.5: `repo_name` added to the two repo-level marts (additive), so the dashboard needn't read `dim_repos`. §4.2: `actor_suppressions` filter for removal requests. |
| 2026-11-18 | Failure modes get stable IDs: §3.3 rewritten as FM-01…FM-12 (adds truncated download, event outside its hour, duplicates, out-of-range timestamps, data-quality failure; transient retries move into ingest; late hours are retried automatically); §4.6 adds pipeline failure modes FM-13…FM-16. §4.5 adds `raw_ingest_audit`. §5.8 reconciliation counts R-01…R-07 and §5.9 metamorphic relations M-01…M-07. §5.5 `gini` range clarified. §1 stable-ID rule. |
| 2026-11-18 | Review fixes to the same-day additions: retry/alert rule split into availability vs content failures, with precedence; raw loses its `unique` test (staging dedupes; FM-09 makes per-day dedupe complete); staging reads only each hour's latest successful attempt, and drops rows by suppression → range → duplicate in that order; the build's window (§1) includes catch-up days; CI turns expiration off; FM-17…FM-20 added (late hour after build, killed ingest, failed build, dashboard); FM-07 alerts without freezing marts; FM-13 cutoff is per day; FM-14 checks before and after the load; FM-16 pending; R-01, R-02, R-06 and R-07 corrected; M-01 checksum excludes load columns; M-02 constraints; gini formula pinned; windows inclusive. |
