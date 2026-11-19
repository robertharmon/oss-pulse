# Decision Log

> **6 sessions**, most recent 2026-11-18. A session-indexed history of
> the project organized by subsystem. Each entry summarizes the
> motivating question and the outcome — read the linked session doc for
> full detail.

## Chronological Index

| Session | Date | Title | Subsystem |
|---|---|---|---|
| 01 | 2026-10-05 | [Initial Bootstrap and Foundation Documents](Session01_20261005_initial_bootstrap_and_foundation_docs.md) | Foundation & Governance |
| 02 | 2026-10-05 | [A5 Architecture Doc and Session-01 Docs Rescue](Session02_20261005_a5_architecture_doc.md) | Foundation & Governance |
| 03 | 2026-10-06 | [A6 CONVENTIONS.md and the No-Local-Docker Decision](Session03_20261006_a6_conventions_and_no_local_docker.md) | Foundation & Governance |
| 04 | 2026-11-11 | [Agentic Build-Out Setup, A7–A9, and the GH Archive URL Fix](Session04_20261111_agentic_build_out_setup.md) | Foundation & Governance / Infrastructure & Cloud |
| 05 | 2026-11-18 | [Phase A Close-Out: Cost Model, Security, Ways of Working, Roadmap, Contract IDs](Session05_20261118_phase_a_close_out_cost_security_roadmap.md) | Foundation & Governance / Infrastructure & Cloud / Analytics & Modeling |
| 06 | 2026-11-18 | [M1 Close, M2 Tooling and Verifiers, Kill Switch, ADR 0003](Session06_20261118_m1_close_m2_tooling_killswitch_adr0003.md) | Foundation & Governance / Infrastructure & Cloud / Data Ingestion / Orchestration & Observability |

---

## Subsystem: Foundation & Governance

Repo setup, documents, workflow conventions, decisions, backlog,
CLAUDE.md, ADRs, session docs.

- **S01** — How does a brand-new repo begin as a serious portfolio
  project without accruing scaffolding debt?
  Landed the full set of foundation documents (README, DECISIONS,
  FOUNDATION_BACKLOG, OPEN_LOOPS, CLAUDE.md) and the first ADR (tech
  stack rationale). Established the PR-only workflow via a
  `protect-main` GitHub ruleset, which required one configuration
  iteration (empty target-branches list caught by smoke test, fixed,
  re-verified with both direct push and force push rejected). Instituted
  the no-AI-attribution rule in three places (global CLAUDE.md, project
  memory, DECISIONS §9) and adopted the session-doc / decision-log
  methodology at session end. Backlog: 6/14 Phase A + 2/10 Phase B
  complete.
- **S02** — How do the pieces committed to in ADR 0001
  actually fit together end-to-end, and how do we get `main` back in
  sync with Session 01's narrative?
  Rescued Session 01's methodology-adoption commit, which had been
  pushed to a branch but never opened as a PR, by cherry-picking it
  onto a fresh branch and merging as PR #6 — this is what put
  `documentation/Session01…md` and `documentation/DECISION_LOG.md` on
  `main` for the first time. Then landed `docs/architecture.md` as PR
  #7, closing A5: an ASCII diagram, per-component responsibility
  table, end-to-end trace of one `WatchEvent` from GH Archive to a
  Streamlit chart, failure-boundary matrix, and security-boundary
  summary — satisfying the "trace one record without reading another
  file" done criterion. Backlog: 7/14 Phase A complete.
- **S03** `current` — How do we lock the project's style conventions
  in one file without re-litigating what DECISIONS.md already locks,
  and does oss-pulse want the same Docker-everywhere local
  environment that color-analytics uses?
  Closed A6 by landing `CONVENTIONS.md` (PR #9) — a pointer-heavy
  consolidation that references DECISIONS.md §4/§6/§7/§8/§9 for
  anything already locked and adds the ground DECISIONS.md doesn't
  cover: Python style (ruff, mypy strict), SQL style (sqlfluff,
  lowercase keywords, leading commas, CTEs over subqueries, no
  `SELECT *` in prod models), PR title shape, and the comments rule
  (default none; comments only when the *why* is non-obvious). The
  comments rule is deliberately placed in CONVENTIONS.md rather than
  DECISIONS.md — style conventions and operating decisions have
  different half-lives and audiences. Separately, in the same PR,
  locked DECISIONS §10 — no local Docker; deploy via `gcloud run
  deploy --source .` (Cloud Run Buildpacks); local dev tools and
  Python deps managed by `uv`. The decision is ~60% technical
  (Windows WSL2 overhead, pre-commit speed, IDE tool visibility, the
  pure-Python stack doesn't fight you to install) and ~40% honest
  portfolio-narrative hedging (the deployment artifact is still a
  container; Google writes the Dockerfile for free). Operationally,
  this session also brought `gh` CLI online (first terminal-opened
  PRs — #8, #9, #10) and surfaced that OAuth is the right credential
  for a human-on-laptop workflow, not fine-grained PATs. Backlog:
  8/14 Phase A complete.

- **S04** `current` — How can agents finish the build safely while the author has little time?
  Locked ADR 0002: agents work on a `build/agentic` integration branch
  (baseline tag `baseline-pre-agentic` on `main`), test-first with seven
  verifier types, using their own bot identities, against a billed dev
  project with hard caps (billing kill switch, query quota, table
  expiry). Independent review agents caught 5 blockers across 4 PRs
  before merge, including that the first-choice no-billing sandbox
  can't run dbt incremental models and that agents had been running
  with the author's credentials. Closed A7 (data contract), A8 (access
  matrix) and A9 (runbook); found that GH Archive URLs use an unpadded
  hour, which turned the contract's ~35% missing-hour rate into 72/72
  present. Backlog: 10/14 Phase A.

- **S05** `current` — What's left between the docs and a build agents can run against?
  Closed Phase A: A11 cost model, A12 security posture, A13 ways of
  working, A10 roadmap (seven milestones to v1, approved), plus stable
  contract IDs (FM-01…FM-20, R-01…R-07, M-01…M-07). The author chose one
  promotion of `build/agentic` into `main`, made at code-complete and
  before the cutover, because prod deploys only from `main`. Commits
  stay authored by Robert under the bot. Four independent reviews found
  14 blockers, mostly interactions between new and older decisions, all
  fixed before merge. Backlog: 14/14 Phase A.

- **S06** `current` — What can be built before the author's account setup, and how do agent roles get enforced?
  Closed M1 (architecture drift fix, tag `m1-done`) and built M2's
  cloud-free parts: a uv workspace, ruff/mypy/pytest, sqlfluff,
  SHA-pinned pre-commit with gitleaks, 12 CI jobs, CODEOWNERS without a
  `*` rule, each gate drilled with a planted bad input. B11 verifiers:
  failure-mode coverage with a shrink-only baseline, no-mixed-commits,
  executable docs, workflow policy, and a red-proof check that runs a
  PR's new tests against its stubs commit. After the author's "You are
  the builder agent", added a lock hook that keys on the hook input's
  `agent_id` to enforce agent roles, and moved all test-writing to a
  test-writer agent. Its audit of the builder-written verifier tests
  found 13 real gaps, all fixed in the scripts (195 tests).

## Subsystem: Infrastructure & Cloud

Terraform, GCP resources, networking, IAM, Secret Manager, remote
state.

- **S04** `design-only` — Who and what may touch each GCP resource, and how is spend capped?
  Two billed projects (dev, prod) each with a billing kill switch,
  10 GB/day query quota and budget alerts; a canonical IAM bindings
  table (`docs/access_matrix.md`) built to be diffed against Terraform,
  with prod CI identities gated by author-approved GitHub Environments
  and WIF pinned to the repo's numeric ID. Rejected the BigQuery
  no-billing sandbox (no DML, 10 GiB lifetime storage, 60-day expiry).
- **S05** `design-only` — What does it cost, and what must the security posture cover?
  Measured volumes (87.7 MB/day gzipped, 92% payload) and verified live
  prices. Found that the 10 MB-per-query billing minimum counts against
  the daily quota, so the hourly dbt build was replaced by hourly ingest
  plus a daily build: ~2–4 GB/day instead of 35–56. Expected spend is
  $0.00–0.15/month. Security: credential inventory and rotation; the
  dashboard key as the one key file (DECISIONS §5 amended); CI's Slack
  webhook as an environment secret; a CI dev identity via WIF.
- **S06** `built, not deployed` — How does spend get a hard stop?
  The billing kill switch (C9): a Cloud Run function that unlinks billing
  when a budget notification shows spend over the cap, simulate mode by
  default, and a `deploy.sh` the author runs in Cloud Shell that applies
  exactly the access matrix's four grants and can publish a drill
  message. Tests by a test-writer agent (32), confirmed red by CI.

## Subsystem: Data Ingestion

Fetchers, raw landing, Parquet schema, retries, backfill.

- **S06** `design-only` — How do ingest and the build run, and how is history backfilled?
  ADR 0003: Cloud Run jobs for both (ingest at `:15`, dbt at 01:30 UTC),
  no platform retries. The first backfill design (widen expiration, then
  restore) failed review on quotas, data-loss risk and one bad hour
  blocking every build. Final: a raw backfill twin without expiration,
  `stg_events` as a view, at most 4 eligible catch-up days per build, a
  day eligible only once all its hours have ended, and ingest refusing
  any load that would expire on arrival. 35 days at the cutover.

## Subsystem: Analytics & Modeling

dbt staging / intermediate / marts, data quality tests, lineage, grain
decisions.

- **S05** `design-only` — What exactly will the tests hold the pipeline to?
  Retention per table (raw and staging 3 days, facts 400, snapshot marts
  30), `insert_overwrite` incrementals, NOT NULL as schema constraints,
  and a daily build that catches up late or failed days from
  `raw_ingest_audit`. Twenty failure modes with a retry/alert rule
  (availability vs content), seven balancing counts and seven
  metamorphic relations, each with a stable ID for the coverage check.

## Subsystem: Orchestration & Observability

Scheduling, retries, alerting, dashboards, consumer layer.

- **S06** `design-only` — What triggers what?
  Two Scheduler jobs call Cloud Run jobs' `:run` API with `run.invoker`
  (runs, can't pass overrides); replays and backfills are author-started
  executions. Scheduler timeouts became moot; the build's window is
  capped so every build fits the 6 GiB per-identity quota.

---

## Current Outlook

**Where we are:** M1 is done (`m1-done`). M2 is mostly done where it
doesn't need the cloud, after **S06**.
- `main` is still at `baseline-pre-agentic`.
- `build/agentic` has the toolchain, 12 CI jobs, the B11 verifiers, the
  agent definitions, a lock hook, the kill-switch code, and ADR 0003
  applied across the docs.
- No cloud resources exist yet.

**What's open:**
- **Next session, first:** confirm the lock hook denies the builder a
  test-file write, and that the four agent types are registered (both
  load at session start).
- **Author actions** (`docs/author_setup.md`, in order):
  1. Part 1: rulesets, bot accounts, repo security settings;
  2. Part 2: dev project, quota, identities;
  3. deploy and drill the dev kill switch;
  4. make the 12 CI jobs required checks.
- **B11 remaining:** the contract ↔ dbt diff (M4), the access matrix ↔
  Terraform diff (M5), retention checks, and the required-check drills.

**What's next:** M3 ingest code (ADR 0003 shape), test-first. It waits on
M2's checks being required in the rulesets.

**Review triggers:**
- **ADR 0001:** the 2027-04-05 checkpoint, or the earlier triggers in the
  ADR.
- **ADR 0002, ADR 0003 and the security doc:** at the cutover, or if the
  kill switch fires, or an agent PR weakens a check.
- **Cost model:** by 2027-08-01, before alerting charges can start.
