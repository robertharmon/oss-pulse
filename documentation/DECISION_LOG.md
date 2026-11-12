# Decision Log

> **4 sessions**, most recent 2026-11-11. A session-indexed history of
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

## Subsystem: Data Ingestion

Fetchers, raw landing, Parquet schema, retries, backfill.

- *(no entries yet)*

## Subsystem: Analytics & Modeling

dbt staging / intermediate / marts, data quality tests, lineage, grain
decisions.

- *(no entries yet)*

## Subsystem: Orchestration & Observability

Scheduling, retries, alerting, dashboards, consumer layer.

- *(no entries yet)*

---

## Current Outlook

**Where we are:** Agentic build-out, milestone 1 (remaining foundation
docs), after **S04**.
- `main` is tagged `baseline-pre-agentic`. All agent work lands on
  `build/agentic` through reviewed PRs.
- ADR 0002 sets the operating model: bot identities, a billed-but-capped
  dev project, and test-first development plus verifiers.
- Phase A is 10/14 complete.
- No cloud resources and no pipeline code exist yet.

**What's open:**
- **Author actions** (`docs/author_setup.md`, in order):
  1. branch rules (`main` requires approval; protect `build/agentic`);
  2. answer `QUESTIONS.md` Q1 (commit attribution under a bot);
  3. the bot accounts;
  4. the dev project and kill switch.
- **Milestone 1 remaining:**
  - A11 cost model (in progress; retention must replace "keep forever");
  - A12 security posture;
  - A13 ways of working;
  - A10 roadmap (folds in the A10 inputs list);
  - contract additions (failure-mode IDs, `raw_ingest_audit`,
    reconciliation and metamorphic sections).
- **Deferred:** the milestone-promotion method (OPEN_LOOPS), decided
  before the first promotion to `main`.

**What's next:** Finish A11, then milestone 2: scaffolding plus verifier
tooling (B1–B6, B8, B9, B11), once the bot identities exist.

**Review triggers:**
- **ADR 0001:** spend over $5 for 3 consecutive months; a role change;
  deprecation or free-tier removal of a chosen service; the 2027-04-05
  checkpoint.
- **ADR 0002:** the kill switch fires; an agent PR weakens a check; the
  author's review queue becomes the bottleneck; cutover.
