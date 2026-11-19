# ADR 0003 — Ingest and build run as Cloud Run jobs; schedule, retries and backfill

> **Status:** Proposed
> **Date:** 2026-11-19
> **Authors:** Robert Harmon

## Context

The data contract fixes *what* ingest and the daily build must do: the
retry/alert rule (§3.3), the audit table (§4.5), the build's window with
catch-up days (§1), and the 70-hour replay limit (FM-13). The cost model
fixes *how often* and *how cheaply*: hourly ingest, a daily build at
01:30 UTC, load jobs only, no standing lookback (§4.4). Four things were
left to this ADR (roadmap M3, contract §8, architecture §8):

1. **What runs them:** a Cloud Run *service* (an HTTP server Scheduler
   calls) or a Cloud Run *job* (a task that runs to completion).
2. **The Scheduler minute.** GH Archive files went live at
   `:05:03`–`:05:04` past the hour on every hour sampled (contract §3.2,
   24/24 on 2026-11-17), so `:05` has no margin.
3. **The backfill window and its path.** v1 needs at least 30 days of
   history at launch (roadmap §1.1). Raw and `stg_events` expire
   partitions after 3 days, so a load of an older hour is deleted on
   arrival (cost model §5.3).
4. **Timeouts and retries** at the Scheduler and Cloud Run layers.

## Decision

### 1. Both run as Cloud Run jobs

| | Ingest: `osp-ingest-<env>` | Build: `osp-dbt-<env>` |
|---|---|---|
| Trigger | Scheduler `15 * * * *` (UTC) | Scheduler `30 1 * * *` (UTC) |
| What one execution does | Ingests the previous hour, then retries every hour from the last 24 with no success and fewer than 3 failed scheduled attempts (contract §3.3) | `dbt build` for the build's window: yesterday plus catch-up days (contract §1) |
| Task timeout | 15 minutes | 60 minutes |
| Retries (Cloud Run `max-retries`) | 0: ingest retries inside its run, and the next hourly run retries hours | 0: a retry would start a second full build |
| Resources | 1 vCPU, 1 GiB (revisited after the M3 runtime measurement) | 1 vCPU, 2 GiB |
| Deploy | `gcloud run jobs deploy --source` (DECISIONS §10) | same |

- **Scheduler calls the job's `:run` API** with an OAuth token for
  `osp-scheduler-prod`, which needs `roles/run.invoker` on each job (the
  role that executes jobs). The call returns as soon as the execution
  starts, so Scheduler's `attempt_deadline` no longer has to outlast the
  build (cost model §4.4's timeout rule becomes moot).
- **Replays and backfills** are executions started by the author with
  argument overrides (`gcloud run jobs execute … --args=…`). The
  Scheduler identity never passes overrides.

### 2. Ingest fires at `:15`

Ten minutes after files have gone live in every sample. If GH Archive is
late, the hour fails as FM-01/FM-02 and is retried by the next run; a
later minute would only add latency to every hour to save a retry on a
rare one.

### 3. Backfill: 35 days, through a temporarily widened raw window

At the cutover, before v1's 14-day clock starts:

1. The author widens the partition expiration of `raw_gharchive_events`
   (Terraform variable) and `stg_events` (dbt variable) to 40 days.
2. Ingest runs as one job execution with `trigger=backfill` and one task
   per hour, in parallel (`CLOUD_RUN_TASK_INDEX` picks the hour): 840
   tasks for 35 days. Each writes its audit row as usual.
3. The author temporarily raises the per-user query quota so the build
   can stage all 35 days in one run (about 14 GB at November volumes,
   36 GB at October-high, against a 6 GiB normal cap).
4. The next build's catch-up rule finds every backfilled day "never built
   successfully" and builds them (contract §1). No separate backfill code
   path in dbt.
5. The author restores both expirations to 3 days and the quota to 6 GiB.
   Raw and staging partitions older than 3 days expire on their own;
   `fct_events` keeps them (400 days).

FM-13's 70-hour limit applies to `trigger=replay`, not `trigger=backfill`,
which is only valid while the window is widened.

## Alternatives considered

- **Cloud Run services** (the architecture's original shape). An HTTP
  server in each image; a 60-minute request limit; Scheduler's deadline
  and the service timeout both had to outlast the build. Request-based
  billing has a smaller free tier (180,000 vCPU-seconds, vs 240,000 for
  jobs). No benefit for work that nobody calls interactively.
- **Ingest as a service, dbt as a job.** Mixed shapes for no gain; the
  same replay story twice.
- **Scheduler minute `:10`.** Five minutes of margin over a one-day
  sample; `:15` costs ten minutes of latency on a daily-built dashboard,
  which nobody sees.
- **90-day backfill.** Fills `mart_contributor_concentration`'s 90-day
  window from day one. 2.6× the quota and download; v1 only asks for 30
  days, and the window fills itself within two months of running.
- **A separate backfill table and staging path.** Never touches the
  normal tables' expiration, but adds a second raw table and a second
  staging route that tests must cover forever, for a once-only event.

## Consequences

**Positive:**
- No web-server code in either image; each is a plain run-to-completion
  program.
- Backfill parallelizes for free, and reuses the normal audit and
  catch-up rules.
- Larger free tier; Scheduler's timeout no longer matters.

**Negative / cost:**
- Starting a job execution takes longer than a warm HTTP request (tens of
  seconds). Irrelevant at hourly and daily cadence.
- The backfill needs three temporary author changes (two expirations and
  a quota), each reverted afterwards. The cutover runbook lists them as
  one checked step each.
- Docs to update when this is accepted: architecture (§2, §3: "service
  or job" → job), access matrix (Scheduler's grant is `run.invoker` on
  two jobs), cost model (§4.4 timeout rule; §6 Cloud Run row uses the
  jobs free tier), contract FM-19 ("request timeout" → "task timeout"),
  RUNBOOK §3.1 (replay command).

## Review date

At the cutover, with measured ingest runtime and build time.

## References

- Data contract §1, §3.2–§3.3, §4.5, FM-13, FM-17…FM-19.
- Cost model §4.4, §5.3, §6.
- Google Cloud: [Execute jobs on a schedule](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule), [Cloud Run pricing](https://cloud.google.com/run/pricing), [Build and create a Python job](https://cloud.google.com/run/docs/quickstarts/jobs/build-create-python).
