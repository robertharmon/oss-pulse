# oss-pulse — Architecture

> How the pieces committed to in [ADR 0001](adr/0001-tech-stack.md) fit
> together. A reader of this doc should be able to trace a single
> GitHub event from GH Archive to a chart on the Streamlit dashboard
> without opening any other file.
>
> This doc describes the **target** architecture. The repo is currently
> in the foundation phase ([`FOUNDATION_BACKLOG.md`](../FOUNDATION_BACKLOG.md));
> no components below exist yet. The point of writing this now is so
> every subsequent PR has something concrete to be consistent with.

---

## 1. The system in one paragraph

Once an hour, Cloud Scheduler pings a Cloud Run service. The service
downloads the previous hour's GH Archive file (one gzipped line-delimited
JSON file, ~0.5–1 GB, holding every public GitHub event for that hour),
converts it to Parquet, and writes it to a GCS bucket. A second Cloud
Run invocation then loads that Parquet file into a raw BigQuery table.
A third Cloud Run invocation runs `dbt build`, which transforms the raw
table through staging and intermediate models into analytical marts
(trending repos, language share, contributor concentration, time-of-day
patterns). A Streamlit app hosted on Streamlit Community Cloud queries
the mart tables directly and renders four charts. If any step fails or
if a dbt test fails, Cloud Logging triggers a Slack webhook. Everything
except the GCP project and billing is defined in Terraform; everything
secret lives in Secret Manager.

## 2. The diagram

```
                      ┌───────────────────────────┐
                      │  https://gharchive.org/   │
                      │  (public, no auth, hourly │
                      │   .json.gz drops, ~0.5GB) │
                      └─────────────┬─────────────┘
                                    │ HTTPS GET
                                    │ (one URL per hour)
                                    ▼
   ┌──────────────────┐   invokes   ┌───────────────────────────────┐
   │ Cloud Scheduler  │────────────▶│ Cloud Run: ingest             │
   │ cron "5 * * * *" │             │ (Python 3.11 in Docker)       │
   │ (one job)        │             │  1. fetch gharchive .json.gz  │
   └──────────────────┘             │  2. stream-decode JSON lines  │
                                    │  3. write Parquet to GCS      │
                                    │  4. call BQ load job          │
                                    │  5. invoke dbt-run service    │
                                    └──────────────┬────────────────┘
                                                   │
                      ┌────────────────────────────┼──────────────────────┐
                      │ writes                     │ load                 │ invokes
                      ▼                            ▼                      ▼
         ┌──────────────────────┐    ┌──────────────────────┐   ┌──────────────────────┐
         │ GCS                  │    │ BigQuery             │   │ Cloud Run: dbt       │
         │ osp-raw-events-<env> │───▶│ osp_raw_<env>        │   │ (Python 3.11 image   │
         │  gharchive/          │    │  .raw_gharchive_     │   │   with dbt-bigquery) │
         │   year=YYYY/         │    │   events             │   │  runs `dbt build`    │
         │   month=MM/          │    │ (hourly partitioned, │   │  against the dataset │
         │   day=DD/            │    │  clustered on        │   │  below               │
         │   hour=HH.parquet    │    │  repo_id)            │   └──────────┬───────────┘
         └──────────────────────┘    └──────────────────────┘              │ builds
                                                                           ▼
                                                        ┌────────────────────────────────┐
                                                        │ BigQuery                       │
                                                        │ osp_staging_<env>              │
                                                        │   stg_events, stg_repos,       │
                                                        │   stg_actors                   │
                                                        │     │                          │
                                                        │     ▼                          │
                                                        │ osp_analytics_<env>            │
                                                        │   fct_events, dim_repos,       │
                                                        │   dim_actors,                  │
                                                        │   mart_trending_repos,         │
                                                        │   mart_language_share,         │
                                                        │   mart_contributor_concentr.,  │
                                                        │   mart_time_of_day_activity    │
                                                        └──────────────┬─────────────────┘
                                                                       │ SELECT (read-only
                                                                       │  BigQuery API,
                                                                       │  service-account
                                                                       │  key via Streamlit
                                                                       │  secrets)
                                                                       ▼
                                                        ┌────────────────────────────────┐
                                                        │ Streamlit Community Cloud      │
                                                        │ dashboard/app.py               │
                                                        │   4 charts, 1 per mart table   │
                                                        └────────────────────────────────┘

   ──────────────────────────── cross-cutting ────────────────────────────

   Observability:  every Cloud Run invocation → Cloud Logging → log-based
                   alert policy on ERROR → Slack webhook (osp_slack_
                   webhook_url in Secret Manager).  dbt test failures
                   non-zero-exit the dbt Cloud Run job → same alert path.

   Infra-as-code:  everything inside the diagram above (buckets, datasets,
                   service accounts, scheduler jobs, Cloud Run services,
                   log sinks, alert policies, secrets as empty shells) is
                   defined in terraform/*.tf.  The ONLY things outside
                   Terraform are the GCP project itself, billing linkage,
                   the Terraform remote-state bucket, and the real secret
                   *values* loaded into Secret Manager.

   Secrets:        Secret Manager holds the Slack webhook URL and the
                   Streamlit dashboard's BigQuery service-account JSON.
                   Cloud Run reads secrets at invocation; GitHub Actions
                   authenticates to GCP via Workload Identity Federation
                   (no long-lived keys in the repo or in GH secrets).

   CI/CD:          GitHub Actions runs lint/typecheck/test/terraform-plan
                   on every PR; `terraform apply` runs on merge to main.
                   dbt and ingest images are built and pushed to Artifact
                   Registry on merge; Cloud Run always pulls `:main`.
```

## 3. Component responsibilities

Each component has one job. If a change feels like it belongs to two,
that's a signal to re-read this section before writing it.

| Component | Owns | Does NOT own |
|---|---|---|
| **GH Archive** (external) | Being the source of truth for public GH events. Hourly `.json.gz` files at a predictable URL. | Reliability guarantees. Occasional missing hours are expected and handled downstream. |
| **Cloud Scheduler** | Firing the ingest job once per hour on a fixed cron. One job per environment. | Retries (Cloud Run handles retry); any logic beyond "invoke the URL". |
| **Cloud Run: ingest** | Fetching one hour's `.json.gz`, converting to Parquet, writing to GCS, triggering the BQ load, then triggering the dbt build. Fails fast on any non-2xx, malformed JSON, or zero rows. | Transformation logic (that's dbt). Scheduling (that's Cloud Scheduler). |
| **GCS: `osp-raw-events-<env>`** | Durable archive of the raw Parquet files. Partitioned by `year=/month=/day=/hour=`. Lifecycle: keep forever at the free-tier size we'll hit. | Serving queries directly — all analytics go through BigQuery. |
| **BigQuery: `osp_raw_<env>`** | The raw landing table (`raw_gharchive_events`). Hourly-partitioned, clustered on `repo_id`. Columns mirror the gharchive JSON schema one-to-one; no transformation. | Any business logic. Any aggregation. |
| **Cloud Run: dbt** | Running `dbt build` against the raw dataset: staging → intermediate → marts, plus tests. One container image, same `dbt-bigquery` project. | Scheduling; invoked by the ingest service once the load completes. |
| **BigQuery: `osp_staging_<env>`** | Views/tables that rename, cast, and lightly clean raw columns. One `stg_<entity>` per raw entity (`stg_events`, `stg_repos`, `stg_actors`). | Business metrics. Joins beyond deduplication. |
| **BigQuery: `osp_analytics_<env>`** | Facts (`fct_events`), dimensions (`dim_repos`, `dim_actors`), and the four `mart_*` tables that answer the README's four questions. | Row-level raw data (goes to staging). Any ad-hoc exploration (that's for notebooks against the raw table). |
| **Streamlit app** | Four charts, one per mart table. One `.py` file, read-only BigQuery access. | Any data transformation beyond chart-level filtering (sort, top-N, date range). If logic is creeping in, it belongs in a mart. |
| **Secret Manager** | Holding the Slack webhook URL and the Streamlit service-account JSON. Rotation on a schedule. | Any config value that isn't secret — those are env vars on Cloud Run, set via Terraform. |
| **Cloud Logging + alert policy** | Catching ERROR-level logs from any Cloud Run service or a dbt test failure, and firing the Slack webhook. | Dashboarding ops metrics beyond "did it fail." |
| **Terraform** | Every GCP resource except the project itself, billing, and the state bucket. | GH Archive (external). The dashboard host (Streamlit Community Cloud is configured out-of-band). |

## 4. Trace one record end-to-end

A single GitHub event — say, a `WatchEvent` (star added) by actor
`octocat` on repo `octocat/hello-world` at `2026-10-05T14:23:17Z` —
walks the pipeline like this. The timestamps are illustrative but
anchored to real cron behavior.

### 4.1 Birth (external, 14:23:17 UTC)

GitHub's public events firehose emits the event. GH Archive, which
tails that firehose, writes it as one JSON line into the hour's
accumulating file:

```
https://data.gharchive.org/2026-10-05-14.json.gz
```

The JSON looks roughly like:

```json
{"id":"47301238871","type":"WatchEvent","actor":{"id":583231,"login":"octocat",...},
 "repo":{"id":1296269,"name":"octocat/hello-world","url":"..."},
 "payload":{"action":"started"},"public":true,"created_at":"2026-10-05T14:23:17Z"}
```

The file closes at 15:00:00 UTC and becomes immutable.

### 4.2 Fetch (15:05 UTC, Cloud Scheduler fires)

Cloud Scheduler, cron `5 * * * *`, invokes the ingest Cloud Run
service's `POST /run` endpoint with `{"hour": "2026-10-05-14"}` in the
body. The 5-minute offset gives GH Archive time to finish writing.

### 4.3 Download + convert (ingest service)

The service:

1. `GET`s `https://data.gharchive.org/2026-10-05-14.json.gz`. Non-2xx raises
   (fail-fast per `DECISIONS.md` §6). Zero-byte body raises.
2. Streams the gzip through a line-by-line JSON decoder (never
   materialises the whole file in memory).
3. Writes rows to a Parquet file in a temp dir using the schema fixed in
   `ingest/schema.py`. Our `WatchEvent` becomes one row:
   `event_id="47301238871", event_type="WatchEvent", actor_id=583231,
    actor_login="octocat", repo_id=1296269, repo_name="octocat/hello-world",
    payload_action="started", created_at=2026-10-05T14:23:17Z`.
4. Uploads the Parquet file to
   `gs://osp-raw-events-prod/gharchive/year=2026/month=10/day=05/hour=14.parquet`.
5. Issues a BigQuery load job pointing at that file, appending to
   `osp_raw_prod.raw_gharchive_events` with `partition=2026-10-05-14`.
   Schema mismatch raises (fail-fast).

### 4.4 Land in raw (BigQuery load, ~15:06 UTC)

The row lands in `osp_raw_prod.raw_gharchive_events`, partition
`2026-10-05-14`, cluster-key `repo_id=1296269`. The row is now
queryable but has not been transformed.

### 4.5 Transform (dbt build, Cloud Run: dbt, ~15:06–15:08 UTC)

Ingest finishes by invoking the dbt Cloud Run service. `dbt build`
runs:

1. **Staging** — `stg_events` selects from `raw_gharchive_events`
   WHERE partition date = yesterday-through-today, renames and casts
   columns, drops any row that fails a `not_null` on `event_id`,
   `repo_id`, or `created_at`. Our row survives.
2. **Dimensions** — `dim_repos` upserts `(1296269, 'octocat/hello-world',
   first_seen, last_seen)`; `dim_actors` upserts
   `(583231, 'octocat', first_seen, last_seen)`.
3. **Fact** — `fct_events` inserts one row keyed on `event_id`:
   `(47301238871, 'WatchEvent', 583231, 1296269, '2026-10-05T14:23:17Z')`.
4. **Marts** — the four `mart_*` models recompute (fully or
   incrementally, per model config):
   - `mart_trending_repos` — a 7-day rolling count of `WatchEvent`,
     `PullRequestEvent`, `PushEvent` per repo, with week-over-week
     delta. `octocat/hello-world`'s star count ticks up by 1.
   - `mart_language_share` — unchanged by this event (no language
     signal in a `WatchEvent`).
   - `mart_contributor_concentration` — unchanged (not a commit event).
   - `mart_time_of_day_activity` — the hour-14 bucket for the repo's
     primary language ticks up by 1.
5. **Tests** — every model's `not_null`, `unique`, and freshness tests
   run. A failure fails the build (non-zero exit) and triggers the
   alert path; downstream models do not run.

### 4.6 Serve (Streamlit app, on next page view)

A visitor opens the dashboard. The Streamlit app opens a BigQuery
client (`with bigquery.Client() as client:` per `DECISIONS.md` §7),
issues four `SELECT`s — one per mart table — and renders four charts:

- **Trending repos this week** — a bar chart; `octocat/hello-world`'s
  bar is 1 taller than it was an hour ago.
- **Language contributor share** — a stacked area chart; unchanged by
  this event.
- **Contributor concentration per repo** — a histogram; unchanged.
- **Time-of-day activity patterns** — a heatmap; the (hour=14,
  language=primary-of-hello-world) cell is 1 brighter.

Total latency from event-time to dashboard-visible: ~45 minutes in the
median case (event at :23 → GH Archive closes at :00 → scheduler fires
at :05 → load+dbt done by :08 → next page view).

## 5. Data flow summary

The record moves through five stages, each with a fixed interface:

| Stage | Interface | What crosses | Fail-fast check |
|---|---|---|---|
| 1. GH Archive → ingest | HTTPS GET of `.json.gz` | gzipped JSONL | HTTP 2xx; non-zero file size |
| 2. ingest → GCS | GCS write | Parquet file | Row count > 0; schema matches |
| 3. GCS → BigQuery raw | BQ load job | columnar rows | Schema matches `raw_gharchive_events` |
| 4. raw → marts (dbt) | SQL `ref()` graph | tables + views | Every model's `not_null`/`unique` tests pass |
| 5. marts → Streamlit | BigQuery `SELECT` | query results | Mart exists; non-empty for the queried window |

If stage N fails, stages N+1…5 don't run for that hour. The hour's
data is missing from the dashboard until the hour is replayed (manual
re-trigger of the ingest service with the same `{"hour": ...}` body —
the pipeline is idempotent on hour).

## 6. Failure boundaries

Where failures stop, who notices, and what gets rerun.

| Failure | Stops at | How it's noticed | Recovery |
|---|---|---|---|
| GH Archive 404 (missing hour) | ingest Cloud Run | Cloud Logging ERROR → Slack webhook | Wait; GH Archive sometimes republishes late. If still missing after N hours, log a RUNBOOK entry and move on — the hour is lost. |
| GH Archive 5xx (transient) | ingest Cloud Run (first try) | Cloud Run auto-retries 3× | Usually self-heals. Alert fires only after all retries exhausted. |
| GCS write fails (quota, IAM) | ingest Cloud Run | ERROR + alert | Fix IAM / quota in Terraform; re-trigger ingest for the affected hour. |
| BQ load schema mismatch | ingest Cloud Run (step 5) | ERROR + alert | Means GH Archive changed its schema. Update `ingest/schema.py` and `raw_gharchive_events` DDL via a PR; backfill from GCS Parquet (which succeeded). |
| dbt model fails to build | dbt Cloud Run | Non-zero exit → ERROR + alert | Fix the model in a PR; re-run `dbt build` manually. Marts stay stale, dashboard shows last successful run. |
| dbt test fails (`not_null`, `unique`, freshness) | dbt Cloud Run | Non-zero exit → ERROR + alert | Investigate: real data issue or test too strict? Either patch upstream or relax the test — both via PR. |
| Streamlit can't reach BigQuery | dashboard | Visitor sees "data unavailable" (per `DECISIONS.md` §6: user-facing surfaces degrade, not raise) | Check Streamlit secrets; rotate the service-account key via Secret Manager. |

Note: **nothing retries silently past the Cloud Run layer.** Cloud
Run's own retry policy handles transient HTTP flaps; everything above
that is explicit and alerted.

## 7. Security boundaries

What can read/write what. The full matrix lands in `docs/access_matrix.md`
(backlog A8); this is the summary.

- **GH Archive (external):** public, no auth, read-only.
- **GCS `osp-raw-events-<env>`:** writable only by the ingest
  service account (`osp-ingest-<env>@...`). Readable by that SA and
  by the dbt SA (`osp-dbt-<env>@...`). No public access, no human
  developer access in `prod` — read access to `prod` goes through a
  separate reviewer SA.
- **BigQuery datasets:**
  - `osp_raw_<env>`: write = ingest SA, read = dbt SA + dashboard SA.
  - `osp_staging_<env>` and `osp_analytics_<env>`: write = dbt SA, read
    = dashboard SA + reviewer SA.
- **Streamlit app → BigQuery:** uses the `osp-dashboard-<env>` SA
  which has `roles/bigquery.dataViewer` on `osp_analytics_<env>` only.
  Cannot see raw or staging data.
- **GitHub Actions → GCP:** Workload Identity Federation. No
  long-lived keys. The federation is scoped to the specific repo and
  branch.
- **Secret Manager:** only the Cloud Run services that need a secret
  can read it. Written by Terraform (as empty shells) and populated
  manually with real values once per secret, out-of-band.
- **Human (Robert) access:** `Owner` on the GCP project (unavoidable,
  solo). Day-to-day work uses `gcloud auth application-default login`
  which issues short-lived credentials; no service-account key JSON
  files on the laptop.

All data in the pipeline is **public** (GH Archive is a public
re-publishing of GitHub's public events firehose). There is no PII,
no proprietary data, no regulatory classification. The IAM strictness
above is practice, not a legal requirement.

## 8. What this doc doesn't cover

Pointers so a reader knows where else to look.

- **Why these tools** → [`ADR 0001`](adr/0001-tech-stack.md).
- **Locked operating decisions** (region, environments, naming,
  secrets policy, fail-fast philosophy, resource-management
  convention, scope boundaries) → [`DECISIONS.md`](../DECISIONS.md).
- **Column-level data contracts** (grain, columns, freshness per mart)
  → `docs/data_contract.md` (backlog A7, not yet written).
- **Full IAM matrix** → `docs/access_matrix.md` (backlog A8, not yet
  written).
- **Runbook / on-call** → `RUNBOOK.md` (backlog A9, not yet written).
- **Cost model** → `docs/cost_model.md` (backlog A11, not yet
  written).

## 9. Review date

Revisit when any of:

- The first ingest-to-dashboard end-to-end run completes (Phase D). The
  trace in §4 will have real numbers to replace the illustrative ones.
- A component boundary moves (e.g., ingest and dbt collapse into a
  single Cloud Run service, or an orchestrator replaces Cloud
  Scheduler).
- A new source or environment is added — both require ADRs under
  `DECISIONS.md` §10.

Otherwise, re-read alongside ADR 0001 at its scheduled 2027-04-05
checkpoint.
