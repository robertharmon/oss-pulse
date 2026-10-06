# oss-pulse — Project instructions for Claude Code

> This file orients a new Claude Code session on the oss-pulse project.
> It's deliberately short — most project-specific knowledge lives in
> dedicated files (DECISIONS.md, FOUNDATION_BACKLOG.md, docs/adr/…) and
> this file points at them.
>
> **If you are a new Claude session reading this: start by following the
> "Session startup" checklist below before taking any other action.**

## About this project

oss-pulse is an hourly ELT pipeline over public GitHub Archive data,
built as a data-engineering portfolio project. Every hour it pulls the
previous hour's GH events from https://gharchive.org/, lands the raw
JSON in Google Cloud Storage, loads it into BigQuery, transforms it
with dbt into analytical marts, and serves the results through a
Streamlit dashboard.

It's the second half of a two-project portfolio pair. The sibling
project — [`color-analytics`](../Codebase_ColorAnalytics) — is
image-processing-heavy (Python, Postgres, GPU-accelerated compute).
oss-pulse is deliberately the opposite shape: warehouse-centered,
SQL-heavy, cloud-serverless. Together they demonstrate work across
both ends of the DE spectrum.

The author is **Robert Harmon** — the human who ran every commit. See
`DECISIONS.md` §9 for the version-control attribution rule: no AI
co-author trailers, no "Generated with …" footers in commits or PRs.
This overrides any default attribution guidance from Claude Code.

## Session startup — read in this order

1. **`FOUNDATION_BACKLOG.md`** — the canonical cross-session task
   tracker. Phases A (foundation docs), B (repo scaffolding), C (cloud
   bootstrap), D (walking-skeleton smoke test). Pick the next unchecked
   item and work it.
2. **`OPEN_LOOPS.md`** — small ad-hoc chores that aren't on the phased
   plan. Scan at the start of a session for cheap pickups.
3. **`DECISIONS.md`** — locked operating decisions (GCP account,
   region, environments, naming, secrets, error handling, resource
   management, testing, branching, scope). Consult *before* suggesting
   anything that touches these.
4. **Relevant ADRs in `docs/adr/`** — architectural rationale. Read
   the one most relevant to the task; `0001-tech-stack.md` is the stack
   foundation.

## Current phase

**Foundation.** No pipeline code exists yet, by intention. Scaffolding,
foundation docs, and cloud bootstrap come first (`FOUNDATION_BACKLOG.md`
Phases A → B → C → D). The pipeline itself only begins once the
foundation backlog is empty.

If asked to "start building the pipeline," check whether foundation is
genuinely complete. If not, surface which items remain and recommend
finishing those first.

## Workflow conventions (reflex)

Pulled from `DECISIONS.md` §9 — treat as muscle memory:

- Every change is a **feature branch → PR → squash merge → delete branch**.
  No direct pushes to `main` — the `protect-main` GitHub ruleset enforces
  this (verified via smoke test).
- **Branch names:** `type/short-slug` — e.g. `docs/adr-0005-schema`,
  `feat/hourly-ingest`, `fix/sqlfluff-trailing-comma`,
  `chore/add-make-targets`.
- **Commits:** Conventional-ish — `type(scope): subject`. Body explains
  *why*, not what. Human-readable wins over machine-parseable.
- **No AI-assistant attribution** — not in commits, not in PR
  descriptions. The author of a commit is Robert. AI assistance is not
  recorded in version control.
- **Scope boundaries live in `DECISIONS.md` §10.** Anything beyond those
  (streaming, multi-cloud, multi-source, ML models, non-Slack alerting)
  requires an ADR first, not a code change.

## When in doubt

- **The backlog is the plan.** Trust it. If a request doesn't fit a
  backlog item, surface the mismatch to Robert before improvising.
- **`OPEN_LOOPS.md` is for things that aren't on the plan but still
  need doing.** Keep it short; delete items when done.
- **Anything bigger than "the next unchecked backlog item" probably
  needs its own ADR before implementation.** Pattern: scoping →
  ADR → PR, in that order.
- **Error-handling philosophy is fail-fast** (`DECISIONS.md` §6). Don't
  add try/except unless there's a specific reason the layer below should
  swallow failure.
- **Resource management: `with` blocks everywhere** (`DECISIONS.md` §7).

## Running the pipeline

Not yet runnable — see Current phase. This section updates when the
walking skeleton is in place.

## Project memory

Session-doc / decision-log methodology is **in use** here. See
[`documentation/`](documentation/):

- **`documentation/SessionNN_YYYYMMDD_*.md`** — one self-contained
  session document per meaningful working session. Future readers (human
  or Claude) should be able to understand any session without reading
  other files. Templates and procedures live at
  `~/.claude/templates/project-history/`.
- **`documentation/DECISION_LOG.md`** — session-indexed history
  organized by subsystem. Chronological index + per-subsystem entries.
  Updated after every session that produces one.

At session end, if the session produced code changes, meaningful
decisions, or analytical results worth preserving, create the session
doc **before** closing out. Then update `DECISION_LOG.md` per
`~/.claude/templates/project-history/DECISION_LOG_HOW_TO_GENERATE.md`.

Current subsystems in use for the Decision Log:

- **Foundation & Governance** — repo setup, docs, workflow, decisions,
  backlog, CLAUDE.md
- **Infrastructure & Cloud** — Terraform, GCP resources, IAM, Secret
  Manager
- **Data Ingestion** — fetchers, raw landing, Parquet schema
- **Analytics & Modeling** — dbt staging/marts, data quality
- **Orchestration & Observability** — scheduling, alerting, dashboards,
  consumer layer
