# oss-pulse — Cost Model

> What the pipeline costs to run, why it should stay at $0, and what would
> push it past that. Covers both GCP projects (dev and prod,
> [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md)), because they
> share one billing account and therefore **one set of free tiers**.
>
> **Status.** Volumes are measured (§2). Prices were checked against
> Google's live pricing pages on 2026-11-18 (§3). The four decisions in
> §8 were **approved by the author on 2026-11-18**. They change the data
> contract, architecture, access matrix and runbook, which are updated in
> follow-up PRs.

---

## 1. Bottom line

- **Expected spend: $0.00–0.15/month** until September 2027, once the §8
  proposals are applied. The only likely charges are a few cents of
  Artifact Registry image storage, plus BigQuery storage if GH Archive
  volumes climb back to their October 2026 level.
- **From no sooner than 2027-09-01: about +$0.35/month.** Google plans to
  start charging for alert policies, and the runbook's one log-based policy
  would cost $0.35/month (§7).
- **Without the §8 changes, the pipeline breaks before it costs money.**
  An hourly `dbt build` with the contract's ~66 tests and four marts bills
  at least 1.5–2.4 GB per run, half of it from BigQuery's 10 MB minimum
  per query. That's **35–56 GB/day against a 10 GiB/day quota**, so dbt
  would fail with `quotaExceeded` a few hours into every day.
- **The quotas alone keep queries free.** Dev and prod at 10 GiB/day each
  is at most 620 GiB in a 31-day month, under the shared 1 TiB free tier.
  Storage has no equivalent cap, so retention (§5) has to be enforced and
  checked.

## 2. Measured inputs

Measured 2026-11-18 against GH Archive's 2026-11-17 files (24/24 hours
present, each published at `:05:03`–`:05:04` past the next hour).

| Quantity | Value | How |
|---|---|---|
| Gzipped size per hour | 2.3–4.6 MB (87.7 MB/day) | `Content-Length` on all 24 hours |
| Events per hour | 2,531–3,671 (~75,000–85,000/day) | Line count, 3 hours (00, 13, 16 UTC), scaled by the day's bytes |
| Decompressed JSON | ×4.7 the gzipped size (~410 MB/day) | Same 3 hours |
| Share of bytes that is `payload` | **92%** | Same 3 hours |
| Parquet, Snappy (pyarrow default) | ×1.54 the gzipped size | Contract §4.1 columns, payload as a JSON string |
| Parquet, Zstandard | ×0.99 the gzipped size | Same |
| Event mix | `PullRequestEvent` ~42%, `IssuesEvent` ~17%, `IssueCommentEvent` 9–21%, `WatchEvent` 5–10%. Still no `PushEvent`. | Same |

**October 2026 was about 2.5× larger** (6.5–14.2 MB/hour gzipped, data
contract §3.2). This doc prices both: **Nov** (measured now) and **Oct-high**
(2.5×), so a volume rebound doesn't come as a surprise.

Derived volumes:

| Quantity | Nov | Oct-high |
|---|---|---|
| Raw BigQuery, logical bytes per day | 0.41 GB | 1.03 GB |
| Raw BigQuery, 3 days | 1.2 GB | 3.1 GB |
| Raw BigQuery, 30 days | 12.3 GB | 30.9 GB |
| GCS Parquet (Zstandard), 14 days | 1.2 GB | 3.0 GB |
| GCS Parquet (Snappy), 30 days | 4.0 GB | 10.1 GB |
| `fct_events` (~70 B/row), 400 days | ~2.3 GB | ~5.8 GB |

The `payload` share is the main lever: **storage cost is basically "how
long we keep raw payloads."** `fct_events` keeps only flags extracted from
the payload, so it stays small.

## 3. Prices and free tiers

All from Google's live pricing pages, fetched 2026-11-18, region
`us-central1`. **"Billing account" means dev and prod share the
allowance.**

| Service | Free each month | Scope | Price beyond free |
|---|---|---|---|
| BigQuery queries | 1 TiB billed bytes (1,099.5 GB) | Billing account | $6.25/TiB on-demand |
| BigQuery query minimum | — | — | **10 MB per table referenced and 10 MB per query** |
| BigQuery storage | 10 GiB | Billing account | Active logical $0.023/GiB-month, long-term $0.016. Physical (compressed) $0.04 / $0.02. |
| BigQuery batch loads from GCS | Free | — | — |
| BigQuery DML (`MERGE`, `INSERT`) | Counted as query bytes | — | A `MERGE` with `UPDATE`/`DELETE` bills the source **plus the target's touched partitions** (the whole target if it isn't partitioned) |
| GCS Standard storage | 5 GB-month (us-central1, us-east1, us-west1 combined) | Billing account | $0.02/GiB-month. Soft-deleted objects are billed too. |
| GCS operations | 5,000 Class A, 50,000 Class B | Billing account | — |
| Cloud Run (request-based) | 180,000 vCPU-s, 360,000 GiB-s, 2M requests | Billing account | $0.000024/vCPU-s |
| Cloud Scheduler | **3 jobs** (paused jobs count) | Billing account | $0.10/job per 31 days |
| Secret Manager | 6 active versions, 10,000 accesses | Billing account | $0.06/version-month |
| Cloud Build | 2,500 build-minutes (e2-standard-2, default pool) | Billing account | $0.006/min |
| Artifact Registry | **0.5 GB** | Billing account | $0.10/GiB-month |
| Cloud Logging | 50 GiB ingestion, 30-day retention | **Per project** | $0.50/GiB |
| Cloud Monitoring alerting | Not charged yet | — | From ≥ 2027-09-01: $0.35/month per metric reference; a log-based policy counts as one |
| Pub/Sub | 10 GiB throughput | Billing account | $40/TiB |
| Budgets, budget notifications | Free (notifications ride Pub/Sub) | — | — |

**Not GCP, and free:** GitHub Actions (public repo), Streamlit Community
Cloud, downloads from GH Archive (ingress is free).

Sources: [BigQuery pricing](https://cloud.google.com/bigquery/pricing),
[BigQuery custom quotas](https://docs.cloud.google.com/bigquery/docs/custom-quotas),
[DML pricing](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/dml-syntax),
[Partition expiration](https://docs.cloud.google.com/bigquery/docs/managing-partitioned-tables),
[Cached results](https://docs.cloud.google.com/bigquery/docs/cached-results),
[dbt incremental strategies](https://docs.getdbt.com/docs/build/incremental-strategy),
[Free features](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Cloud Storage](https://cloud.google.com/storage/pricing),
[GCS soft delete](https://docs.cloud.google.com/storage/docs/soft-delete),
[Cloud Run](https://cloud.google.com/run/pricing),
[Cloud Scheduler](https://cloud.google.com/scheduler/pricing),
[Secret Manager](https://cloud.google.com/secret-manager/pricing),
[Cloud Build](https://cloud.google.com/build/pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing),
[Observability](https://cloud.google.com/stackdriver/pricing),
[Pub/Sub](https://cloud.google.com/pubsub/pricing),
[Budget API](https://docs.cloud.google.com/billing/docs/how-to/budget-api-setup),
[Spend cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

## 4. Queries: the 10 MB minimum is the real budget

The daily custom quota counts **billed** bytes ("Query usage is an
accumulation of billed bytes"), so every query costs at least 10 MB of it,
no matter how small the table. On a pipeline this size, **the number of
queries matters more than the amount of data.**

### 4.1 What one daily `dbt build` bills (with §8 applied)

| Part | Billed (Nov) | Billed (Oct-high) |
|---|---|---|
| Tests: ~23 left after NOT NULL moves into the schema (§8.3); relationships tests reference two tables, so 20 MB each | ~0.27 GB | ~0.27 GB |
| Model statements: 10 models, `insert_overwrite` runs ~2 statements each at the 10 MB-per-table minimum | ~0.3 GB | ~0.3 GB |
| `stg_events`: one day of raw, including `payload` | ~0.41 GB | ~1.03 GB |
| `fct_events`: one day of `stg_events`, reading the extracted `payload_action` column, not the JSON | ~0.02 GB | ~0.05 GB |
| `dim_repos`, `dim_actors`: `MERGE` on unpartitioned tables bills the whole target (millions of rows by year one) | ~0.3 GB | ~0.6 GB |
| Marts: trending 14d, concentration 90d, time-of-day 30d, language month-to-date of `fct_events`, plus `dim_repos` for language | ~0.55 GB | ~1.4 GB |
| **Total** | **~1.9 GB** | **~3.7 GB** |

The contract as written (~66 tests, 43 of them `not_null`) adds ~0.45 GB
to each build.

### 4.2 Cadence options (one day, prod)

| Option | What runs | Billed/day (Nov) | Billed/day (Oct-high) | Against 10 GiB/day |
|---|---|---|---|---|
| **Contract as written** | Hourly full `dbt build` with all tests | ≥35 GB | ≥56 GB | **Fails daily** |
| Hourly full build, §8.3 applied | Same, ~23 tests | ≥26 GB | ≥47 GB | **Fails daily** |
| (B) Hourly staging + fact, daily marts | ~10 queries/hour + one daily full build | ~7 GB | ~9 GB | Barely fits |
| **(A) Hourly ingest, daily full build (proposed)** | Ingest loads raw hourly (loads are free); one `dbt build` per day | **~1.9 GB** | **~3.7 GB** | Fits, room for replays |

The hourly rows are lower bounds: they leave out the incremental-write and
dimension costs from §4.1.

Why (A) loses nothing a viewer can see: every mart is daily-grain. The
contract has `mart_trending_repos` "recomputed hourly with the latest full
day bucketed on the previous full UTC day," so 23 of 24 hourly rebuilds
would produce identical rows. The other three marts already have a 24h
freshness target. Raw keeps its 2h freshness, because ingest stays hourly.

### 4.3 Monthly query total vs the 1 TiB free tier (option A)

| Source | Nov | Oct-high |
|---|---|---|
| Prod daily build | ~57 GB | ~111 GB |
| Dashboard (§8.4: each mart's latest partition, loaded once, cached) | ~1 GB | ~1 GB |
| Dev and CI (fixture builds, roughly 4 runs × ~0.5 GB per PR, ~20 PRs/month) | ~40 GB | ~40 GB |
| **Total** | **~100 GB (9%)** | **~150 GB (14%)** |

### 4.4 Design rules that follow

These go into the ingest ADR and the dbt work. They aren't contract
changes, so they don't need approval, but each one is a cost bug if it's
missed:

- **Ingest writes with load jobs, never DML.** Loading the hour, and
  writing its `raw_ingest_audit` row, are free as load jobs. An `INSERT`
  would bill 10 MB per hour, 7 GB/month, for one row each time.
- **Reconcile from load-job statistics, not `COUNT(*)`.** The load job
  reports rows written. Comparing that with the line count costs nothing.
- **Partitioned incremental models use `insert_overwrite`, not `merge`.**
  dbt's `merge` strategy scans the whole destination table for the unique
  key (~0.45 GB a day on a 400-day `fct_events` at Nov volume). Replacing
  whole partitions only bills the partitions it touches. If a model has to
  use `merge`, it sets `incremental_predicates` to its window.
- **Extract `payload_action` once, in `stg_events`.** Every later model
  reads that column, not the JSON. Reading one field from a JSON column
  may bill the whole column (§9 measures this).
- **Snapshot marts are partitioned on `as_of_date`, and the dashboard
  filters on a literal date.** Filtering through a `MAX(as_of_date)`
  subquery doesn't prune partitions, so it bills the whole table.
- **Dashboard queries avoid `CURRENT_DATE()` and other non-deterministic
  functions.** Those disable BigQuery's free result cache.
- **No standing lookback window in the daily build.** The build rebuilds
  yesterday plus only the days that changed or failed since their last
  build (contract §1, FM-17), found from `raw_ingest_audit`. That costs a
  day's staging per changed day, instead of re-reading three days of
  payload every day.
- **`full_refresh: false` on `fct_events`, the dims and the snapshot
  marts.** With 3-day staging, a full refresh would rebuild 400 days of
  history from 3 days of data and wipe the rest.
- **Scheduler → dbt timeouts:** Scheduler's HTTP `attempt_deadline`
  (default 180 s, max 30 min) and the Cloud Run request timeout (default
  300 s) must both exceed the build time. Keep `retry_count` at 0, or a
  retry starts a second full build.

### 4.5 Quota values

BigQuery's `QueryUsagePerUserPerDay` is one number for the whole project,
applied to each identity separately. It can't be set "on the dashboard
identity" alone. It caps the dashboard's key at the same level as dbt, so
the value has to leave dbt room to run while still stopping a leaked key
from taking the whole day. Proposed:

| Quota | Prod | Dev | Why |
|---|---|---|---|
| `QueryUsagePerDay` | 10 GiB | 10 GiB | DECISIONS §1. Together that's at most 620 GiB a month, under the 1 TiB free tier. |
| `QueryUsagePerUserPerDay` | 6 GiB | 10 GiB (same as project) | Prod: dbt needs ~1.9–3.7 GB, and a leaked dashboard key still leaves ~4 GiB for it. Dev: only the builder and CI query it, so a lower per-user value would just cap the builder. |

Quotas reset at **midnight Pacific**, not UTC. The proposed build time,
01:30 UTC, is well clear of the reset (07:00–08:00 UTC).

## 5. Storage

### 5.1 Retention (proposed, §8.2)

| Data | Retention | Mechanism | Rebuild path if lost |
|---|---|---|---|
| GCS Parquet (`osp-raw-events-<env>`) | 14 days (dev: 7) | Bucket lifecycle rule, **soft delete off** | Re-download from GH Archive |
| `raw_gharchive_events` | 3 days | Partition expiration | Reload from GCS (free load job) or GH Archive |
| `stg_events` | 3 days | Partition expiration | Rebuilt from raw by the next build |
| `fct_events` | 400 days | Partition expiration; `full_refresh: false` | Backfill from GH Archive (§5.3) |
| `stg_repos`, `stg_actors` | Rolling 3-day window | Rebuilt each build | Rebuilt from `stg_events` |
| `dim_repos`, `dim_actors` | Keep | `full_refresh: false` | Backfill. `fct_events` has no `repo_name` or `actor_login`, so dims can't be rebuilt from it. |
| `mart_trending_repos`, `mart_contributor_concentration` | 30 days of daily snapshots | Partition expiration on `as_of_date` | Rebuild from `fct_events` |
| `mart_language_share`, `mart_time_of_day_activity` | Keep (small: months × languages, languages × hours × buckets) | — | Rebuild from `fct_events` |
| `raw_ingest_audit` | Keep | — (one row per hour) | Lost for good if the project is wiped (RUNBOOK §3.5) |

- **GCS is the recovery copy, BigQuery raw is the working copy.**
  Reloading an hour from GCS is a free load job, so raw only needs to hold
  what the daily build reads, plus margin for a two-day dbt outage.
- **`stg_events` is as big as raw,** because it keeps the full `payload`
  (contract §4.2). It gets raw's retention, not the fact table's.
- **400 days of `fct_events`** covers the 90-day concentration window and
  13 months of the month-over-month language chart.
- **The two snapshot marts grow ~1–6 MB a day** (one row per active repo
  per day). 30 days of snapshots keeps the chart's history without letting
  them grow forever.
- **GCS soft delete is on by default** (7 days, billed). With it, the
  bucket would really hold ~21 days of files. Data buckets set it to 0;
  the files are re-derivable anyway.
- **Time travel:** raw and staging datasets set the time-travel window to
  its 2-day minimum. It's free under logical billing but billed under
  physical billing (§9).

### 5.2 Totals vs the free tiers

| | Nov | Oct-high | Free |
|---|---|---|---|
| BigQuery: raw 3d + `stg_events` 3d + `fct_events` 400d (steady state, ~13 months in) + dims + marts + dev | ~6.4 GB | ~14.0 GB | 10 GiB (10.7 GB) |
| GCS: Parquet 14d (Zstandard) + dev | ~1.5 GB | ~3.3 GB | 5 GB |

At Oct-high volume and a full 400-day `fct_events`, BigQuery storage would
be ~3.3 GB over: **about $0.08/month**. Physical (compressed) storage
billing might remove that, since raw JSON compresses roughly 4–5×. But
physical billing also charges for time travel and the 7-day fail-safe, and
raw and staging turn over 0.4–1 GB a day. §9 measures before choosing.

**Use Zstandard for Parquet.** Pyarrow's default (Snappy) makes the files
54% larger than GH Archive's own gzip. At 30 days of Oct-high volume that's
the difference between 6.5 GB and 10.1 GB in the bucket.

### 5.3 Backfill is limited by retention and quota

- **Retention:** BigQuery expires a partition immediately if it's older
  than the table's expiration when it's written. Loading a 60-day-old hour
  into raw (3-day expiration) deletes it on arrival, and the same happens
  to its `stg_events` partition. Backfill needs a separate path: a
  temporary raw table and staging model without expiration, or raising the
  expiration for the duration of the backfill. Replaying any hour older
  than 3 days hits the same limit. The ingest ADR picks the method.
- **Quota:** staging a backfilled day bills ~0.4 GB (Nov). 90 days is
  ~37 GB of staging alone. At the 6 GiB per-user cap, that's 7 or more
  days of builds, or a temporary quota raise that only the author can make.

## 6. Everything else (option A, prod + dev)

| Service | Expected use | Share of free | Notes |
|---|---|---|---|
| Cloud Run | Ingest: 730 runs × ~20 s. dbt: 30 × ~5 min. Kill switch: ~0. ≈ 24,000 vCPU-s, 1 GiB each | ~13% | Runtimes are estimates; §9 measures ingest |
| Cloud Scheduler | 2 prod jobs (hourly ingest, daily dbt). **No dev jobs.** | 2 of 3 | A third job is the last free one. Paused jobs still count. |
| Secret Manager | Prod: Slack webhook record, plus a GitHub token if the language lookup (contract §5.7, option A) is chosen. Dev: none (access matrix §3). | ≤2 of 6 versions | Old versions count while enabled: destroy them on rotation |
| Cloud Build | `--source` deploys after cutover, ~5 min each | <10% | — |
| Artifact Registry | Buildpack images for ingest and dbt (sizes unmeasured; Python + `dbt-bigquery` + `pyarrow` likely several hundred MB each), plus the kill-switch function's image in each project | Likely over 0.5 GB | Terraform creates `cloud-run-source-deploy` itself, with a **keep-2-newest cleanup policy**, so `--source` doesn't auto-create it without one. The kill switch's `gcf-artifacts` repo is auto-created and needs the same policy added after its first deploy. Expected overage $0.01–0.10/month. |
| Cloud Logging | Tens of MB/month | <1% | Don't log per event |
| Pub/Sub | Budget notifications, KB/month | ~0% | — |
| GCS operations | ~730 writes + load reads per month, plus dev | <20% | — |

## 7. Guards: which one catches what

The guards are set in DECISIONS §1 and ADR 0002. This table checks that
there's no gap.

| Runaway | Caught by | Lag |
|---|---|---|
| Query loop, hammered dashboard, bad backfill | Custom query quotas (§4.5) | Immediate (checked before each query, approximately) |
| Storage creep (retention left off, soft delete on, snapshot marts unpartitioned) | Billing kill switch only. Quotas don't cover storage. | Hours to a day: budget notifications "may take several hours" |
| Cloud Run invocation loop | Kill switch. A native **spend cap budget** could also pause Cloud Run automatically. It doesn't cover BigQuery or span projects, so it can't replace the kill switch. Consider it at ADR 0002's review. | Same as above |
| Paid alerting from 2027-09 | Nothing automatic: it's a scheduled price change. One log-based policy is $0.35/month. | Review this doc by **2027-08-01** |

**Retention must be checked, not assumed.** A B11 check should assert, in
Terraform and dbt config:
- partition expiration on `raw_gharchive_events`, `stg_events`,
  `fct_events` and the two snapshot marts;
- the lifecycle rule and zero soft-delete retention on each data bucket;
- the Artifact Registry cleanup policy;
- `full_refresh: false` on the models in §5.1.

## 8. Decisions (approved 2026-11-18)

Each changes docs that the author owns. All four were approved as written
below; the follow-up PRs apply them to those docs.

1. **Cadence: hourly ingest, daily `dbt build` at 01:30 UTC** (option A,
   §4.2).
   - Contract: freshness of `stg_*`, `fct_events`, `dim_*` and
     `mart_trending_repos` goes from 2h to **28h**. A build covers up to
     the previous UTC day. Just before the next build finishes (~01:35),
     the newest `event_hour` (23:00 two days back) is ~26.6h old. 28h
     leaves margin for a late hour 23. Raw stays at 2h.
   - Contract: `stg_events` gains a `payload_action` column (additive);
     snapshot marts are partitioned on `as_of_date`.
   - Architecture §3/§4: ingest stops invoking dbt. A second Scheduler job
     triggers dbt. "One job per environment" becomes two in prod.
   - Access matrix §4.2: the Scheduler identity gets `run.invoker` on the
     dbt service; ingest's grant to invoke dbt goes away.
   - Runbook §3.1 (replay): add "run `dbt build --vars '{run_date: …}'`"
     after re-ingesting, since nothing triggers dbt after a replay any more.
   - Runbook §2 / monitoring: raw's 2h freshness test now runs once a day,
     so **a stalled ingest (Scheduler paused or deleted) goes unnoticed for
     up to ~24h.** Ingest failures still alert within the hour; only "ingest
     never ran" is slower. Closing that gap needs a metric-absence alert:
     a second policy, +$0.35/month from 2027-09.
   - Alternative (B) keeps staging and the fact table hourly at ~4× the
     query use. Not recommended: nothing downstream reads them hourly.
2. **Retention** as in §5.1: GCS 14 days with soft delete off, raw and
   `stg_events` 3 days, `fct_events` 400 days, snapshot marts 30 days,
   dims and the small marts kept, and `full_refresh: false` on the
   long-lived models. This replaces "keep forever" in `architecture.md` §3.
3. **NOT NULL enforced by BigQuery, not tested by query.**
   - The raw table's non-nullable contract columns are `REQUIRED` in the
     Terraform schema, and ingest's pyarrow schema marks them
     `nullable=False` (pyarrow's default is nullable, which BigQuery
     rejects against a `REQUIRED` column).
   - dbt models use `contract: enforced` with `not_null` constraints.
   - Removes 43 test queries per build (~0.45 GB). Uniqueness,
     relationships and ranges stay as tests; BigQuery doesn't enforce them.
   - **Behavior change:** a null in a required raw field now fails the
     whole hour's load (fail-fast, DECISIONS §6). Today the contract has
     staging drop such rows and catch them in a test (§3.3, architecture
     §4.5). The hour is retried on the next run and alerts after 3 tries,
     like a missing hour.
4. **Dashboard: one query per chart per refresh, cached.** Each chart
   loads its mart's latest partition by literal date, filters and sorts in
   pandas, and caches the result with `st.cache_data(ttl=3600)`. This
   replaces contract §6.1's "one `SELECT` per chart on page load; no
   caching layer in v1".
   - The risk was smaller than first estimated: BigQuery's own result
     cache is free and lasts until the table changes (once a day). The
     real risk is per-viewer parameters (date ranges, top-N) in SQL,
     because each variant is a separate cache entry. Pandas filtering
     removes that.

## 9. To measure in the milestone 2 dev spike

- Physical vs logical bytes for one day of raw, including time-travel and
  fail-safe bytes (`INFORMATION_SCHEMA.TABLE_STORAGE`), to choose the
  storage billing model.
- What `dbt build --empty` bills per model (whether the 10 MB minimum
  applies to zero-row queries).
- Bytes billed when staging reads `payload.action` from the `payload` JSON
  column: is the whole column billed? Read `total_bytes_billed` from the
  finished job, not a dry run; a dry run reports the whole column as an
  upper bound.
- That BigQuery loads Zstandard-compressed Parquet, and rejects a nullable
  pyarrow field against a `REQUIRED` column (so §8.3's ingest schema is
  tested).
- Ingest runtime and memory for one hour on Cloud Run, and the dbt build
  time (sets the §4.4 timeouts).
- Buildpack image sizes for ingest and dbt.

Each result updates §2–§6 with a change-log row.

## 10. Cost attribution

- **Labels on every resource** (Terraform): `app=oss-pulse`,
  `env=dev|prod`, `component=ingest|dbt|dashboard|killswitch|terraform`,
  `managed_by=terraform`. Billing reports filter on them.
- **Labels on every BigQuery job.** dbt-bigquery's `query-comment` with
  `job-label: true` labels dbt jobs; ingest and the dashboard set
  `component` on their jobs. Bytes billed per component then comes from
  `INFORMATION_SCHEMA.JOBS` (one query, 10 MB).
- **No billing export to BigQuery** in v1. It would add a table that grows
  every day, to answer a question the labels already answer.

## 11. Review date

Review by **2027-08-01**, before alerting charges can start. Review earlier
if:
- GH Archive volume returns to the Oct-high range or beyond.
- Either project's quota is hit outside a planned backfill.
- Any month's invoice is above $0.50.

## 12. Change log

| Date | Change |
|---|---|
| 2026-11-18 | Initial version (A11). Measured volumes, verified prices, query and storage model, four proposals (§8). Revised after independent review: incremental-write and dimension costs, snapshot-mart growth, GCS soft delete, backfill expiration, full-refresh guard, 28h freshness, per-user quota 6 GiB. |
| 2026-11-18 | §8 proposals approved by the author (option A cadence, retention, NOT NULL in schema, dashboard load-once + cache). |
