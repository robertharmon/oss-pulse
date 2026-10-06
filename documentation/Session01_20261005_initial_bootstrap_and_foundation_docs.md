# Session 01 — Initial Bootstrap and Foundation Documents

**Date:** 2026-10-05
**Status:** Complete
**Focus:** Bootstrap the oss-pulse repository from zero: land the foundation
documents (README, DECISIONS, FOUNDATION_BACKLOG, OPEN_LOOPS, CLAUDE.md),
land the first architecture decision record (ADR 0001 — tech stack
rationale) and its template, create the public GitHub repository with
branch protection, establish the PR-only workflow via a GitHub ruleset
(which required one iteration to configure correctly), institute a
cross-project no-AI-attribution standard, and adopt the session-doc /
decision-log methodology.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Motivation and Context](#2-motivation-and-context)
3. [Foundation Documents Landed](#3-foundation-documents-landed)
4. [GitHub Repository and Public Setup](#4-github-repository-and-public-setup)
5. [Branch Protection: Misconfiguration, Smoke Test, Fix](#5-branch-protection-misconfiguration-smoke-test-fix)
6. [Workflow Conventions Established via Early PRs](#6-workflow-conventions-established-via-early-prs)
7. [ADR 0001 — Tech Stack Rationale, and ADR Template](#7-adr-0001--tech-stack-rationale-and-adr-template)
8. [Project CLAUDE.md for Session Continuity](#8-project-claudemd-for-session-continuity)
9. [Session-Doc Methodology Adopted](#9-session-doc-methodology-adopted)
10. [Decisions and Rejections](#10-decisions-and-rejections)
11. [Open Loops at Session End](#11-open-loops-at-session-end)
12. [Files Changed](#12-files-changed)

---

## 1. Overview

oss-pulse began the session as a concept and ended it as a public GitHub
repository with ten commits on `main`, five successful pull requests
through a verified branch-protection ruleset, and the full set of
foundation documents (6 of 14 Phase A items plus 2 of 10 Phase B items
complete). The repository is deliberately scaffold-first: no pipeline
code exists yet, by design.

The session established three durable standards that will shape every
subsequent session:

- **The PR-only workflow via `protect-main`** — verified by smoke-testing
  the gate with both a direct push and a force push, both of which were
  rejected after an initial misconfiguration was found and fixed.
- **No AI-assistant attribution in version control** — codified in three
  layers (global `~/.claude/CLAUDE.md`, project memory for the sibling
  color-analytics repo, and oss-pulse's own `DECISIONS.md` §9).
- **Session-doc / decision-log methodology** — adopted at session end as
  the project's institutional-memory system, with templates sourced from
  `~/.claude/templates/project-history/`.

Backlog progress at session close:
- Phase A: **6 / 14** complete (A1, A2, A3, A4, A14, plus a retroactively
  numbered addition)
- Phase B: **2 / 10** complete (B7 branch protection, B10 ADR template —
  both landed ahead of schedule)
- Phase C: 0 / 8
- Phase D: 0 / 5

## 2. Motivation and Context

### Problem

The author had one existing portfolio project
([color-analytics](../../Codebase_ColorAnalytics)), an image-processing
pipeline exercising Python, Postgres, and GPU-accelerated compute. For
a complete data-engineering portfolio, a *second* project was needed —
one deliberately opposite in shape: warehouse-centered, SQL-heavy,
cloud-serverless. The goal was to exercise the modern cloud data stack
(BigQuery, dbt, orchestration, IaC, CI/CD) that color-analytics does
not touch.

Beyond the technical shape, the session also carried a
process/discipline goal: build this project *the way a professional
team would build it from day one* — scaffolding before content, PRs
through a protected main, infrastructure-as-code from the first cloud
resource, every change gated by review (even solo).

### Approach

**Walking-skeleton methodology.** Decided early that scaffolding
(branch protection, CI stubs, Terraform skeleton, foundation docs) is
always-on from commit 1, with content growing phased on top. The
alternative — "vertical slices per phase, with CI added later" — was
rejected because retrofitting guardrails is strictly more expensive
than installing them before any content exists to protect.

### Prior Art

- The sibling **color-analytics** project established the pattern of
  shipping with a project-level `CLAUDE.md` and a `documentation/`
  session-doc folder. oss-pulse initially started *without* adopting
  session docs; the decision to adopt was made at this session's end
  when the "how does a new Claude session orient itself" question
  surfaced.
- The author's global `~/.claude/CLAUDE.md` establishes the engineering
  principles (Scale Appropriateness, Error Handling Philosophy as a
  per-project choice, Testing Litmus Test, Naming rules, etc.) that
  this project inherits by default and codifies project-specifically
  in `DECISIONS.md`.

## 3. Foundation Documents Landed

Three documents landed in the bootstrap commit, before any cloud
resource existed:

### `README.md`

The project one-pager. Explains what oss-pulse is, the four analytical
questions the pipeline exists to answer:

1. **Trending repos this week** — repos with the largest week-over-week
   increase in stars/PRs/pushes.
2. **Language contributor share** — percentage of unique contributors
   touching each language, month over month.
3. **Contributor concentration per repo** — Gini coefficient of commits
   per author.
4. **Time-of-day activity patterns** — commit distribution by hour,
   split by primary language.

Each will eventually be served by one `mart_*` table and one dashboard
chart. The README also points at `DECISIONS.md` §10 for scope
boundaries and `FOUNDATION_BACKLOG.md` for progress tracking.

### `DECISIONS.md`

Ten locked operating decisions. Reproduced here as a summary; the
authoritative version is in the repo.

| § | Decision | Key points |
|---|---|---|
| 1 | GCP account | Dedicated Google account; **$0/month** target enforced by billing alerts at $1/$5, BigQuery scan quota of 10 GB/day, and serverless-only architecture |
| 2 | Region | `us-central1` for all services; no multi-region |
| 3 | Environments | `dev` and `prod` only — no `staging` for a solo project |
| 4 | Naming conventions | Buckets `osp-<purpose>-<env>`; datasets `osp_<layer>_<env>`; service accounts `osp-<role>-<env>`; dbt models match table names |
| 5 | Secrets policy | Zero secrets in the repo. Secret Manager + gitleaks + Workload Identity Federation preferred over keys |
| 6 | Error-handling philosophy | **Fail fast** everywhere. Dashboard is the only layer that catches-and-presents |
| 7 | Resource management | `with` blocks exclusively — no manual `.close()` |
| 8 | Testing philosophy | Litmus test (would deleting a line of my code break this test?); integration tests against a real BigQuery sandbox, not mocks |
| 9 | Commit/branch/PR | Branches `type/short-slug`; squash merges; **no AI attribution** |
| 10 | Scope boundaries | Hourly batch only; GCP only; GH Archive only; no ML models; Slack alerting is the ceiling |

### `FOUNDATION_BACKLOG.md`

The ordered cross-session task tracker. Four phases, A → D:

- **Phase A — Foundation documents** (originally 13 items; grew to 14
  when A14 was added retroactively mid-session). Documents that make
  implicit assumptions explicit before any code lands.
- **Phase B — Repo scaffolding** (10 items). Tool configs, CI stubs,
  branch protection, ADR template.
- **Phase C — Cloud bootstrap** (8 items). GCP project, Terraform
  foundation, scan quotas, remote state bucket.
- **Phase D — Walking-skeleton smoke test** (5 items). One PR touching
  every surface, deliberate CI-failure and incident drills.

The pipeline code itself only starts after Phase D is complete — this
is the project's foundational discipline.

## 4. GitHub Repository and Public Setup

### Repository creation

The repo was initially created via the GitHub web UI at
`github.com/robertharmon/oss-pulse` as **private**, with a
MIT-License file auto-added by the creation flow. Private visibility
was a default-settings accident, not a deliberate choice.

The remote was wired to the local repo:

```
git remote add origin https://github.com/robertharmon/oss-pulse.git
```

The first `git push` was rejected (fast-forward conflict) because
GitHub's auto-created `LICENSE` commit was ahead of the local tree. The
fix was `git pull --rebase origin main --allow-unrelated-histories`,
which placed the GitHub LICENSE commit at the root and the local
foundation commits on top.

### Flip to public

Private visibility was discovered to be the cause of a downstream
problem (see Section 5): GitHub rulesets **do not enforce on private
repositories without a paid plan**. The error message `"Your rulesets
won't be enforced on this private repository until you move to GitHub
Team organization account."` surfaced the issue.

The repo was flipped to public via Settings → Danger Zone → Change
repository visibility. Rulesets began enforcing immediately on next
push.

### License

MIT was auto-selected by GitHub at creation. This matched the
pre-session recommendation; no change needed. Copyright attribution:
"Robert" / 2026 (set by GitHub using the account's display name).

## 5. Branch Protection: Misconfiguration, Smoke Test, Fix

This was the single most instructive thread of the session. A
seemingly-complete ruleset configuration turned out to have a silent
gap, caught only because the session's walking-skeleton discipline
included a deliberate smoke test.

### The ruleset `protect-main`

Created in Settings → Rules → Rulesets with:

- **Name:** `protect-main`
- **Enforcement status:** Active
- **Rules enabled:**
  - Restrict deletions
  - Block force pushes (`non_fast_forward`)
  - Require a pull request before merging (0 required approvals, since
    solo)
  - Require status checks to pass (empty check list until CI exists)
- **Bypass actors:** none
- **Target branches:** _(configured below — this is where the gap was)_

### Smoke test 1 — direct push to main

A deliberate empty commit was created on `main` with the message
`"test: should be rejected by protect-main"`. Expected: `git push`
rejected with a ruleset-related error.

**Actual outcome:** the push *succeeded*. The commit landed on
`origin/main`.

### Diagnosis via GitHub API

The ruleset was queried unauthenticated at
`https://api.github.com/repos/robertharmon/oss-pulse/rulesets/<id>`.
The response revealed:

```json
"conditions": {
  "ref_name": {
    "exclude": [],
    "include": []
  }
}
```

**The target-branches `include` list was empty.** The ruleset was
Active, had the right rules, had no bypass actors — but applied to
no branches, so every rule was a no-op on every ref.

### Fix

In the ruleset's **Target branches** section, "Include default branch"
was added. This covers `main` as the default branch and automatically
follows renames.

### Smoke test 2 — force push to main

After the fix (and before cleaning up the test commit), a force-push
was attempted to drop the test commit. Expected: either the force-push
is now rejected (confirming the gate works), or it succeeds (indicating
further misconfiguration).

**Actual outcome:**

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Cannot force-push to this branch
remote: - Changes must be made through a pull request.
```

Both rules fired: the force-push block and the require-PR rule. The
gate was now verified working.

### Cleanup

The test commit was removed from `main` via a dedicated **revert PR**
(not a force-push, which was now correctly blocked). Because `git
revert` of an empty commit produces no diff, the author had to use
`git commit --allow-empty` with a revert-style message to document the
removal — the commit itself is empty but its message explains what
happened. The commit is preserved in history as a legible record of
the smoke-test gap.

### Lessons

1. A ruleset marked "Active" with every rule box checked can still be
   a no-op if its target-branches list is empty. The UI gives no
   obvious indication.
2. The authoritative verification is the behavior, not the
   configuration page. **Smoke-test every gate deliberately.**
3. The GitHub API (`/rulesets/<id>` endpoint) is a reliable, unbuffered
   source of truth that bypasses UI caching.

## 6. Workflow Conventions Established via Early PRs

Five pull requests were opened, merged, and verified over the course of
the session:

| # | Title | What it exercised |
|---|---|---|
| 1 | `chore(backlog): close B7 — branch protection active via protect-main ruleset` | First PR through the (then-broken) gate |
| 2 | `chore: revert empty smoke-test commit now that protect-main targets main` | Revert pattern for an empty, misleading commit on main |
| 3 | `chore: add OPEN_LOOPS.md for ad-hoc housekeeping tasks` | Second-tracker introduction |
| 4 | `docs: land ADR template and ADR 0001 (tech stack & rationale)` | First architectural document; closed A4 and B10 |
| 5 | `docs: add project-level CLAUDE.md for session orientation (A14)` | Session-handoff infrastructure |

Each PR followed the full-cycle pattern:

1. Feature branch created locally with `type/short-slug` name
2. Change committed with a conventional-ish message (type + scope +
   subject + body-explaining-why)
3. Pushed to origin with `-u` for tracking
4. PR opened on GitHub with a title + body (what / why / what-could-break)
5. Squash-merged via the GitHub UI
6. Remote branch deleted (via "Delete branch" button or `git push
   origin --delete`)
7. Local main synced via `git fetch --prune && git merge --ff-only
   origin/main`
8. Local feature branch deleted with `git branch -D` (capital-D is
   required because squash-merged branches aren't recognized as "fully
   merged" by git's default-safety check — the squashed commit has a
   different hash)

The pattern is codified in CLAUDE.md as muscle-memory for future
sessions.

### A sub-lesson: `git fetch --prune` cleanup

Stale remote-tracking refs (`remotes/origin/<deleted-branch>`) linger
locally after a remote branch is deleted on GitHub, unless pruned.
Discovered mid-session when `git branch -a` showed a branch that no
longer existed on origin. Fix: `git fetch --prune origin`. Noted in
`OPEN_LOOPS.md` as a one-time global config toggle:
`git config --global fetch.prune true`.

## 7. ADR 0001 — Tech Stack Rationale, and ADR Template

Backlog items **A4** and **B10** closed together in PR #4.

### `docs/adr/0000-template.md` (B10)

Michael Nygard-style skeleton: Status / Date / Authors header, Context,
Decision, Alternatives considered, Consequences (positive / negative /
neutral), Review date, References. All future ADRs follow this shape.

### `docs/adr/0001-tech-stack.md` (A4)

The full stack decision for oss-pulse, in one document rather than
split across many ADRs. Rationale: at project kickoff the stack coheres
as one decision — splitting it is overkill.

**The chosen stack:**

| Layer | Tool |
|---|---|
| Cloud provider | GCP |
| Warehouse | BigQuery |
| Object storage | GCS |
| Transformation | dbt Core (OSS) |
| Orchestration (production) | Cloud Scheduler → Cloud Run |
| Orchestration (local practice) | Dagster or Kestra, time-boxed |
| Infrastructure-as-code | Terraform |
| Secrets | Google Secret Manager |
| Ingest runtime | Python 3.11 in Docker |
| Python package mgmt | `uv` |
| Lint/format | `ruff` |
| Type check | `mypy` strict |
| SQL lint | `sqlfluff` (BigQuery dialect) |
| Pre-commit | `pre-commit` + `gitleaks` |
| CI/CD | GitHub Actions |
| Data quality | dbt tests + Great Expectations |
| Dashboard | Streamlit Community Cloud |
| Local prototyping | DuckDB (BigQuery-compatible SQL) |

**Alternatives seriously considered and rejected:**

- **AWS** — more job-postings but weaker free tier and more fragmented
  warehouse story.
- **Azure** — enterprise+Microsoft focused; weaker free tier for
  learners.
- **Snowflake** — 30-day trial, not always-free; incompatible with $0
  budget over months.
- **Databricks** — Community Edition restricted; strengths unused by
  a pure-SQL analytics pipeline.
- **DuckDB alone** — defeats the "experience with a cloud warehouse"
  portfolio goal.
- **Airflow (as primary)** — requires always-on process; budget blocker.
- **Pulumi** — Terraform is more widely recognized at entry-level DE
  hiring.
- **Airbyte / Fivetran** — the point is to practice *writing* an
  ingest job, not outsource it.
- **Looker Studio** — GUI tool, no code to review.
- **Metabase / Evidence.dev** — Streamlit is more universally
  recognized; both are candidates for future iterations.

**Review date:** 2027-04-05 (six months), or earlier on specific
triggers (cost overrun, significant tool deprecation, author's role
change).

Explicit non-goals captured for future reference: AWS mirror project,
Databricks mini-project, Kafka/streaming project.

## 8. Project CLAUDE.md for Session Continuity

Backlog item **A14** (added retroactively during this session, closed
in PR #5).

### The gap

Mid-session, the author asked: *"If I were to stop the session now, how
would a new Claude Code instance know what to do in the next session?"*

Audit of what a new session would have:
- Global `~/.claude/CLAUDE.md` (universal preferences) ✓
- Auto-attached git context (branch, recent commits) ✓
- Repo files on disk ✓
- A conversation of context from this session ✗
- Any cue to read the backlog first ✗
- Project-specific memory ✗ (empty for a new working directory)

The missing piece: a repo-level `CLAUDE.md` to orient a fresh session.

### The fix

A short `CLAUDE.md` at the repo root. It:

1. States what the project is in one paragraph.
2. Lists the session-startup reading order:
   `FOUNDATION_BACKLOG.md` → `OPEN_LOOPS.md` → `DECISIONS.md` →
   relevant ADRs.
3. Names the current phase (Foundation — no pipeline code yet).
4. Reiterates workflow reflexes: branch names, commit style, no
   AI-attribution, no direct pushes to `main`.
5. Points at the sibling color-analytics project.
6. States the project-memory posture (updated in Section 9 below).

### Why "A14" and not inserted earlier

Keeping backlog numbers stable matters because commit messages already
reference specific numbers (B7, A4, B10). Renumbering mid-flight would
decouple those references from their items. A14 is numerically last in
Phase A but logically foundational — the ordering accepts that
tradeoff.

## 9. Session-Doc Methodology Adopted

The initial `CLAUDE.md` draft said session-doc methodology was **not**
in use for this project — the backlog + ADRs + PR descriptions + commit
messages would serve as institutional memory. That stance was reversed
at session end when the author requested this very document.

The adoption includes:

1. **Templates sourced from** `~/.claude/templates/project-history/`:
   `SESSION_DOC_TEMPLATE.md` and `DECISION_LOG_HOW_TO_GENERATE.md`.
2. **Folder convention:** `documentation/` (same as sibling
   color-analytics; the global template uses this name too).
3. **Filename convention:**
   `documentation/SessionNN_YYYYMMDD_title_in_snake_case.md` where NN
   is zero-padded.
4. **Companion file:** `documentation/DECISION_LOG.md` — session-indexed
   history organized by subsystem.

### Subsystems chosen for the Decision Log

Five subsystems, selected to partition oss-pulse's concerns without
over-decomposing:

- **Foundation & Governance** — repo setup, docs, workflow, decisions,
  backlog, CLAUDE.md, ADRs
- **Infrastructure & Cloud** — Terraform, GCP resources, IAM, Secret
  Manager
- **Data Ingestion** — fetchers, raw landing, Parquet schema
- **Analytics & Modeling** — dbt staging/marts, data quality
- **Orchestration & Observability** — scheduling, alerting, dashboards,
  consumer layer

Session 01 (this doc) belongs under **Foundation & Governance**.

The `CLAUDE.md` project memory section was updated accordingly: session
docs are in use; see `documentation/`.

## 10. Decisions and Rejections

Decisions made (and their locations in the repo):

| Decision | Location | Rationale summary |
|---|---|---|
| BigQuery over Snowflake/Databricks | ADR 0001 | Free tier is permanent; stack coheres for pure-SQL analytics |
| GCP over AWS/Azure | ADR 0001 | Simpler on-ramp for learners; best free tier |
| Serverless orchestration (Cloud Scheduler + Cloud Run) over always-on orchestrator | ADR 0001 | $0 budget constraint; pipeline is linear enough to not need a DAG framework in prod |
| $0/month hard budget | `DECISIONS.md` §1 | Enforced architecturally, not by vigilance |
| `us-central1` single region | `DECISIONS.md` §2 | Lowest cost, best free-tier availability |
| `dev` + `prod` only (no `staging`) | `DECISIONS.md` §3 | Three environments is theater for a solo project |
| Fail-fast error handling | `DECISIONS.md` §6 | Bad data silently flowing is worse than a loud crash in batch ELT |
| `with` blocks for all resources | `DECISIONS.md` §7 | Exception-safe cleanup; no manual close() |
| Walking-skeleton over phased buildup | this session doc | Scaffolding retrofits are strictly more expensive than installing early |
| Session-doc methodology adopted | `CLAUDE.md` + this file | Reversed from initial "not in use" at session end |

Rejections (what was considered and why not):

- **GitHub Pro / paid plan for private rulesets** — rejected in favor
  of flipping the repo to public, which gets the same functionality
  for free and better serves the portfolio-visibility goal.
- **Force-push for the smoke-test commit cleanup** — rejected after the
  gate was fixed, because the fixed gate rightly blocks force-push.
  Revert PR used instead.
- **Three environments (dev/staging/prod)** — rejected (see §3).
- **Databricks for this project** — rejected (see ADR 0001). Captured
  as future-work.
- **Session-doc methodology** — initially rejected ("not in use"),
  then adopted at session end. The reversal is documented so future
  readers see the arc rather than only the final state.

## 11. Open Loops at Session End

Captured in `OPEN_LOOPS.md`, not here. Summary:

- Add GitHub repo topics (`data-engineering elt dbt bigquery terraform
  portfolio-project`).
- Set `git config --global fetch.prune true`.
- Once CI exists (gated on B6), populate the `protect-main` ruleset's
  "Require status checks to pass" list with each CI job's name.
- Enable "Automatically delete head branches" in repo settings so merged
  feature branches get deleted automatically rather than requiring a
  manual click.

## 12. Files Changed

### Created

| File | Purpose |
|---|---|
| `README.md` | Project one-pager — what oss-pulse is, questions it answers, scope boundaries, status |
| `DECISIONS.md` | Ten locked operating decisions |
| `FOUNDATION_BACKLOG.md` | Phased foundation task tracker (A → D) |
| `OPEN_LOOPS.md` | Ad-hoc housekeeping queue |
| `CLAUDE.md` | Claude Code session-startup instructions |
| `docs/adr/0000-template.md` | Michael Nygard ADR skeleton |
| `docs/adr/0001-tech-stack.md` | Tech stack rationale (A4) |
| `documentation/Session01_20261005_initial_bootstrap_and_foundation_docs.md` | This file |
| `documentation/DECISION_LOG.md` | Session-indexed subsystem history, initial version |

### Modified

| File | Change |
|---|---|
| `DECISIONS.md` | §9 extended to codify the no-AI-attribution rule |
| `FOUNDATION_BACKLOG.md` | A1-A3 marked complete at bootstrap; A4, B10, B7 (early), A14 (retroactive) marked complete through session; change-log entries added |
| `README.md` | Repo map updated to list `OPEN_LOOPS.md` and `CLAUDE.md`; status section updated |
| `CLAUDE.md` | Project-memory section flipped from "session docs not in use" to "session docs in use" |

### GitHub artifacts (not in repo tree)

| Artifact | Purpose |
|---|---|
| `protect-main` ruleset (Active, targets `main`) | Enforces no-direct-push, no-force-push, no-delete, require-PR |
| 5 merged PRs (#1-#5) | Workflow verification + content |
| Public repo visibility | Required for ruleset enforcement on free account |

### Cross-repo / cross-system changes

| Location | Change |
|---|---|
| `~/.claude/CLAUDE.md` (global) | New "No AI-assistant attribution" subsection under Anti-patterns to avoid |
| `color-analytics/memory/feedback_no_ai_attribution.md` | New feedback-type memory file |
| `color-analytics/memory/MEMORY.md` | New index pointer to the above |

### Commit timeline on `main`

```
10. (this session doc, in flight) docs: adopt session-doc methodology and document Session 01
 9. docs: add project-level CLAUDE.md for session orientation (A14) (#5)
 8. docs: land ADR template and ADR 0001 (tech stack & rationale) (#4)
 7. chore: add OPEN_LOOPS.md for ad-hoc housekeeping tasks (#3)
 6. Revert "test: should be rejected by protect-main" (#2)
 5. test: should be rejected by protect-main (preserved as record)
 4. chore(backlog): close B7 — branch protection active via protect-main ruleset (#1)
 3. docs(decisions): forbid AI-assistant attribution in commits and PRs
 2. chore: bootstrap repo with foundation documents
 1. Initial commit (LICENSE, from GitHub)
```

---

**Next session's first action:** read `CLAUDE.md`, follow the
session-startup checklist, open `FOUNDATION_BACKLOG.md`, pick the next
unchecked item. The item is **A5 — Architecture doc + diagram**.
