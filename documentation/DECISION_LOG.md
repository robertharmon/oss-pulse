# Decision Log

> **5 sessions**, most recent 2026-11-18. A session-indexed history of
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

## Subsystem: Data Ingestion

Fetchers, raw landing, Parquet schema, retries, backfill.

- *(no entries yet)*

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

- *(no entries yet)*

---

## Current Outlook

**Where we are:** Phase A is complete after **S05**. M1 has one item
left (the `architecture.md` drift fix).
- `main` is still at `baseline-pre-agentic`. It gets one "Rebase and
  merge" from `build/agentic` at code-complete, before the prod cutover.
- `docs/roadmap.md` is the plan and tracker: seven milestones, v1 about
  the end of March 2027.
- No cloud resources and no pipeline code exist yet.

**What's open:**
- **Author actions** (`docs/author_setup.md`, in order):
  1. Part 1: branch rules (there's no `build/agentic` ruleset yet), bot
     accounts, repo security settings;
  2. Part 2: the dev project, quota, agent identity and CI's dev
     identity;
  3. deploy the dev kill switch.
- **Until the bot exists,** the agent works under the author's GitHub
  login. That's fine for docs, but not for build work (ADR 0002).

**What's next:** the `architecture.md` drift fix and the `m1-done` tag,
then M2 (scaffolding and verifier tooling), whose non-cloud parts don't
wait on the author.

**Review triggers:**
- **ADR 0001:** the 2027-04-05 checkpoint, or the earlier triggers in the
  ADR.
- **ADR 0002 and the security doc:** at the cutover, or if the kill
  switch fires, or an agent PR weakens a check.
- **Cost model:** by 2027-08-01, before alerting charges can start.
