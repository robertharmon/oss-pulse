# oss-pulse — Cost Model

> What the pipeline costs to run, why it should stay at $0, and what would
> push it past that. Covers both GCP projects (dev and prod,
> [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md)), because they
> share one billing account and therefore **one set of free tiers**.
>
> **Status.** Volumes are measured (§2). Prices were checked against
> Google's live pricing pages on 2026-11-18 (§3). The four design changes in
> §8 are **proposals awaiting the author's approval**; until they're
> approved, the contract and architecture docs still describe the old
> design.

---

## 1. Bottom line

- **Expected spend: $0.00–0.20/month** through at least August 2027, once
  the §8 proposals are applied. The only likely charges are a few cents of
  Artifact Registry image storage, plus BigQuery storage if GH Archive
  volumes climb back to their October 2026 level.
- **Without the §8 changes, the pipeline breaks before it costs money.**
  An hourly `dbt build` with the contract's ~70 tests and four marts
  bills about 1.5–2.4 GB per run, half of it from BigQuery's 10 MB minimum
  per query. That's **35–56 GB/day against a 10 GB/day quota**, so dbt
  would start failing with `quotaExceeded` a few hours into every day.
- **The first scheduled cost increase is alerting.** Google plans to
  charge $0.35/month per log-based alert policy from **no sooner than
  2027-09-01**. Two or three policies would be about $0.70–1.05/month (§7).

## 2. Measured inputs

Measured 2026-11-18 against GH Archive's 2026-11-17 files (24/24 hours
present, each published at `:05:03`–`:05:04` past the next hour).

| Quantity | Value | How |
|---|---|---|
| Gzipped size per hour | 2.3–4.6 MB (87.7 MB/day) | `Content-Length` on all 24 hours |
| Events per hour | 2,531–3,671 (~87,000/day) | Line count, 3 hours (00, 13, 16 UTC) |
| Decompressed JSON | ×4.7 the gzipped size (~410 MB/day) | Same 3 hours |
| Share of bytes that is `payload` | **94%** | Same 3 hours |
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
| `fct_events` (~70 B/row) per year | 2.2 GB | 5.6 GB |

The `payload` share is the main lever: **storage cost is basically "how
long we keep raw payloads."** `fct_events` keeps only flags extracted from
the payload, so it stays small.

## 3. Prices and free tiers

All from Google's live pricing pages, fetched 2026-11-18, region
`us-central1`. **"Billing account" means dev and prod share the
allowance.**

| Service | Free each month | Scope | Price beyond free |
|---|---|---|---|
| BigQuery queries | 1 TiB billed bytes | Billing account | $6.25/TiB on-demand |
| BigQuery query minimum | — | — | **10 MB per table referenced and 10 MB per query** |
| BigQuery storage | 10 GiB | Billing account | Active logical $0.023/GiB-month, long-term $0.016. Physical (compressed) $0.04 / $0.02. |
| BigQuery batch loads from GCS | Free | — | — |
| BigQuery DML (`MERGE`, `INSERT`) | Counted as query bytes | — | A `MERGE` with `UPDATE`/`DELETE` bills the source **plus the target's touched partitions** |
| GCS Standard storage | 5 GB-month (us-central1, us-east1, us-west1 combined) | Billing account | $0.02/GiB-month |
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
[Free features](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Cloud Storage](https://cloud.google.com/storage/pricing),
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
accumulation of billed bytes"), so every query costs at least 10 MB of it
no matter how small the table. On a pipeline this size, **the number of
queries matters more than the amount of data.**

### 4.1 What one `dbt build` bills

| Part | Queries | Billed (Nov) | Billed (Oct-high) |
|---|---|---|---|
| Tests as written in the contract (~71: 40 `not_null`, 11 `unique`, 4 relationships, ranges, accepted values, singular, reconciliation) | ~71 | ~0.71 GB | ~0.71 GB |
| Same tests with §8.3 applied (NOT NULL enforced by BigQuery at write; ~30 tests left) | ~30 | ~0.30 GB | ~0.30 GB |
| 10 models, each ≥2 tables at the 10 MB minimum | ~10–20 | ~0.20 GB | ~0.20 GB |
| Staging, one day of raw (reads the `payload` column) | — | ~0.40 GB | ~1.0 GB |
| Marts (trending 14d, concentration 90d, time-of-day 30d, language month-to-date of `fct_events`) | — | ~0.55 GB | ~1.4 GB |

### 4.2 Cadence options (one day, prod)

| Option | What runs | Billed/day (Nov) | Billed/day (Oct-high) | Against 10 GB/day |
|---|---|---|---|---|
| **Contract as written** | Hourly full `dbt build` with all tests | ~35 GB | ~56 GB | **Fails daily** |
| Hourly full build, §8.3 applied | Same, ~30 tests | ~26 GB | ~47 GB | **Fails daily** |
| (B) Hourly staging + fact, daily marts | ~10 queries/hour + one daily full build | ~6 GB | ~8 GB | Fits, little headroom |
| **(A) Hourly ingest, daily full build (proposed)** | Ingest loads raw hourly (loads are free); one `dbt build` per day | **~1.5 GB** | **~3 GB** | Fits, room for replays |

Why (A) loses nothing a viewer can see: every mart is daily-grain. The
contract has `mart_trending_repos` "recomputed hourly with the latest full
day bucketed on the previous full UTC day," so 23 of 24 hourly rebuilds
would produce identical rows. The other three marts already have a 24h
freshness target. Raw keeps its 2h freshness, because ingest stays hourly.

### 4.3 Monthly query total vs the 1 TiB free tier (option A)

| Source | Nov | Oct-high |
|---|---|---|
| Prod daily build | ~45 GB | ~90 GB |
| Dashboard, cached 1h (§8.4): at most 24 × 4 queries × 10 MB a day | ≤30 GB | ≤30 GB |
| Dev and CI (fixture builds, roughly 4 runs × ~0.5 GB per PR, ~20 PRs/month) | ~40 GB | ~40 GB |
| **Total** | **~115 GB (11%)** | **~160 GB (16%)** |

### 4.4 Design rules that follow

These go into the ingest ADR and the dbt work:

- **Ingest writes with load jobs, never DML.** Loading the hour, and
  writing its `raw_ingest_audit` row, are free as load jobs. An `INSERT`
  would bill 10 MB per hour, 7 GB/month, for one row each time.
- **Reconcile from load-job statistics, not `COUNT(*)`.** The load job
  reports rows written. Comparing that with the line count costs nothing.
- **Partition every table a test or `MERGE` touches**, and set dbt tests'
  `where:` to the build's window. A `MERGE` bills the target's touched
  partitions; an unpartitioned target bills the whole table every run.
- **Replays and backfills draw on the same quota.** A replay is one hour
  of ingest (free) plus the next daily build. Backfill is in §5.3.

### 4.5 The per-user quota applies to everyone

BigQuery's `QueryUsagePerUserPerDay` is one number for the whole project,
applied to each identity separately. It can't be set "on the dashboard
identity" alone, as ADR 0002 and the access matrix imply. It still caps
the dashboard key, but at the same level as dbt. Proposed values (both
projects):

| Quota | Value | Why |
|---|---|---|
| `QueryUsagePerDay` | 10 GiB | DECISIONS §1; option A uses 15–30% of it |
| `QueryUsagePerUserPerDay` | 5 GiB | A leaked dashboard key can burn at most half the day's quota, which leaves dbt (needs ~1.5–3 GB) room to run |

Quotas reset at **midnight Pacific**, not UTC. Schedule the daily build
well clear of 07:00–08:00 UTC; the proposed time is 01:30 UTC.

## 5. Storage

### 5.1 Retention (proposed, §8.2)

| Data | Retention | Mechanism | Rebuild path if lost |
|---|---|---|---|
| GCS Parquet (`osp-raw-events-<env>`) | 14 days (dev: 7) | Bucket lifecycle rule | Re-download from GH Archive |
| `raw_gharchive_events` | 3 days | Partition expiration | Reload from GCS (free load job) or GH Archive |
| `stg_events` | 3 days | Partition expiration | Rebuilt from raw by the next build |
| `fct_events` | 400 days | Partition expiration | Rebuild from GH Archive (backfill, §5.3) |
| `stg_repos`, `stg_actors`, `dim_*` | Keep | — (one row per repo or actor) | Rebuild from `fct_events` window |
| `mart_*` | Keep | — (each is under a few MB) | Rebuild from `fct_events` |
| `raw_ingest_audit` | Keep | — (one row per hour) | Lost for good if the project is wiped (RUNBOOK §3.5) |

- **GCS is the recovery copy, BigQuery raw is the working copy.**
  Reloading an hour from GCS is a free load job, so raw only needs to hold
  what the daily build reads, plus margin for a two-day dbt outage.
- **`stg_events` is as big as raw,** because it keeps the full `payload`
  (contract §4.2). It gets raw's retention, not the fact table's.
- **400 days of `fct_events`** covers the 90-day concentration window and
  13 months of the month-over-month language chart.

### 5.2 Totals vs the free tiers

| | Nov | Oct-high | Free |
|---|---|---|---|
| BigQuery: raw 3d + `stg_events` 3d + `fct_events` 400d (at steady state, ~13 months in) + dims, marts, dev | ~6.3 GB | ~13.8 GB | 10 GiB (10.7 GB) |
| GCS: Parquet 14d (Zstandard) + dev | ~1.5 GB | ~3.3 GB | 5 GB |

At Oct-high volume and full 400-day `fct_events`, BigQuery storage would be
~3 GB over: **about $0.07/month**. Switching the datasets to physical
(compressed) storage billing would likely remove that, since raw JSON
compresses roughly 4–5×; the spike measures the real ratio (§9).

**Use Zstandard for Parquet.** Pyarrow's default (Snappy) makes the files
54% larger than GH Archive's own gzip. At 30 days of Oct-high volume that's
the difference between 6.5 GB and 10.1 GB in the bucket.

### 5.3 Backfill is limited by quota and retention

- **Retention:** loading an hour older than the raw table's 3-day
  partition expiration into that table deletes it right away. Backfill
  needs its own path (a temporary table without expiration, or loading and
  building one day at a time). The same applies to replaying an hour older
  than 3 days. That's for the ingest ADR.
- **Quota:** staging a backfilled day bills ~0.4 GB (Nov). 90 days is
  ~37 GB: about four days of the 10 GiB quota, or a temporary quota raise
  that only the author can make.

## 6. Everything else (option A, prod + dev)

| Service | Expected use | Share of free | Notes |
|---|---|---|---|
| Cloud Run | Ingest: 730 runs × ~20 s. dbt: 30 × ~5 min. Kill switch: ~0. ≈ 24,000 vCPU-s, 1 GiB each | ~13% | Runtimes are estimates; the spike measures ingest |
| Cloud Scheduler | 2 prod jobs (hourly ingest, daily dbt). **No dev jobs.** | 2 of 3 | A third job is the last free one. Paused jobs still count. |
| Secret Manager | Slack webhook record, GitHub token (language lookup): 2 prod, ≤1 dev | ≤3 of 6 versions | Old versions count while enabled: destroy them on rotation |
| Cloud Build | `--source` deploys after cutover, ~5 min each | <10% | — |
| Artifact Registry | Buildpack images for ingest and dbt (sizes unmeasured; Python + `dbt-bigquery` + `pyarrow` likely several hundred MB each) | Likely over 0.5 GB | **Cleanup policy: keep the 2 newest versions per image.** Expected overage $0.01–0.10/month |
| Cloud Logging | Tens of MB/month | <1% | Don't log per event |
| Pub/Sub | Budget notifications, KB/month | ~0% | — |
| GCS operations | ~730 writes + load reads per month, plus dev | <20% | — |

## 7. Guards: which one catches what

The guards are set in DECISIONS §1 and ADR 0002. This table is for checking
there's no gap.

| Runaway | Caught by | Lag |
|---|---|---|
| Query loop, hammered dashboard, bad backfill | Custom query quotas (§4.5) | Immediate (checked before each query, approximately) |
| Storage creep (retention left off) | Billing kill switch only. Quotas don't cover storage. | Hours to a day: budget notifications "may take several hours" |
| Cloud Run invocation loop | Kill switch. A native **spend cap budget** could also pause Cloud Run automatically. It doesn't cover BigQuery or span projects, so it can't replace the kill switch. Consider it at ADR 0002's review. | Same as above |
| Paid alerting from 2027-09 | Nothing automatic: it's a scheduled price change | Review this doc by **2027-08-01** |

**Retention must be checked, not assumed.** A B11 check should assert, in
Terraform: partition expiration on `raw_gharchive_events`, the lifecycle
rule on each data bucket, and the Artifact Registry cleanup policy.

## 8. Proposals awaiting the author

Each changes `docs/data_contract.md` or `docs/architecture.md`. Neither
file changes until the author approves.

1. **Cadence: hourly ingest, daily `dbt build` at 01:30 UTC** (option A,
   §4.2).
   - Contract: freshness of `stg_*`, `fct_events`, `dim_*` and
     `mart_trending_repos` goes from 2h to 26h. Raw stays at 2h.
   - Architecture: ingest stops invoking dbt. A second Scheduler job
     triggers dbt.
   - Alternative (B) keeps staging and the fact table hourly at ~4× the
     query use. Not recommended: nothing downstream reads them hourly.
2. **Retention** as in §5.1: GCS 14 days, raw and `stg_events` 3 days,
   `fct_events` 400 days, dimensions, marts and the audit table kept. This replaces "keep
   forever" in `architecture.md` §3.
3. **NOT NULL enforced by BigQuery, not tested by query.**
   - Raw columns marked `REQUIRED` in the Terraform schema, so the load job
     rejects nulls for free.
   - dbt models use `contract: enforced` with `not_null` constraints.
   - Removes ~40 test queries per build. Uniqueness, relationships and
     ranges stay as tests (BigQuery doesn't enforce them).
4. **Dashboard caches query results for 1 hour** (`st.cache_data(ttl=…)`).
   This replaces contract §6.1's "no caching layer in v1". Uncached, each
   page view bills 40 MB, so 250 views a day would use the whole project
   quota.

## 9. To measure in the milestone 2 dev spike

- Physical vs logical bytes for one day of raw, to choose the storage
  billing model.
- What `dbt build --empty` bills per model (whether the 10 MB minimum
  applies to zero-row queries).
- Billed bytes when staging reads one field (`payload.action`) from the
  `payload` JSON column: is the whole column billed?
- That BigQuery loads Zstandard-compressed Parquet.
- Ingest runtime and memory for one hour on Cloud Run.
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
| 2026-11-18 | Initial version (A11). Measured volumes, verified prices, query and storage model, four proposals (§8) pending author approval. |
