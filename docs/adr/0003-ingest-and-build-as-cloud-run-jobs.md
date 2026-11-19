# ADR 0003 — Ingest and build run as Cloud Run jobs; schedule, retries and backfill

> **Status:** Proposed
> **Date:** 2026-11-18
> **Authors:** Robert Harmon

## Context

The data contract fixes *what* ingest and the daily build do: the
retry/alert rule (§3.3), the audit table (§4.5), the build's window with
catch-up days (§1), the replay limit (FM-13). The cost model fixes *how
often* and *how cheaply*: hourly ingest, a daily build at 01:30 UTC, load
jobs only, no standing lookback (§4.4), and quotas of 10 GiB/day per
project and 6 GiB/day per identity (§4.5). Left open (roadmap M3, contract
§8, architecture §8):

1. **What runs them:** a Cloud Run *service* (an HTTP server Scheduler
   calls) or a Cloud Run *job* (a task that runs to completion).
2. **The Scheduler minute.** GH Archive files went live at
   `:05:03`–`:05:04` on every hour sampled (contract §3.2), so `:05` has
   no margin.
3. **Timeouts and retries** at the Scheduler and Cloud Run layers.
4. **The backfill window and its path.** v1 needs at least 30 days of
   history (roadmap §1.1). Raw and `stg_events` expire partitions after 3
   days, and BigQuery expires a partition immediately if it's already
   older than that, so old hours can't go through the normal tables.

## Decision

### 1. Both run as Cloud Run jobs

| | Ingest: `osp-ingest-<env>` | Build: `osp-dbt-<env>` |
|---|---|---|
| Scheduler | `15 * * * *` UTC | `30 1 * * *` UTC |
| One execution | The previous hour, then every hour from the last 24 with no success and fewer than 3 failed scheduled attempts (contract §3.3) | `dbt build` for the build's window (§3 below) |
| Task timeout | 15 minutes | 60 minutes |
| Cloud Run `max-retries` | 0 (ingest retries inside its run; the next run retries hours) | 0 (a retry would start a second build) |
| Scheduler `retry_count` | 0 | 0 |
| Resources | 1 vCPU, 1 GiB (revisited after M3's runtime measurement) | 1 vCPU, 2 GiB |
| Deploy | `gcloud run jobs deploy --source`, entrypoint set with `--command` | same |

- **Scheduler calls the job's `:run` API** with an OAuth token for
  `osp-scheduler-prod`, which holds `roles/run.invoker` on each job. That
  role runs a job but can't pass overrides, which is what we want: the
  scheduled path takes no arguments. The call returns once the execution
  starts, so no Scheduler deadline has to outlast the work.
- **Replays and backfills** are executions the author starts with
  argument overrides (`gcloud run jobs execute … --args=…`), using the
  author's own login.
- **Ingest writes only with load jobs** (the hour's rows, and its audit
  row) and reconciles from load-job statistics (cost model §4.4).

### 2. Ingest fires at `:15`

Ten minutes after files went live in every sample. A late file fails as
FM-01/FM-02 and the next run retries it; a later minute would add latency
to every hour to save a retry on a rare one.

### 3. Backfill: 35 days, through its own table, built a few days a night

**Path.** With `trigger=backfill`, ingest loads into
`osp_raw_<env>.raw_gharchive_events_backfill`: the same schema as raw,
**no partition expiration**. Ingest creates it on first use (its
`dataEditor` grant allows that) and the author drops it once every
backfilled day is built and balances. No expiration, quota or Terraform
setting changes.

**Staging becomes a view.** `stg_events` changes from an incremental
table kept 3 days to a **view** over raw ∪ backfill, applying the same
rules (latest successful attempt per hour, suppressions, range,
duplicates). A materialized `stg_events` would expire old backfilled days
the moment they were written. The view reads the same raw bytes the
incremental model did, and saves its 1.2–3.1 GB of storage. Its dedupe
partitions by `(event_hour, event_id)`, which is equivalent because copies
of an event share an hour (FM-09), and lets date filters prune raw's
partitions.

**Execution.** One task per day (35 tasks), each ingesting its 24 hours in
order with the normal in-run retries, at most 5 tasks at a time. That keeps
load jobs on each table to well under BigQuery's 1,500 per table per day,
and their rate under its metadata-update limit, and stays gentle on GH
Archive. Re-running the execution skips hours that already succeeded.

**Getting every hour to an end state.** A backfill hour is retried by
re-running the backfill until it has succeeded or has 3 failed attempts
(any trigger) since its last success. The 3rd failure logs `ERROR` and
alerts, and the hour is recorded as given up (contract FM-01: a lost hour
is lost). **A backfilled day is eligible for the build only when all 24 of
its hours are in an end state**, so one stuck hour can't fail every
night's build.

**Building it within quota.** The build's window becomes: yesterday, plus
**at most 4 catch-up days, oldest first**. At October-high volumes that's
about 5 GB a build, under the 6 GiB per-identity quota; at November
volumes, about 2.6 GB. A 35-day backfill then builds itself over about 9
nights with no quota change. (The author may raise both quotas for a day
to go faster; nothing depends on it.) Snapshot marts are rebuilt for the
latest `as_of_date` only; backfilled days feed them through `fct_events`.

**Guard against silent loss.** Before loading an hour, ingest reads the
target table's partition expiration (`tables.get`, free) and refuses an
hour that would expire on arrival, whatever the trigger. This generalizes
FM-13.

**At the cutover:** a 2-day trial backfill first, then the full 35 days.
v1's 14-day clock starts when the last backfilled day has built and
balanced.

### 4. Contract changes this needs (applied after approval)

- §1: the build's window (yesterday + at most 4 eligible catch-up days,
  oldest first; backfilled days eligible only when all hours are in an end
  state); backfill table; R-07's "given up" counts failed attempts of any
  trigger.
- §4.2: `stg_events` is a view; no retention of its own.
- §4.5: `raw_ingest_audit.trigger = 'backfill'` rows target the backfill
  table.
- FM-13: refuse any hour that would expire on arrival; FM-19: "task
  timeout", not "request timeout"; FM-07: "the dbt job".

## Alternatives considered

- **Cloud Run services.** An HTTP server in each image, a 60-minute
  request limit, and a Scheduler deadline that must outlast the build.
  Request-billed services get 180,000 free vCPU-seconds against jobs'
  240,000. No benefit for work nobody calls interactively.
- **Widen raw and staging expiration during the backfill, then restore.**
  The first draft. It needed both quotas raised by hand, an `ALTER TABLE`
  or Terraform change twice, and a gate before restoring (lowering an
  expiration deletes older partitions immediately); and dbt likely sets
  `stg_events`' expiration only when it creates the table. Too many manual
  steps, each able to lose data.
- **One task per hour (840 tasks).** Would hit BigQuery's per-table
  metadata-update rate on the audit table, and a same-day re-run would
  approach 1,500 load jobs on each table.
- **Scheduler minute `:10`.** Five minutes of margin on a one-day sample.
- **90-day backfill.** Fills `mart_contributor_concentration`'s 90-day
  window from day one, but takes ~23 nights at the 4-day cap (or a quota
  raise), and v1 only needs 30 days. The window fills itself within two
  months of running.

## Consequences

**Positive:**
- No web-server code; each image is a plain run-to-completion program.
- Backfill reuses the normal ingest, audit, staging and catch-up paths. No
  settings to change and change back.
- Every build stays within quota by construction, backfill or not.
- `stg_events` no longer stores a duplicate of raw.

**Negative / cost:**
- Starting a job execution takes tens of seconds longer than a warm HTTP
  call. Irrelevant at hourly and daily cadence.
- The backfill is slow (~9 nights for 35 days at the cap).
- The backfill table holds ~14 GB (November) to 36 GB (October-high) until
  dropped, over the 10 GiB free tier for a week or two: a few cents. GCS
  gets 3–8 GB more for 14 days: also cents.
- `stg_events` as a view re-applies its rules on each read; the build reads
  it a few times a day (`fct_events`, the staging dimensions, tests).
- First real run is in prod: dev has no Cloud Run (access matrix §3).
  Hence the 2-day trial.

**Docs to update after approval:** the contract (§4 above); the
architecture (§2, §3: jobs, the backfill table, the staging view);
DECISIONS §10 (`gcloud run jobs deploy --source`); the access matrix
(a `run-job:` scope type for the diff script; Scheduler's `run.invoker`
on two jobs; "service" → "job" in §2 and §5); the cost model (§3 jobs free
tier, §4.4 timeout rule now moot, §5.1 `stg_events` retention, §5.3
backfill, §6 Cloud Run row); the roadmap (M7 "deploys both jobs"); the
runbook (§1 alert filter for job logs, §3.1 replay command, a backfill
procedure).

## Review date

At the cutover, with measured ingest runtime, build time, and the trial
backfill.

## References

- Data contract §1, §3.2–§3.3, §4.1–§4.5, FM-13, FM-17…FM-19, R-07.
- Cost model §4.1–§4.5, §5.1–§5.3, §6.
- Google Cloud: [Execute jobs on a schedule](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule),
  [Execute jobs](https://docs.cloud.google.com/run/docs/execute/jobs),
  [Cloud Run IAM roles](https://docs.cloud.google.com/iam/docs/roles-permissions/run),
  [Cloud Run pricing](https://cloud.google.com/run/pricing),
  [Cloud Run quotas](https://docs.cloud.google.com/run/quotas),
  [max-retries](https://docs.cloud.google.com/run/docs/configuring/max-retries),
  [container contract](https://docs.cloud.google.com/run/docs/container-contract),
  [Build and create a Python job](https://docs.cloud.google.com/run/docs/quickstarts/jobs/build-create-python),
  [Managing partitioned tables](https://docs.cloud.google.com/bigquery/docs/managing-partitioned-tables),
  [BigQuery quotas](https://docs.cloud.google.com/bigquery/quotas).
