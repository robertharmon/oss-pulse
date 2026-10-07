# Decision Log

> **3 sessions**, most recent 2026-10-06. A session-indexed history of
> the project organized by subsystem. Each entry summarizes the
> motivating question and the outcome — read the linked session doc for
> full detail.

## Chronological Index

| Session | Date | Title | Subsystem |
|---|---|---|---|
| 01 | 2026-10-05 | [Initial Bootstrap and Foundation Documents](Session01_20261005_initial_bootstrap_and_foundation_docs.md) | Foundation & Governance |
| 02 | 2026-10-05 | [A5 Architecture Doc and Session-01 Docs Rescue](Session02_20261005_a5_architecture_doc.md) | Foundation & Governance |
| 03 | 2026-10-06 | [A6 CONVENTIONS.md and the No-Local-Docker Decision](Session03_20261006_a6_conventions_and_no_local_docker.md) | Foundation & Governance |

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

## Subsystem: Infrastructure & Cloud

Terraform, GCP resources, networking, IAM, Secret Manager, remote
state.

- *(no entries yet)*

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

**Where we are:** Foundation phase, Session 03 complete. The repo
exists publicly at `github.com/robertharmon/oss-pulse` with a verified
PR-only workflow, nine merged PRs, the first ADR committing to the
BigQuery + dbt + serverless-GCP stack ($0/month target), the
architecture doc describing how the ADR's pieces fit together, a
code-and-docs conventions file (`CONVENTIONS.md`), and a
no-local-Docker operating decision in `DECISIONS.md` §10. `gh` CLI
is operational for terminal-opened PRs. No cloud resources exist
yet. No pipeline code exists yet.

**What's open:**

- Six remaining Phase A documents (A7 data contract, A8 access
  matrix, A9 runbook, A10 90-day roadmap, A11 budget/cost model,
  A12 security posture, A13 solo ways-of-working — a few of these
  may rightly merge or be deferred pending reality).
- All of Phase B except B7 (branch protection) and B10 (ADR template).
- All of Phase C (cloud bootstrap).
- All of Phase D (walking-skeleton smoke test).

**What's next:** **A7 — Data contract.** Upstream sources (GH Archive)
with known SLAs and failure modes, output tables (grain, freshness,
columns), downstream consumers, column add/deprecate rule. The mart
list in `docs/architecture.md` §4 is the authoritative source for
which marts the contract needs to describe.

**Review triggers for the current stack decision (ADR 0001):**
- Any month with cloud spend above $5 for three consecutive months
- Role change for the author
- Major deprecation or free-tier removal at a chosen service
- 2027-04-05 as a scheduled checkpoint
