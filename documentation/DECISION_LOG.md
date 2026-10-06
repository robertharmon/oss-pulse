# Decision Log

> **1 session** on 2026-10-05. A session-indexed history of the project
> organized by subsystem. Each entry summarizes the motivating question
> and the outcome — read the linked session doc for full detail.

## Chronological Index

| Session | Date | Title | Subsystem |
|---|---|---|---|
| 01 | 2026-10-05 | [Initial Bootstrap and Foundation Documents](Session01_20261005_initial_bootstrap_and_foundation_docs.md) | Foundation & Governance |

---

## Subsystem: Foundation & Governance

Repo setup, documents, workflow conventions, decisions, backlog,
CLAUDE.md, ADRs, session docs.

- **S01** `current` — How does a brand-new repo begin as a serious
  portfolio project without accruing scaffolding debt?
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

**Where we are:** Foundation phase, immediately post-bootstrap. The
repo exists publicly at `github.com/robertharmon/oss-pulse` with a
verified PR-only workflow, five merged PRs, and the first ADR
committing to the BigQuery + dbt + serverless-GCP stack ($0/month
target). No cloud resources exist yet. No pipeline code exists yet.

**What's open:**

- Eight remaining Phase A documents (A5 architecture, A6 conventions,
  A7 data contract, A8 access matrix, A9 runbook, A10 90-day roadmap,
  A11 budget/cost model, A12 security posture, A13 solo
  ways-of-working — a few of these may rightly merge or be deferred
  pending reality).
- All of Phase B except B7 (branch protection) and B10 (ADR template).
- All of Phase C (cloud bootstrap).
- All of Phase D (walking-skeleton smoke test).

**What's next:** **A5 — Architecture doc + diagram.** A system diagram
plus component-responsibility narrative plus data-flow walkthrough so
a reader can trace a single record from GH Archive to a Streamlit
chart without reading any other file.

**Review triggers for the current stack decision (ADR 0001):**
- Any month with cloud spend above $5 for three consecutive months
- Role change for the author
- Major deprecation or free-tier removal at a chosen service
- 2027-04-05 as a scheduled checkpoint
