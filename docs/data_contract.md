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

### 3.3 Known failure modes

Each has a defined handling pattern. Fail-fast at ingest
([`../DECISIONS.md`](../DECISIONS.md) §6) with alerts routing per
[`architecture.md`](architecture.md) §6.

| Failure | Signal | Handling |
|---|---|---|
| **Missing hour (404)** — rare; §3.2 found 72/72 hours present | HTTP 404 at the hourly URL past N+65 | Record the miss in `raw_ingest_audit` (hour, 404 timestamp, retry count), retry on the next scheduled runs, and **alert if the hour is still missing after 3 attempts** (≈3 hours). Since misses are rare, each one is worth a look. Downstream models skip gaps; the dashboard renders missing hours as blank, not errors. |
| **Late hour (published after N+65)** | 404 at scheduled fetch, 200 at manual retry | Manual re-trigger of the ingest service with the same `{"hour": …}` body. Pipeline is idempotent on hour. |
| **Transient 5xx** | HTTP 5xx on first try | Cloud Run auto-retries 3×. If all retries fail, alert; same recovery as missing hour. |
| **Truncated file** | gzip decode error or JSON parse error mid-stream | Fail-fast raises; alert fires. Re-trigger manually once GH Archive republishes. |
| **Schema drift (new event type)** | New `event_type` value appears in `stg_events` | Non-fatal at raw layer (we store the raw JSON); staging dedupe + mart logic may silently ignore it. Add an `accepted_values` dbt test on `event_type` so new types surface as test failures within a day. |
| **Schema drift (new field in payload)** | New key inside `payload` JSON | Raw layer preserves `payload` as a JSON column; new fields are invisible to downstream models until explicitly extracted. No action needed unless a mart wants the new field. |
| **Schema drift (removed field)** | Expected top-level field becomes NULL across the hour | Fail-fast: ingest asserts the first record contains `id`, `type`, `actor`, `repo`, `created_at`. Missing any raises. Partial-row drops (one field goes away) surface as `not_null` test failures in staging within the hour. |
| **Zero-byte file** | `Content-Length: 0` or gzip-decoded empty body | Fail-fast raises at ingest; alert fires. Usually a GH Archive publication glitch; manually re-trigger once GHA republishes. |

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
- **Freshness target:** newest `event_hour` within 2h of now (allows
  for the scheduler offset + ingest runtime + alert fatigue margin).
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

- **Tests:** `not_null` on every non-nullable column; `unique` on
  `event_id`; freshness check per the target above.

### 4.2 `osp_staging_<env>.stg_events`

- **Grain:** one row per deduplicated event — `event_id` is unique.
- **Writer:** dbt. Reads `raw_gharchive_events`.
- **Readers:** dbt (fact/mart layer); never read by dashboards.
- **Materialization:** incremental on `event_hour`.
- **Freshness target:** same as raw (2h).
- **Columns:** same shape as raw, with these transformations:
  - `event_type` is `accepted_values`-tested (see §4.3).
  - `created_at` is cast and verified to be within a sane window
    (`BETWEEN TIMESTAMP("2015-01-01") AND CURRENT_TIMESTAMP() +
    INTERVAL 1 HOUR`); rows outside the window are dropped and
    counted in a load-audit view.
  - `payload` stays as JSON; mart models extract fields they need.
- **Tests:** `not_null` on `event_id`, `event_type`, `repo_id`,
  `actor_id`, `created_at`; `unique` on `event_id`; `accepted_values`
  on `event_type`.

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
- **Freshness:** 2h.
- **Tests:** `not_null` on PK; `unique` on PK; relationship test from
  `stg_events` to each.

Both exist so dim tables don't scan `raw_gharchive_events` directly.

---

## 5. Marts — the four contract-bearing tables

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
- **Freshness:** 2h.
- **Columns:** `event_id` (PK), `event_type`, `event_hour`,
  `created_at`, `actor_id` (FK → `dim_actors`), `repo_id` (FK →
  `dim_repos`), plus event-type-specific flags extracted from
  `payload`:
  - `is_star` (BOOL) — `event_type = 'WatchEvent'`.
  - `is_pr_opened` (BOOL) — `event_type = 'PullRequestEvent'` AND
    `payload.action = 'opened'`.
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
- **Freshness:** 2h.
- **Tests:** `not_null` and `unique` on PK.

### 5.3 `mart_trending_repos`

**Answers:** README Q1 — repos with the largest week-over-week increase
in stars or PRs. (README originally said "stars, PRs, or pushes";
`pushes_*` columns are omitted because `PushEvent` is absent from the
feed — see §4.3. README wording drift tracked in §8.)

- **Grain:** one row per `(repo_id, as_of_date)` — a daily snapshot of
  each repo's 7-day rolling counts.
- **Freshness:** 2h (recomputed hourly with the latest full day
  bucketed on the previous full UTC day).
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `repo_id` | INT64 | FK → `dim_repos`. |
  | `as_of_date` | DATE | Snapshot day. |
  | `stars_7d` | INT64 | WatchEvent count over 7 days ending `as_of_date`. |
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
- **Freshness:** 24h — the mart updates once per day; the dashboard
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
- **Freshness:** 24h.
- **Columns:**

  | Column | Type | Notes |
  |---|---|---|
  | `repo_id` | INT64 | FK → `dim_repos`. |
  | `as_of_date` | DATE | Snapshot day. |
  | `distinct_pr_openers_90d` | INT64 | Distinct `actor_id` with `is_pr_opened = true` on this repo over trailing 90 days. |
  | `total_prs_opened_90d` | INT64 | Count of `is_pr_opened` events on this repo over trailing 90 days. |
  | `gini` | FLOAT64 | Gini coefficient of PR-opens per actor over trailing 90 days. 0 = perfectly even, 1 = one actor did everything. |
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
- **Freshness:** 24h.
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

## 6. Downstream — Streamlit dashboard

### 6.1 Consumer

- **App:** `dashboard/app.py` on Streamlit Community Cloud.
- **Reads:** the four `mart_*` tables in §5. Nothing else.
- **Auth:** `osp-dashboard-<env>` service account, `roles/bigquery.
  dataViewer` on `osp_analytics_<env>` only (per
  [`architecture.md`](architecture.md) §7).
- **Access pattern:** one `SELECT` per chart on page load; no caching
  layer in v1.

### 6.2 SLA to the viewer

- **Freshness:** matches the slowest mart feeding each chart (2h for
  trending, 24h for the other three).
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
- **README wording drift.** The four questions in `../README.md` were
  written assuming `PushEvent` was in the feed. With `PushEvent`
  absent (§4.3), three of them now have mart contracts that differ
  from the README phrasing: Q1 drops "pushes", Q3 counts PR-openers
  rather than commit authors, Q4 drops "commit" from the bucket set.
  The README is not part of this PR; a follow-up docs PR should
  reconcile the two before any mart is actually built. Logged as a
  separate line in `../OPEN_LOOPS.md`.
- **Backfill window.** How far back do we backfill when first lighting
  the pipeline? Likely answered by the first ingest ADR; parked.
- **PII posture.** `actor_login` is a GitHub handle — public, but
  identifiable. The security doc (backlog A12) will cover
  classification; this contract treats everything as public.
- **GitHub token for language lookup (§5.7).** Which account issues
  the token, where it rotates. Parked until `dim_repos` is built.

---

## 9. Change log

| Date | Change |
|---|---|
| 2026-10-07 | Initial version. Covers upstream (GH Archive), raw + staging layers, four mart contracts, Streamlit consumer, change-management rules. Closes A7. |
| 2026-10-07 | §3.2 replaced order-of-magnitude guesses with measurements from a 6-hour sample on 2026-10-07; added §3.2.1 (method) and a scheduler-margin note. Added §8 item for the scheduler offset. |
| 2026-10-07 | Follow-up measurement run (32,602 rows across 5 hours + 11 off-peak HEADs) drove: §3.2 availability downgraded to ~55% measured, file-size and row-count ranges widened; §3.3 missing-hour upgraded from edge case to hot path (non-alerting by default); §4.1 added `org_id`, `org_login`, `is_public`; §4.3 added `DiscussionEvent` to the whitelist and noted PushEvent/CreateEvent/DeleteEvent/SponsorshipEvent as absent-but-whitelisted; §5.1 removed `is_push`/`push_commit_count`, re-derived PR flags from `payload.action` (the measured discriminator); §5.3 replaced `pushes_*` columns with `prs_opened_*` + `prs_merged_*`; §5.5 redefined the mart around PR-opening actors (PushEvent-based commit metric unbuildable); §5.6 replaced `push` bucket with `issue_opened` + `star`; §8 added README-wording-drift item. |
| 2026-11-11 | §3.1 URL pattern corrected to an unpadded hour (`-5`, not `-05`); §2 notes the project's own hour stays padded. §3.2 availability corrected from ~55% to 72/72 present: the earlier 404s came from padded URLs (§3.2.1 correction + re-check). §3.3 missing hour downgraded from routine to rare, now alerting after 3 failed attempts instead of a trailing-24h miss-rate threshold. |
| 2026-11-11 | §5.4 `distinct_contributors` / `total_contributors_this_month` redefined on PR-opened or PR-merged events (the old definition still referenced the absent `PushEvent`); noted shares can sum past 100%. §5.1 `is_pr_merged` re-verified against 3 fresh hours (`merged` action confirmed present) and noted that a merge event's actor is the merger, not the author. |
