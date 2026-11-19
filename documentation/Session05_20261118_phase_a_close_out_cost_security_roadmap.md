# Session 05 — Phase A Close-Out: Cost Model, Security, Ways of Working, Roadmap, Contract IDs

**Date:** 2026-11-18
**Status:** Complete (Phase A done; M1 has one item left)
**Focus:** Record the author's two pending decisions, then finish the
foundation documents:
- A11 cost model;
- A12 security posture;
- A13 ways of working;
- A10 roadmap;
- the contract's failure-mode IDs, balancing counts and metamorphic
  relations.

Every document went through an independent review agent before merge.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Author Decisions](#2-author-decisions)
3. [Measurements](#3-measurements)
4. [A11 Cost Model](#4-a11-cost-model)
5. [A12 Security Posture](#5-a12-security-posture)
6. [A13 Ways of Working and A10 Roadmap](#6-a13-ways-of-working-and-a10-roadmap)
7. [Contract Additions](#7-contract-additions)
8. [Independent Review Results](#8-independent-review-results)
9. [Decisions and Rejections](#9-decisions-and-rejections)
10. [Open Items at Session End](#10-open-items-at-session-end)
11. [ELI5 Topics This Session](#11-eli5-topics-this-session)
12. [Files Changed](#12-files-changed)

---

## 1. Overview

**Starting point.** The author asked for the project's status, and then
said to keep building on `build/agentic`. The author also answered the
two open questions:
- Q1: commits are authored by Robert even when the bot pushes them;
- the promotion method: no per-milestone promotions to `main`.

**Arc of the session:**
1. Recorded both decisions (PR #17), and fixed the README's questions to
   match the contract (PR #18).
2. Measured current GH Archive volumes, and had an agent verify GCP prices
   against live pricing pages.
3. Wrote the cost model (A11). Its central finding changed the
   architecture: an hourly dbt build can't fit the daily query quota. The
   author approved four decisions, which were then applied to the
   contract, access matrix and runbook (PRs #19, #20).
4. Wrote the security posture (A12, PR #21), ways of working (A13, PR #22)
   and roadmap (A10, PR #23).
5. Added stable IDs to the contract for failure modes, balancing counts
   and input/output relations (PR #24).
6. The author approved all of it. Phase A is complete (PR #25).

The author also asked twice for plainer explanations: what "rebuilt
everything every hour" meant, and what "everything" was. The answer was
the ten dbt tables plus ~66 test queries, each billed at least 10 MB.

## 2. Author Decisions

| Question | Decision |
|---|---|
| Commit authorship when the bot pushes (QUESTIONS Q1) | (a) Commits are authored as Robert; the bot only pushes and opens PRs. |
| How `build/agentic` reaches `main` | Once, at the end, with "Rebase and merge". `main` stays frozen at `baseline-pre-agentic` as a fallback snapshot. Milestones get `m<N>-done` tags, reviewed as compare ranges. |
| Cadence | Ingest hourly; one `dbt build` a day at 01:30 UTC. |
| Retention | GCS 14 days (soft delete off); raw and `stg_events` 3 days; `fct_events` 400 days; snapshot marts 30 days; dimensions and small marts kept. |
| NOT NULL | Enforced by the BigQuery schema (`REQUIRED`, `contract: enforced`), not by 43 test queries. |
| Dashboard | Each chart loads its mart once, filters in pandas, caches for 1 hour. |
| Great Expectations | Kept, as ingest's in-memory batch validation (the only implementation of those rules). |
| `primary_language` | Looked up from GitHub's API, cached in `dim_repos`, refreshed weekly. Design in an M4 ADR. |
| Merge point | `build/agentic` merges into `main` **before** the cutover, because prod can only deploy from `main`. |
| v1 definition | Four charts live with ≥30 days of history; 14 days in a row without manual intervention; a full calendar month's invoice of $0.00–0.50; all gates green; runbook exercised; README passes a 5-question test. |
| A13, A10, contract additions | Approved as written after review. |

## 3. Measurements

All on 2026-11-18, against GH Archive's 2026-11-17 files.

| Quantity | Value |
|---|---|
| Hours present | 24/24, each published at `:05:03`–`:05:04` past the next hour |
| Gzipped size | 2.3–4.6 MB/hour; 87.7 MB/day (about 2.5× smaller than October) |
| Events | 2,531–3,671/hour; ~75,000–85,000/day |
| Decompressed | ×4.7 the gzipped size |
| `payload` share of bytes | 92% |
| Parquet size vs gzip | Snappy ×1.54; Zstandard ×0.99 |
| Events outside their file's hour | 0 of 9,291 (3 hours) |
| Duplicate `event_id`s | 0 (same 3 hours) |
| `PushEvent` | Still absent |

One download of hour 00 stopped at 1.76 of 4.57 MB on our side; a retry
was complete. It became failure mode FM-04 (truncated download).

## 4. A11 Cost Model

**The finding that changed the design:**
- **BigQuery bills at least 10 MB per query, and per table referenced.**
- **The daily custom quota counts *billed* bytes, so the minimum counts
  against it.**
- **An hourly `dbt build` with ~66 tests billed about 1.5–2.4 GB per run.**
  That's 35–56 GB a day against a 10 GiB quota. The pipeline would have
  stopped every day long before costing money.

**Other findings:**
- **Raw storage is mostly payloads,** so retention sets storage cost.
  "Keep forever" passes the shared 10 GiB free tier within months.
- **Dev and prod share one billing account,** and therefore one set of
  free tiers, for almost every service.
- **The two projects' quotas cap query spend by themselves:**
  10 + 10 GiB/day is at most 620 GiB a month, under the 1 TiB free tier.
  Storage has no such cap.
- **Expected spend:** $0.00–0.15/month, plus ~$0.35/month for one alert
  policy once Google starts charging for alerting (no sooner than
  2027-09-01).
- **Spend cap budgets** now exist. They can pause Cloud Run, but don't
  cover BigQuery, so the kill switch stays.

**What the review changed** (2 blockers):
- dbt's default `merge` strategy scans the whole target table, so the
  design moved to `insert_overwrite`.
- The snapshot marts grow by MB per day, so they're now partitioned and
  keep 30 days.
- Smaller fixes:
  - GCS soft delete adds 7 hidden days of storage;
  - a full refresh would wipe 400 days of facts;
  - backfills load into already-expired partitions;
  - freshness has to be 28h, not 26h;
  - the per-user quota applies to every identity, and is now 6 GiB.

## 5. A12 Security Posture

**Content:**
- Data classes per source.
- A personal-data posture: no individual actors on the dashboard.
- GH Archive free text treated as hostile input, including for agents.
- A full credential inventory with rotation.
- The dashboard key as the one key file. DECISIONS §5 was amended to name
  it, along with the other secrets that live outside Secret Manager.
- Audit logging, supply chain, `SECURITY.md`, and private vulnerability
  reporting.

**What the review changed** (2 blockers):
- **The bot could reach the prod dashboard key indirectly.** Streamlit
  lets anyone with Write on the repo manage the app. What stops the agent
  is that only the author holds the bot's web login; the doc now says so,
  with a check at each milestone.
- **Removal requests didn't stick.** Deleted rows would come back on the
  next build. They now use `actor_suppressions` and `repo_suppressions`
  seeds, filtered in staging.
- **Also:**
  - the Slack webhook became an environment secret on protected branches;
  - the language token is issued by the author, not the bot;
  - rotations get tracked;
  - the agent sharing the author's Windows account is named as a known
    risk.

## 6. A13 Ways of Working and A10 Roadmap

**A13** moves the per-PR loop out of the plan file and into the repo:
1. a stubs commit;
2. a tests-only commit, which must fail by assertion against the stubs;
3. implementation commits that never touch test paths.

The review caught that commits can't be told apart by author, since all
are authored as Robert and pushed by the bot. The doc now states that
limit plainly, and makes the test-fix path a review check, not a
mechanical one.

**A10** lays out seven milestones to v1, with status markers so it works
as a tracker. The key sequencing point is that prod can only deploy from
`main`, so the merge happens at code-complete, before the cutover. The
review found:
- CI had no dev identity, so `docs/author_setup.md` §2.5 now creates one,
  with Workload Identity Federation;
- verifiers only bind once they're required checks;
- "a full month's bill" pushes v1 to about the end of March 2027;
- a rollback must be a revert PR, never a force-push.

## 7. Contract Additions

- **Failure modes FM-01…FM-20**, with a retry/alert rule:
  - availability failures retry and alert on the 3rd attempt;
  - content failures alert on the first.
- **`raw_ingest_audit`,** written by a load job and read with
  `tabledata.list`, so it costs no query.
- **Reconciliation counts R-01…R-07** and **metamorphic relations
  M-01…M-07.**
- **The build's window (contract §1):** each daily build also catches up
  any day that gained a late hour or failed its last build.

The review found 6 blockers:
- R-06 summed per language instead of per (language, bucket);
- R-01 broke on replays;
- M-01's checksum included columns that change on every load;
- raw's `unique` test contradicted duplicate handling;
- a late hour 23 was silently lost downstream;
- CI fixtures would be deleted by partition expiration on arrival.

All fixed before approval.

## 8. Independent Review Results

| PR | Doc | Blockers | Should-fix | Outcome |
|---|---|---|---|---|
| #19 | Cost model | 2 | 8 | Fixed, then approved |
| #21 | Security posture | 2 | 9 | Fixed, merged |
| #22, #23 | Ways of working, roadmap (one review) | 4 | 9 | Fixed, approved |
| #24 | Contract additions | 6 | 8 | Fixed, approved |

**Pattern:** each reviewer got the docs and pointers, never my
reasoning. Most blockers were interactions between a new decision and an
older one:
- daily cadence vs late hours;
- 3-day retention vs replays and CI fixtures;
- one bot identity vs the TDD commit rules.

## 9. Decisions and Rejections

| Considered | Outcome | Why |
|---|---|---|
| Hourly full `dbt build` | Rejected | 35–56 GB/day against a 10 GiB quota |
| Hourly staging + fact, daily marts | Rejected | ~4× the query use; nothing downstream reads hourly |
| dbt `merge` incrementals | Rejected | Scans the whole target every build; `insert_overwrite` instead |
| Standing 3-day lookback in the daily build | Rejected | Re-reads payloads daily; replaced by audit-driven catch-up days |
| Separate marts-only dataset for the dashboard | Rejected | All data is public; not worth the extra moving part |
| Dashboard key copy in Secret Manager | Rejected | One more leak surface with no reader |
| Language token from the bot account | Rejected | Shares the agent's rate limit; prod would depend on a build-time account |
| Resetting `main` to roll back | Rejected | Force-push is forbidden; revert PR instead |
| Promotion per milestone | Rejected by the author | One promotion at the end keeps `main` a clean fallback |
| Dropping Great Expectations | Rejected by the author | Kept as the single implementation of ingest's batch checks |

## 10. Open Items at Session End

**Waiting on the author** (`docs/author_setup.md`, in order):
1. Part 1:
   - §1.1 branch rules (there's no `build/agentic` ruleset yet);
   - §1.2–1.3 bot accounts, with the bot's mail forwarded;
   - §1.4 repo security settings and the `ci-alerts` environment.
2. Part 2:
   - the dev project and quota;
   - the key-expiry policy test (§2.1 step 5);
   - the agent identity;
   - CI's dev identity (§2.5).
3. Deploy the dev kill switch once the agent writes it.

Until Part 1 is done, the agent still works under the author's GitHub
login. That's acceptable for docs, but ADR 0002 requires the bot before
any build work.

**Next for the agent:**
- **M1:** the `architecture.md` drift fix, the only M1 item left. Then
  tag `m1-done`.
- **M2:** scaffolding and verifier tooling (B1–B6, B8, B9, B11). The
  non-cloud parts can start before the author's setup.

## 11. ELI5 Topics This Session

None. The author asked for plainer explanations twice (§1), but neither
was an ELI5 invocation, so there's no quiz.

## 12. Files Changed

### Merged to `build/agentic` (PRs #17–#25)
| File | Change |
|---|---|
| `docs/cost_model.md` | Created (A11) |
| `docs/security.md`, `SECURITY.md` | Created (A12) |
| `docs/ways_of_working.md` | Created (A13) |
| `docs/roadmap.md` | Created (A10) |
| `docs/data_contract.md` | Cost decisions applied (§1 rules, 28h freshness, retention, `payload_action`, partitioned snapshot marts, dashboard access); FM-01…FM-20, `raw_ingest_audit`, R-01…R-07, M-01…M-07; PII and token questions resolved; `repo_name` on repo marts; suppression filter |
| `docs/access_matrix.md` | Scheduler invokes dbt; dashboard scope stated; bot token type corrected; Slack webhook as environment secret |
| `RUNBOOK.md` | Replay with catch-up, retry/alert rule, 70-hour replay limit, key rotation reboot, environment secret |
| `DECISIONS.md` | §5 exceptions named; §9 single promotion and commit authorship |
| `docs/adr/0002-…md` | §4 one promotion at the end; per-user quota note |
| `docs/author_setup.md` | §1.2 mail forwarding, §1.3 step 5 authorship, §1.4 repo security, §2.1 key-expiry test, §2.5 CI's dev identity |
| `CLAUDE.md` | Workflow reflexes (promotion, authorship); roadmap and ways of working added to the required reading |
| `README.md` | The four questions match the contract |
| `QUESTIONS.md`, `OPEN_LOOPS.md`, `FOUNDATION_BACKLOG.md` | Q1 answered; two loops closed; A10–A13 closed |

### Outside the repo
| File | Change |
|---|---|
| `~/.claude/projects/…oss-pulse/memory/agentic-buildout-plan.md` | Single-promotion decision and commit authorship |
