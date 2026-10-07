# Session 03 — A6 CONVENTIONS.md and the No-Local-Docker Decision

**Date:** 2026-10-06
**Status:** Complete
**Quiz:** [Quiz03](quizzes/Quiz03_20261006_tooling_and_serverless.md)
**Focus:** Close backlog item A6 (CONVENTIONS.md), lock the
"no local Docker; deploy via `gcloud run --source`" operating decision
as DECISIONS.md §10, get `gh` CLI operational so future sessions
can open PRs from the terminal, and codify + enforce the
session-startup required-reading list via `.claude/settings.json`
SessionStart hook.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Motivation and Context](#2-motivation-and-context)
3. [`gh` CLI Bring-Up](#3-gh-cli-bring-up)
4. [A6 — CONVENTIONS.md Contents](#4-a6--conventionsmd-contents)
5. [DECISIONS §10 — No Local Docker](#5-decisions-10--no-local-docker)
6. [Required-Reading Hook (`.claude/settings.json`)](#6-required-reading-hook)
7. [PRs and Workflow Notes](#7-prs-and-workflow-notes)
8. [Decisions and Rejections](#8-decisions-and-rejections)
9. [ELI5 Topics This Session](#9-eli5-topics-this-session)
10. [Open Loops at Session End](#10-open-loops-at-session-end)
11. [Files Changed](#11-files-changed)

---

## 1. Overview

Three PRs landed:

- **PR #8 — `docs: add Session 02 doc and update DECISION_LOG`** —
  the carryover from Session 02. The Session 02 doc existed on the
  `docs/session02` branch but had never been PR'd; Session 03 opened
  it, merged, and cleaned up the branch.
- **PR #9 — `docs: CONVENTIONS.md (A6) + no-local-Docker decision`**
  — bundled A6 (new file at repo root) with a DECISIONS.md addition
  that locked the "no local Docker; deploy via `gcloud run deploy
  --source .`" call that surfaced during the A6 discussion. The
  former §10 (scope boundaries) was renumbered to §11 and every
  cross-reference across `CLAUDE.md`, `README.md`, and
  `docs/architecture.md` was updated in the same commit.
- **PR #10 — this session's doc + DECISION_LOG update + quiz.**

Backlog progress at session close:
- Phase A: **8 / 14** complete (adds A6)
- Phase B: 2 / 10
- Phase C: 0 / 8
- Phase D: 0 / 5

## 2. Motivation and Context

### Problem

- **A6 was the next unchecked item.** Project needed a single file
  that said how we name things, format Python and SQL, shape commit
  messages, and decide whether a line of code earns a comment —
  without re-litigating every PR.
- **Session 02's doc was still on a feature branch.** The commit
  (`563d711`) existed on `origin/docs/session02` but no PR had been
  opened. Had to clear this before any Session 03 work could land.
- **`gh` CLI had been installed earlier that session but never
  authenticated.** Session 02 noted "either install `gh` or keep
  budgeting the paste step"; this session completed the install.

### Approach

Sequential, three branches:

1. Verify `gh --version`, run `gh auth login` (interactively; user
   drove), open PR #8 for the Session 02 carryover. Review, squash,
   delete branch.
2. Pull `main`, cut `docs/conventions-md`. Adapt
   `../Codebase_ColorAnalytics/02_scripts/color-analytics/CONVENTIONS.md`'s
   structure, consolidate project-specific rules (don't re-litigate
   what DECISIONS.md already locks), add the one new call
   (comments default to none; only when the *why* is non-obvious).
   During the discussion, the "should we Docker-ize local dev?"
   question surfaced and was decided — captured in the same PR as
   DECISIONS.md §10.
3. On `docs/session03`, write this file, the Decision Log entries,
   and the Quiz 03 file. PR, merge.

### Prior Art

- **Color-analytics' `CONVENTIONS.md`** — provided the structure
  (verb/object naming grid, deprecated terms table, worked-rename
  examples, DB-contract-freeze rule). oss-pulse's version is thinner
  because most project-specific rules already live in DECISIONS.md
  §4 and §9; this file consolidates and points.
- **Global `CLAUDE.md`'s "Naming" section** — the four rules
  (vocabulary consistency, altitude matches specificity, pipeline
  stage format `s<N>_<subject>_<input>_to_<output>.py`, length is
  OK when it earns its place) ported in directly.
- **Global `CLAUDE.md`'s "Default to writing no comments" rule** —
  provided the frame for CONVENTIONS §7. Legitimate reasons
  (hidden constraints, subtle invariants, workarounds, surprising
  business rules) vs. illegitimate reasons (restating what the code
  does, referencing current PR, "added for X flow", section headers)
  came from that rule.

## 3. `gh` CLI Bring-Up

Installed earlier in the session as a parallel chore; this session
completed authentication.

- `gh --version` → `2.102.0`. Confirmed present on PATH.
- First auth attempt used an existing fine-grained PAT (`github_pat_*`).
  `gh pr create` failed with `GraphQL: Resource not accessible by
  personal access token (createPullRequest)` — the token had been
  provisioned without "Pull requests: write" scope.
- Decision: re-auth via OAuth web browser flow rather than editing the
  PAT. Rationale: for a human-on-laptop workflow, OAuth is the
  default-correct credential; PATs shine when a CI job or script
  needs a narrower, auditable credential. The OAuth preset covers
  normal `gh` operations in one approval click.
- `gh auth login` (user ran interactively) → HTTPS, authenticate git
  with GitHub credentials, browser flow. Resulted in a `gho_*` token
  with scopes `gist, read:org, repo, workflow`. `gh pr create`
  worked on retry.
- Side benefit: `gh` is now the credential helper for `git`, so
  `git push` reuses the same auth. No separate credential prompts.

## 4. A6 — CONVENTIONS.md Contents

Seven sections, written to be a pointer-heavy consolidation rather
than a self-contained style guide:

| § | Content |
|---|---|
| 1 | **Naming — meaning out of context.** The four rules + a pointer to DECISIONS.md §4 for the project-specific name shapes (bucket, dataset, table, service account, Secret Manager, Python module, dbt model, Terraform resource). A "deprecated terms" subsection exists but is empty — populate as vocabulary stabilizes. |
| 2 | **Python style.** Ruff (format + lint, config in `pyproject.toml`), `mypy --strict`, line length = ruff default (88), ruff's import sorter, identifier case conventions, pointers out to DECISIONS §6/§7/§8 for errors, resources, and tests. |
| 3 | **SQL style.** `sqlfluff` with BigQuery dialect, lowercase keywords, leading commas, CTEs over subqueries, one statement per file (dbt enforces), always `{{ ref() }}` and `{{ source() }}`, column order in marts (keys → dimensions → measures → timestamps), no `SELECT *` in production models. |
| 4 | **Branch names** — pointer to DECISIONS §9. |
| 5 | **Commit messages** — pointer to DECISIONS §9. |
| 6 | **PR titles & descriptions.** Title matches the squash-merge commit (`type(scope): subject`). Description template (what / why / how tested / what could break) until B8's PR template lands. No AI-attribution footers. |
| 7 | **When to write comments.** The one genuinely new rule. Default: don't. Only when the *why* is non-obvious — the test is "if I delete this comment, would a future reader plausibly misunderstand the code?" Four legitimate reasons listed (hidden constraints, subtle invariants, workarounds for specific external bugs, surprising business rules), four illegitimate ones listed (restating code, referencing current task/PR, "added for X flow", section headers). Docstring guidance plus a worked example of a pipeline-stage module docstring (reads / writes / fail-fast triggers). dbt subtlety: prefer `description:` in `schema.yml` over inline `-- comments`. |

### Judgment call captured here

The comments rule was placed in CONVENTIONS.md §7 rather than as a
new DECISIONS.md section. Rationale: operating decisions
(DECISIONS.md) describe the project's shape — environments, regions,
scope, error-handling as a system property. Style conventions
(CONVENTIONS.md) describe how a human reads code. They age
differently: operating decisions get locked once and rarely change;
style conventions evolve as the codebase grows.

## 5. DECISIONS §10 — No Local Docker

Surfaced mid-session when the user asked: "should the repo run via
Docker so I never install packages locally?" Color-analytics does
exactly that; a sibling-project default would have been reasonable.
After pushback, decided *against* it for oss-pulse. The decision was
written up in DECISIONS.md inline (not as a new ADR) because it's a
project-wide operating decision, not an architectural trade-off with
alternatives worth preserving in a separate document.

### What was decided

- **Deploy mode:** `gcloud run deploy --source .` — Cloud Run
  Buildpacks build the image; no `Dockerfile` in the repo.
- **Local dev tools** (`ruff`, `mypy`, `sqlfluff`, `pre-commit`,
  `uv`, `gh`, `gcloud`, `terraform`) run natively on the host.
- **Project Python dependencies** are managed by `uv`, which
  creates a project-local `.venv/` invisibly. No `pip install` into
  system Python, ever. No manual venv activation.

### Why oss-pulse ≠ color-analytics on this axis

Color-analytics has heavy native dependencies (OpenCV, GPU
libraries, Postgres, segmentation models) that are genuinely painful
to install cross-platform; Docker pays for itself the first time it
avoids a CUDA-build afternoon. oss-pulse is the opposite shape —
pure-Python packages (`requests`, `pyarrow`,
`google-cloud-bigquery`), SQL, and some CLIs (`gcloud`, `terraform`,
`dbt`). None of these fight you to install, so Docker's dev-loop
tax (slower pre-commit, IDE can't see tools, Windows WSL2 overhead)
isn't paid for by a corresponding benefit.

### What "containerized serverless ETL" still means in the portfolio story

The deployment artifact IS a container — Cloud Run runs containers.
What changes is the *author* of the Dockerfile: Google writes it
(via Buildpacks), not us. If a future interviewer asks "where's your
Dockerfile?", the answer is "I chose source-based deploys so I'd
show when *not* to pay a cost — a hand-rolled Dockerfile for a
small batch ingest would have been maintenance tax (base image
updates, layer ordering, security scanning) for zero functional
gain." That's a stronger portfolio story than "I pattern-matched to
Docker because the ecosystem talks about it a lot."

### Honest hedge: 60% technical, 40% portfolio

A direct question later in the session asked whether I was conceding
Docker to be amicable or whether it was genuinely warranted. The
honest answer: for the project's actual shape, Docker is maybe 60%
warranted and 40% portfolio-narrative. For a solo DE project, the
narrative weight is real but shouldn't drive the decision; the
technical weight is light. Call it: no Docker.

### Related clarification that landed

The user asked whether an "hourly" pipeline requires their PC to be
on 24/7. No — this is the point of the serverless choice. Cloud
Scheduler fires on cron; Cloud Run spins up a container for ~2
minutes/hour and shuts down. Nothing of the user's runs 24/7.
Billing target ($0/month) survives because 24 runs × 2 min × 1 vCPU
is well inside Cloud Run's free tier. No change to any doc — the
answer is already implicit in ADR 0001 and the architecture doc —
but the clarification is why "scheduled hourly" doesn't contradict
"$0 month target."

### §10 → §11 renumber housekeeping

The former §10 (scope boundaries) became §11. Updated references in:

- `CLAUDE.md` ("Scope boundaries live in `DECISIONS.md` §11.")
- `README.md` ("See `DECISIONS.md` §11 for the full list.")
- `docs/architecture.md` ("both require ADRs under `DECISIONS.md`
  §11.")

Deliberately left untouched: `documentation/Session01_…md` — it's a
historical artifact dated 2026-10-05, and rewriting it to match a
later renumber would misrepresent what was true at the time.

## 6. Required-Reading Hook

Mid-session the user asked whether Claude should always read the
project-level required docs and reference docs at the start of every
session. The honest answer landed in two parts:

- **Required-reading tier** (CLAUDE.md, FOUNDATION_BACKLOG,
  OPEN_LOOPS, DECISIONS, CONVENTIONS) — yes, always. Small, high
  signal, affects decisions on every PR.
- **Reference docs** (README, architecture, every ADR) — my initial
  recommendation was to leave them task-triggered to protect context
  budget. The user overrode this and asked for them to be enforced
  too. Decision honored.

Enforcement is three parts:

1. **`CLAUDE.md § Session startup — required reading`** was rewritten
   from "read in this order" (advisory) into a two-tier required list
   (operating context + reference context) with explicit "no
   exceptions" framing. The CLAUDE.md list is the authoritative source
   if hook text and docs ever drift.
2. **`.claude/settings.json`** (new file, checked into the repo) adds
   a `SessionStart` hook that emits
   `hookSpecificOutput.additionalContext` instructing Claude to
   follow the required-reading list in `CLAUDE.md § Session startup`
   — **the hook does not list filenames**, it points at CLAUDE.md as
   the single source of truth. First draft of the hook did spell out
   every file; a quick second pass caught the duplication risk (list
   lives in two places; adding A7 would force a settings.json edit
   too) and refactored to the pointer form. Validated by extracting
   the command, `eval`ing it, parsing the output as JSON
   (`additionalContext` length 497 chars, parses cleanly).
3. **Hook does not fire this session.** `SessionStart` hooks fire at
   session boot; adding one mid-session does not retroactively fire
   it. First activation happens on the next fresh session (or after
   the user opens `/hooks` to reload config).

### Alternatives considered

- **Harden the CLAUDE.md instruction only (option 2 from the
  discussion).** Rejected because the project CLAUDE.md already *told*
  Claude to read these files; it was advisory and sometimes
  skipped. Enforcement needs the hook.
- **A `UserPromptSubmit` hook that fires on every prompt.** Rejected
  as overkill — the required-reading list only needs to be loaded
  once per session, not re-injected before every message.
- **Omit reference docs from the required list.** This was my
  initial recommendation. User overrode on the grounds that
  consistency matters more to them than context budget conservation.
  Documented but not acted on.
- **Spell out every filename in the hook itself.** The first draft
  did this. Caught and reverted: it duplicated CLAUDE.md's list,
  which meant every new doc (A7, A8, ...) would force a parallel
  settings.json edit, and drift between the two files would be
  silent. The pointer-form hook is strictly better — one file to
  update as the doc set grows.

### Portability note

The hook uses `"shell": "bash"` explicitly. On this Windows machine
Git Bash is installed (git / `gh` both work), so bash is available.
If a future environment lacks Git Bash, the hook silently no-ops and
Claude falls back to the human-readable instruction in CLAUDE.md.
PowerShell equivalent is left for later if needed.

## 7. PRs and Workflow Notes

Three full-cycle PRs through `protect-main`:

| # | Title | Branch | Merge commit |
|---|---|---|---|
| 8 | `docs: add Session 02 doc and update DECISION_LOG` | `docs/session02` | `5df860b` |
| 9 | `docs: CONVENTIONS.md (A6) + no-local-Docker decision` | `docs/conventions-md` | `a9aacf4` |
| 10 | *(this session's doc + Decision Log + quiz)* | `docs/session03` | *(pending at write time)* |

### Workflow notes

- **`gh pr create` now works end-to-end.** First successful terminal
  PR open was PR #8. The paste-into-UI workaround from Session 02 is
  retired.
- **Two commits on one branch, squash-merged.** PR #9 held two
  logical changes (A6 landing + DECISIONS §10 addition). Discussed
  briefly whether to split; kept as one because the Docker decision
  surfaced during A6 and the PR body makes both pieces visible to
  the reviewer. The squash commit flattens them anyway.
- **Orphaned-commit mini-detour.** User surfaced hash `a38a280` and
  asked whether git could still see it. Confirmed: it's reachable
  via reflog (HEAD@{31}) and will auto-expire in ~90 days. Content
  (the `OPEN_LOOPS.md` blob) is byte-identical to what's live on
  main under PR #3's squash commit (`7a98b0b`), so nothing lost.
  No action needed, but documented the manual cleanup path for
  future reference: `git reflog expire --expire-unreachable=now
  --all; git gc --prune=now`.

## 8. Decisions and Rejections

| Decision | Rationale |
|---|---|
| Open Session 02's unmerged commit as PR #8 before any Session 03 work | Keeps `main` linear; Session 03's branch cuts from a `main` that already contains Session 02. |
| OAuth web-browser auth for `gh`, not fix the fine-grained PAT | For a human-on-laptop workflow, OAuth is the default-correct credential and the preset covers normal operations. PATs are for narrow CI credentials. |
| CONVENTIONS.md is a thin pointer file, not a self-contained style guide | DECISIONS.md already locks most project-specific rules. Duplicating them in CONVENTIONS.md creates drift risk. Single source of truth > reader convenience of one file. |
| Comments rule in CONVENTIONS.md, not DECISIONS.md | Style conventions vs. operating decisions — different half-life, different audience. See §4 above. |
| No local Docker | 60% technical (dev-loop friction, pure-Python stack, Windows WSL2 overhead), 40% narrative (portfolio story is still "containerized serverless ETL"; we just didn't write the Dockerfile Google writes for free). |
| DECISIONS §10 inline, not a new ADR | Operating decision, not an architectural tradeoff worth preserving alternatives. If a future need forces a custom Dockerfile, that's when the ADR gets written. |
| Renumber scope-boundaries §10 → §11 rather than adding Docker as §11 | §10 flows naturally after §9 (commit/branch/PR) — both are "how we work day-to-day" sections. Scope boundaries belong at the end, as the "and here's what's out of scope" closer. |
| Bundle A6 + DECISIONS §10 in one PR | Both docs-only, both touched during the same conversation, PR body makes both pieces discoverable to the reviewer. |

Rejections:

- **Add Docker because the sibling project uses it** — rejected. The
  two projects have different stack shapes; blind symmetry is the
  wrong default.
- **Write a Dockerfile anyway "for the portfolio"** — rejected. The
  deployment artifact is already a container; author of the
  Dockerfile doesn't need to be us.
- **Edit the fine-grained PAT to add PR scope** — rejected in favor
  of OAuth. User would have had to walk through GitHub's token UI,
  find the right section, re-authorize gh anyway. OAuth is one
  browser click.
- **Fix the Session 01 doc's §10 reference** — not relevant this
  session (Session 01 doesn't reference it), but the general
  principle: don't retroactively edit historical session docs.

## 9. ELI5 Topics This Session

Four ELI5-shaped explanations given this session. All four are
general software-engineering concepts, not oss-pulse-specific. Quiz
file at [`quizzes/Quiz03_20261006_tooling_and_serverless.md`](quizzes/Quiz03_20261006_tooling_and_serverless.md).

1. **Linters and formatters** (ruff / mypy / sqlfluff). What a
   linter is, what a formatter is, why the Python community
   consolidated on ruff, what `mypy --strict` buys you, how
   sqlfluff fits the same mold for SQL.
2. **Diff-friendly SQL patterns.** Three worked examples with
   visual diffs: leading commas (one-line change to add a column),
   CTEs vs nested subqueries (named steps the diff can touch
   independently), no `SELECT *` in prod models (schema changes
   become visible in PRs instead of landing silently).
3. **Serverless scheduling.** How Cloud Scheduler + Cloud Run let
   an "hourly" pipeline run without any machine of the user's
   being on. Cost model: pay for ~2 minutes/hour of actual work,
   not 24 hours of idle VM.
4. **uv-vs-Docker for local Python tooling.** Why `uv` solves the
   same problems Docker does (no system-Python pollution, no venv
   activation ritual, clean uninstall) with none of the dev-loop
   tax, and where Docker is actually still worth it (deployment
   artifact, hard-to-install native deps — color-analytics' case,
   not oss-pulse's).

## 10. Open Loops at Session End

Nothing new added to `OPEN_LOOPS.md` this session. Pre-existing open
loops unchanged:

- GitHub repo topics still unadded.
- `git config --global fetch.prune true` still unset.
- CI status checks still absent from the `protect-main` ruleset
  (gated on B6).

Follow-ups implied by this session (not yet filed anywhere):

- **A7 — Data contract** is the next unchecked backlog item. The
  mart list from `architecture.md` §4 is the authoritative source
  for which marts the contract needs to describe.
- **`uv` and `pre-commit` need to be installed on the host** when
  Phase B starts. Not now; this is a Phase B task implied by
  DECISIONS §10.
- **`pyproject.toml` will land in Phase B (B3)** and that's where
  ruff / mypy / sqlfluff get their project-level config. CONVENTIONS
  §2 and §3 reference these configs in advance; B3 populates them.
- **Vocabulary table in CONVENTIONS.md §1 is empty.** Populate as
  terms stabilize — likely during A7 (data contract) when the
  domain nouns get locked.

## 11. Files Changed

### Created

| File | Purpose |
|---|---|
| `CONVENTIONS.md` | The A6 code & docs conventions file. 207 lines. |
| `documentation/Session03_20261006_a6_conventions_and_no_local_docker.md` | This file. |
| `documentation/quizzes/Quiz03_20261006_tooling_and_serverless.md` | End-of-session quiz across the four ELI5 topics. |
| `.claude/settings.json` | New file. `SessionStart` hook enforcing required-reading list. |

### Modified

| File | Change |
|---|---|
| `DECISIONS.md` | New §10 (Runtime, packaging, and deployment); former §10 renumbered to §11; change-log entry added. |
| `CLAUDE.md` | Scope-boundaries pointer §10 → §11. Session-startup section rewritten from advisory to required two-tier list (operating context + reference context); pointer to `.claude/settings.json` hook. |
| `README.md` | Scope-boundaries pointer §10 → §11. |
| `docs/architecture.md` | ADR trigger pointer §10 → §11. |
| `FOUNDATION_BACKLOG.md` | A6 marked `[x]`; change-log entry for 2026-10-06 A6 closure. |
| `documentation/DECISION_LOG.md` | S03 entry under Foundation & Governance; chronological index updated; current-outlook refreshed. |

### GitHub artifacts

| Artifact | Purpose |
|---|---|
| PR #8 (merged, `5df860b`) | Session 02 doc + DECISION_LOG carryover. |
| PR #9 (merged, `a9aacf4`) | A6 CONVENTIONS.md + DECISIONS §10 no-local-Docker. |
| PR #10 (pending) | Session 03 doc + DECISION_LOG update + Quiz 03. |

### Commit timeline on `main` since Session 02 close

```
a9aacf4 docs: CONVENTIONS.md (A6) + no-local-Docker decision (#9)
5df860b docs: add Session 02 doc and update DECISION_LOG (#8)
```

Session 03's doc + Decision Log update + Quiz 03 land in a third
commit on `docs/session03`, PR'd as #10.

---

**Next session's first action:** read `CLAUDE.md`, follow the
session-startup checklist, open `FOUNDATION_BACKLOG.md`, pick the next
unchecked item. The item is **A7 — Data contract**.
