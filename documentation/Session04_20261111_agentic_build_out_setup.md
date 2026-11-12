# Session 04 — Agentic Build-Out Setup, A7–A9, and the GH Archive URL Fix

**Date:** 2026-11-11
**Status:** Complete (milestone 1 in progress)
**Focus:** Decide how to finish oss-pulse with AI agents doing most of the
building while the author has much less time. Lock the operating model
(ADR 0002): isolated agent identities, a billed-but-hard-capped dev
project, an integration branch, and test-first development plus
verifiers. Then start milestone 1:
- commit the data contract (A7);
- land the access matrix (A8) and the runbook (A9);
- correct a measurement error that had made GH Archive look ~35%
  unavailable.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Motivation and Context](#2-motivation-and-context)
3. [Gap Analysis: What Stands Between Today and a Working Project](#3-gap-analysis)
4. [Designing the Agentic Workflow](#4-designing-the-agentic-workflow)
5. [Step 0: A7 Close-Out and the Baseline](#5-step-0-a7-close-out-and-the-baseline)
6. [Data Findings](#6-data-findings)
7. [ADR 0002: How It Changed Under Review](#7-adr-0002-how-it-changed-under-review)
8. [A8 Access Matrix and A9 Runbook](#8-a8-access-matrix-and-a9-runbook)
9. [Independent Review Results](#9-independent-review-results)
10. [Decisions and Rejections](#10-decisions-and-rejections)
11. [Work in Progress: A11 Cost Model Estimates](#11-work-in-progress-a11-cost-model-estimates)
12. [Open Items at Session End](#12-open-items-at-session-end)
13. [ELI5 Topics This Session](#13-eli5-topics-this-session)
14. [Files Changed](#14-files-changed)

---

## 1. Overview

**Starting point.** The author said they no longer have the time they
used to, and asked how agents could build the rest of the project
"to completion, using proper workflows and development practices,"
stopping short of creating accounts and deploying.

**What the session produced:**
- **A gap analysis.** It found 27 open backlog items, about ten promises
  scattered across the docs that no backlog item tracked, and seven needs
  written down nowhere.
- **A verification-first agent workflow,** designed with the author.
- **ADR 0002,** recording that workflow and the safety model around it.
- **A merged baseline:** `main` was tagged `baseline-pre-agentic`, and all
  agent work now flows through the `build/agentic` integration branch.

**PRs merged:** five.
- **#11 into `main`:** A7 data contract.
- **#12–#15 into `build/agentic`:** ADR 0002, the contract URL fix, A8
  and A9.

**Review caught real problems.** Each PR into `build/agentic` got an
independent review agent, and those reviews found **five blockers**,
all fixed before merge:
1. The BigQuery no-billing sandbox can't run dbt incremental models.
2. Agents were running with the author's own credentials.
3. Fine-grained GitHub tokens can't act on a personal repo where the bot
   is only a collaborator.
4. `main` didn't require an approval, so a Write-access bot could merge.
5. Re-linking billing after the kill switch fires would trigger it again.

**The most consequential data finding.** GH Archive URLs use an
**unpadded hour** (`2026-11-10-5.json.gz`). The contract's "~35% of hours
missing" came from probing zero-padded URLs. Re-probing three full days
found **72 of 72 hours present.**

**Backlog at session close:**

| Phase | Done |
|---|---|
| A | 10 / 14 (adds A7, A8, A9) |
| B | 2 / 11 (B11 added) |
| C | 0 / 10 (C9, C10 added) |
| D | 0 / 5 |

## 2. Motivation and Context

### Problem

The project was mid-foundation (A1–A6, A14, B7, B10 done; A7 drafted
in an undocumented session on 2026-10-07 but never committed). The
author's available time dropped sharply. Finishing by hand at the
original pace wasn't realistic, but handing the build to agents raised
three worries the author named directly:
1. Running up costs unexpectedly.
2. Security.
3. The author must create every account personally.

### Approach

1. Answer "what's left?" honestly, including work no tracker covered.
2. Design an agent workflow where correctness comes from **checks the
   agent can't quietly weaken**, not from trusting agent output.
3. Write the operating model down as an ADR before any agent writes
   pipeline code.
4. Run milestone 1 (the remaining foundation docs) through the new
   workflow, so the workflow itself gets tested on low-risk work.

### Prior Art

- **Session 01** established the PR-only workflow and the `protect-main`
  ruleset, which this session found too weak for a bot collaborator.
- **Session 02** produced `docs/architecture.md`. This session found
  several places where it has drifted (queued under A10).
- **Session 03** produced CONVENTIONS.md and DECISIONS §10 (no local
  Docker; `gcloud run deploy --source`). The access matrix's deploy
  identities follow §10.

## 3. Gap Analysis

The author asked: "Once all the items in the foundation backlog are
complete, what's next?" The backlog's own answer has three steps:
1. archive the backlog;
2. create `ROADMAP.md` from `docs/roadmap.md`;
3. open the first ingest PR.

But `docs/roadmap.md` doesn't exist. It's what A10 produces, and A10 was
unchecked.

A follow-up question ("are there any other steps... before this project
is fully realized?") produced three groups:

**1. Tracked:** 27 unchecked backlog items, plus the handoff.

**2. Promised in docs, but tracked nowhere:**
- the ingest ADR (cron offset, backfill window);
- `raw_ingest_audit` and its alerting;
- the `primary_language` source;
- the README ↔ contract reconcile;
- CI checks in the ruleset;
- Great Expectations on raw (promised by ADR 0001 and README);
- license and going public;
- optional Dagster/Kestra practice;
- scheduled reviews.

**3. Needed, but written down nowhere:**
- Terraform for the Cloud Run services, the Scheduler and the alert
  policy (C5 only covers buckets, datasets and service accounts);
- a deploy workflow;
- the production alert path (C8 only proves CI → Slack);
- a **data-contract bug:** `mart_language_share` still counted
  `PushEvent`, which is absent from the feed;
- storage under "keep forever" would exceed the free tiers within
  months;
- `architecture.md` drift;
- no definition of "v1 done."

**What the author chose:**
- **(c)** Fix the contract issues on the still-open A7 branch now.
- **(b)** Hold everything else as inputs to A10. These were written into
  `FOUNDATION_BACKLOG.md` under A10 as "Inputs to fold in."

**Later correction:** the "license and going public" item was stale. The
repo is already public and has had an MIT `LICENSE` since its first
commit. It's noted here for the A10 roadmap pass.

## 4. Designing the Agentic Workflow

### 4.1 The video, and what transfers

The author shared a talk arguing that engineering is shifting from
writing code to building **verifiers**: deterministic checks an agent
can grind against. The talk's example was a pixel diff that let agents
iterate for days on Figma import fidelity.

**What transfers:**
- An agent can only work unattended against a check it can't fake.
- The human's job moves from reviewing output to approving what the
  checks are.

**What doesn't transfer:**
- **No ground truth to compare against.** The talk had one: the original
  design file. oss-pulse has no "correct mart" to diff against, so that
  ground truth has to be built, from small hand-checked datasets.
- **Pass/fail, not a score.** Most of this project's checks pass or fail;
  there's no number to grind down. No score would have caught that README
  questions about pushes were unanswerable.
- **Agents game tests.** Tests are easier to game than pixel diffs.
- **Unreviewable history.** Days of unsupervised churn doesn't leave a
  history a portfolio reviewer can follow.

### 4.2 Verifier ideas and the author's picks

Thirteen ideas were proposed. Asked "how could #1 go wrong?", the
analysis of the two-independent-implementations idea concluded that its
main risk is correlated error: both versions agree and are both wrong,
whether from a shared misreading of the spec or an agent "fixing" a
disagreement by copying. **The author chose seven, plus test-driven
development (TDD) wherever code has executable behavior:**

| # | Verifier | What it really is | Where it runs |
|---|---|---|---|
| 2 | Change the input in a known way; the output must change in the matching way (reload an hour → nothing changes; shift timestamps a day → dates shift, values don't; shuffle actors → Gini unchanged) | Metamorphic testing | PRs touching ingest or dbt |
| 3 | Counts that must balance (file lines = raw rows; raw = staging + dropped + rejected; mart totals = fact counts) | Reconciliation | Every dbt build, in CI **and hourly in prod** |
| 4 | `dbt build --empty` and dry-runs against real BigQuery | Static validity check | Every PR |
| 6 | Commands in the docs are executed in CI | Executable documentation | PRs touching docs |
| 7 | A fresh agent rebuilds the contract entry from the code alone; diff against the real one | Spec-conformance review (TDD in reverse) | PRs touching ingest or dbt |
| 8 | A red-team agent writes realistic breaking inputs as failing tests; the round stops after 3 consecutive failed attempts | Adversarial testing | End of each code milestone |
| 9 | Every failure mode in contract §3.3 gets an ID and a test, and coverage must be 100% | Acceptance-test-driven development | Every PR |

**How TDD fits:**
- A **test-writer agent** that never sees the implementation writes
  failing tests first.
- **CI proves they're red:** the new tests run against the base branch
  and must fail.
- **Tests are frozen after that:** CI blocks any later commit in the PR
  from touching `tests/`.

TDD doesn't apply to docs items, the dev-project spike, or pure-config
scaffolding. Those rely on planted-bad-input drills instead.

### 4.3 Workflow decisions

| Question | Decision |
|---|---|
| Who merges agent PRs? | The agent squash-merges into `build/agentic`. The author promotes milestones to `main`. |
| How is it run? | One builder session that spawns specialist subagents (test-writer, reviewer, spec-reconstructor, red team). Not a parallel multi-agent workflow. |
| Cloud access | The author first chose a no-billing sandbox. Review showed it can't work (§7), so dev became billed with hard caps plus a kill switch. |
| Agent identities | Bot GitHub account and bot Google account. The author's Owner `gcloud` login stays off the agent's machine. |
| Milestone promotion method | Deferred ("stay on the branch for now"). Tracked in `OPEN_LOOPS.md`. |

The full plan is in the author's plan file. Its durable parts are in
ADR 0002 and in the A10 inputs list.

## 5. Step 0: A7 Close-Out and the Baseline

1. **Checked the `merged` question against real data** (§6.1). The
   contract's `is_pr_merged` was right, and I had been wrong to doubt it.
2. **Fixed `mart_language_share`:**
   - `distinct_contributors` is now "actors with an opened or merged PR"
     (it had been `PushEvent` or merged PR).
   - The denominator now uses the same events.
   - Added a note that shares can sum past 100%.

   Why "opened or merged" rather than "opened a PR or an issue": it keeps
   the metric about code contribution, the closest match to the original
   push-based intent.
3. **Added the A10 inputs list** to the backlog.
4. **PR #11** (`docs(contract): add data contract (A7) and queue gaps for
   A10`) was squash-merged by the author.
5. **Baseline:** tagged `main` at `c24242e` as `baseline-pre-agentic`
   (pushed), and created `build/agentic` from it (pushed).

## 6. Data Findings

### 6.1 PullRequestEvent actions (3 hours, 2026-11-10 15–17 UTC)

| Measure | Value |
|---|---|
| Events | 9,017 (~3,000/hour) |
| Gzipped size | 2.0–2.4 MB/hour (October baseline: 6.5–14.2 MB) |
| PullRequestEvent | 4,009 |
| `action = opened` | 1,595 |
| `action = merged` | 1,428 |
| `action = labeled` | 676 |
| `action = closed` | 76 |
| `payload.pull_request` keys | only `url`, `id`, `number`, `head`, `base` (no `merged` flag) |
| Event types present | PullRequest, Issues, PullRequestReview, Watch, Release, IssueComment, Fork, Member, Gollum, CommitComment, Public, Discussion. **Still no PushEvent.** |

**Side note:** on a `merged` event, the `actor` is whoever merged the PR,
usually a maintainer, not its author. This is now noted in contract §5.1.

### 6.2 GH Archive hour URLs are unpadded

| URL | HTTP |
|---|---|
| `2026-11-10-5.json.gz` | 200 |
| `2026-11-10-05.json.gz` | 404 |
| `2026-11-10-0.json.gz` / `-00` | 200 / 404 |
| `2026-11-09-3.json.gz` / `-03` | 200 / 404 |

Full-day probes with unpadded URLs:

| Day | Present |
|---|---|
| 2026-10-06 | 24/24 |
| 2026-10-07 | 24/24 |
| 2026-11-09 | 24/24 |

**Consequences (PR #14):**
- **§3.1:** the URL pattern is now `<YYYY-MM-DD-H>`. The project's own hour
  string stays padded, so ingest must convert, and a test covers hours
  0–9.
- **§3.2:** availability is 72/72.
- **§3.2.1:** the old measurement now carries a correction note.
- **§3.3:** a missing hour is now rare. It alerts after 3 failed attempts,
  instead of being treated as routine and alerting only past a 60% daily
  miss rate.

How the bug was found: while writing the runbook's replay procedure, the
URL format looked worth checking. It's an example of the "every claim
needs a receipt" verifier idea (#5) catching something even though it
wasn't selected.

## 7. ADR 0002: How It Changed Under Review

**Draft 1** ("against a no-billing sandbox dev project"):
- dev in a BigQuery sandbox, which can't be charged;
- agents impersonating a dev service account from the author's login;
- command deny-rules as a guard.

**Review blocker 1 (credentials).** Impersonation starts from the
author's own login, and that login (Owner, with billing rights) stays on
disk. Deny-rules match command text and are easy to get around. Also,
the agent's `gh` CLI was the author's admin account.

**Review finding 2 (sandbox), confirmed against Google's docs:**
- The sandbox doesn't support DML, so no `MERGE`, so no dbt incremental
  models.
- Storage is a 10 GiB *lifetime* limit, and "this quota is not refunded
  upon data deletion."
- All tables and partitions expire after 60 days.

**Author's decisions after that review:**
1. Switch to a billed dev project with the guards, **including the
   billing kill switch** ("let's for sure do this").
2. Create a bot GitHub account, and keep the Owner `gcloud` login off the
   machine.
3. Approve the contract correction.
4. Defer the promotion method.

**Draft 2** ("with isolated agent identities and a capped dev project").
The re-review found four more problems, all fixed:

| Finding | Fix |
|---|---|
| Fine-grained PATs can't act on a personal repo the bot only collaborates on | Classic token with `repo` + `workflow`, still limited by the bot's Write role |
| `protect-main` required a PR but no approval, so a Write bot could merge to `main` | `main` requires 1 approval and code-owner review. Admin bypass is set to "for pull requests only." |
| `gh auth logout` leaves Windows Credential Manager able to push as the author | Setup clears it (`cmdkey /delete:git:https://github.com`) and runs `gh auth setup-git` |
| The kill switch can delete resources, not just stop them | Stated plainly. It's acceptable because all project data is re-derivable from GH Archive. |

**Smaller fixes:**
- `build/agentic` gets protected from day one.
- The CODEOWNERS list now covers every file that defines a check
  (`.claude/**`, tool configs, `terraform/**`, the access matrix).
- The agent service account gets explicit `dataEditor` + `jobUser`.
- The dev bucket gets a 7-day lifecycle rule.
- The Pub/Sub topic is created before the budget.

**Final spending guards (DECISIONS §1):**

| Guard | Dev | Prod | Hard? |
|---|---|---|---|
| Billing kill switch (budget → Pub/Sub → function unlinks billing) | $2/mo | $5/mo | Hard, with a lag |
| BigQuery query quota | 10 GB/day | 10 GB/day, plus a per-user cap on the dashboard identity | Hard (queries only) |
| 7-day table expiry + bucket lifecycle | yes | — | Default, not hard: the builder could skip it |
| Budget email alerts | $1, $2 | $1, $5 | Soft |

## 8. A8 Access Matrix and A9 Runbook

### 8.1 `docs/access_matrix.md` (PR #13)

**Structure:**
1. principles;
2. principals, with fully qualified member strings, the repository pinned
   by numeric ID `1406578436`, and the WIF principal sets;
3. what dev hosts;
4. **the canonical bindings table:** one row per grant, with Member /
   Scope / Role / Condition / Why columns, built for a B11 diff script;
5. a resource view;
6. credentials outside IAM;
7. change rules.

**Key design points from two review rounds:**
- **The Terraform apply identity** needs `iam.securityAdmin`, not
  `projectIamAdmin`, to set IAM on individual resources. The doc states
  plainly that `editor` + `securityAdmin` is effectively Owner, guarded
  only outside IAM: by the `prod-apply` GitHub Environment (author
  approval, `main` only).
- **Prod CI identities are gated by GitHub Environments**
  (`prod-plan` / `prod-apply` / `prod-deploy`), using a mapped
  `attribute.gh_env`.
  - `prod-plan` is limited to the protected branches (`main`,
    `build/agentic`). GitHub's approval screen doesn't show the workflow
    diff, so the branch limit is what guarantees the workflow requesting
    the token was itself reviewed.
  - `pull_request_target` is banned, both in the provider condition and by
    a B11 check.
- **A dedicated build identity** (`osp-build-prod`, `run.builder`)
  replaces the Compute Engine default service account, which gets
  `editor` by default. A B11 check asserts that `editor` stays absent.
- **The Slack notification channel is created by hand.** If Terraform
  managed it, a refresh would copy the webhook URL into state.
- **The dashboard key is the single key-file exception**, and it gets a
  per-user query quota.
- **The kill switch needs** `billing.projectManager` + `browser` on the
  project, `billing.viewer` on the billing account, and `run.invoker` on
  its own function.
- **Corrections to `architecture.md` §7,** queued under A10:
  - dbt never reads GCS;
  - the dashboard needs `bigquery.jobUser`;
  - the "reviewer" identity is dropped;
  - "no human access in prod" doesn't hold for a solo Owner.

### 8.2 `RUNBOOK.md` (PR #15)

**Part 1, the playbook:**
- alert routing;
- SEV1–SEV4 with concrete examples;
- six standard procedures (replay an hour; missing hour; dbt test
  failure; leaked secret; unexpected spend or the kill switch firing;
  dashboard unavailable);
- a blameless incident template.

**Part 2,** the incident log, is empty. Its first entry will be the D5
drill.

**Review-driven details:**
- **Missing hours:** first and second 404s log at `WARNING`; only the
  third attempt logs `ERROR` and pages.
- **Replay** overwrites the hour's partition (`WRITE_TRUNCATE` on the
  hour) instead of appending.
- **Re-linking billing:** budgets track month-to-date spend, so the kill
  switch must be defused (raise the budget or pause the function) before
  re-linking.
- **Webhook rotation** touches three places: the notification channel,
  the GitHub secret, and the Secret Manager record.
- **History scrub on a public repo** needs the admin bypass and a GitHub
  Support purge.
- **Kill-switch recovery** lists what must be restored by hand, and notes
  that `raw_ingest_audit` history is lost for good.

## 9. Independent Review Results

| PR | Review rounds | Blockers | Other findings | Verdict after fixes |
|---|---|---|---|---|
| #12 ADR 0002 | 2 | 1 + 2 (credentials; PAT type; `main` approval) | 6 + 6 | Merged |
| #13 Access matrix | 2 | 2 (apply SA can't set resource IAM; plan SA reachable from agent branches) | 11 + 9 | Approve with fixes, applied |
| #14 Contract URL fix | 0 | — | — | Measured directly; author-approved |
| #15 Runbook | 1 | 2 (kill switch re-fires on re-link; first 404s would page) | 9 | Merged after fixes |

**Process note:** every reviewer got only the diff, the spec, and
pointers to related docs. None was given my reasoning. All of the
blockers were real, and three were things I had stated as fact.

## 10. Decisions and Rejections

| Considered | Outcome | Why |
|---|---|---|
| BigQuery no-billing sandbox for dev | **Rejected after adoption** | No DML (dbt incremental can't run), 10 GiB lifetime non-refundable storage, 60-day expiry (Google docs) |
| Fully offline dev (DuckDB plus fixtures) | Rejected | BigQuery-specific bugs would first appear at cutover, on the author's limited time |
| One billed project with `_dev`/`_prod` datasets | Rejected | Agent's dev access would share a blast radius with prod |
| Agent uses the author's credentials, restricted by deny-rules | Rejected | Deny-rules are text matching; the credentials still reach billing, prod and repo settings |
| Separate Windows user for agent work | Deferred | Strongest isolation, but unnecessary once the author's logins are simply absent |
| Fine-grained PAT for the bot | Rejected | Not supported for a collaborator on a personal-account repo |
| Author reviews every agent PR | Rejected | ~40 PRs. Replaced by code-owner review of check-defining files plus milestone review. |
| Multi-agent parallel workflow | Rejected | Higher cost, more merge conflicts, harder to follow |
| Verifier #1 (two independent implementations, diffed) | Not selected | Correlated errors; agents "fixing" disagreements by copying |
| Merge commits for milestone PRs | Deferred by author | Tracked in OPEN_LOOPS before the first promotion |
| Option B for language contributors ("opened a PR or an issue") | Not chosen | Counts bug reporters and misses merging maintainers; option A matches the original code-contribution intent |

## 11. Work in Progress: A11 Cost Model Estimates

Branch `docs/a11-cost-model` exists locally with no commits yet.
Preliminary math (low = Nov 2026 sample, high = Oct 2026 upper range):

| Quantity | Low | High | Free tier |
|---|---|---|---|
| GCS Parquet, per month | 1.7 GB | 10.0 GB | 5 GB-month |
| GCS, 14-day retention | 0.8 GB | 4.7 GB | |
| BigQuery raw (logical), per month | 7.0 GB | 25.3 GB | 10 GiB |
| BigQuery raw, 14-day retention | 3.3 GB | 11.8 GB | |
| `fct_events`, 100 days | 0.54 GB | 1.38 GB | |
| Query scan per day (hourly staging + trending, daily other marts, 10 MB per-table minimum) | 8.0 GB | 13.4 GB | quota 10 GB/day |
| Query scan per month | 239 GB | 401 GB | 1 TiB |

**Implications for A11:**
- **Retention:** "keep forever" can't stay free. Proposed: 14-day
  retention on GCS and raw partitions, since both are re-derivable from GH
  Archive, while `fct_events` keeps more than 90 days. This changes the
  contract, so it needs the author's approval.
- **Query quota:** at October volumes, hourly builds could hit the
  10 GB/day quota. BigQuery's 10 MB minimum per table referenced matters.
  Likely answer: build staging and fact hourly, and marts daily.

Still to verify for A11:
- whether the quota counts processed or billed bytes;
- whether free tiers are per billing account (and so shared by dev and
  prod);
- Artifact Registry's 0.5 GB free storage against image sizes (needs a
  cleanup policy);
- Cloud Monitoring alerting pricing.

## 12. Open Items at Session End

**Waiting on the author** (in order; see `docs/author_setup.md`):
1. §1.1 branch rules: `main` requires approval, and `build/agentic` gets
   protected.
2. `QUESTIONS.md` Q1: commit attribution under a bot account
   (recommended: (a), commits authored by Robert and only pushed by the
   bot).
3. §1.2–1.3: bot Google and GitHub accounts, before milestone 2.
4. Part 2, the dev project: before milestone 2's BigQuery work.

**Milestone 1 remaining:**
- A11 cost model (in progress);
- A12 security posture, which must also reconcile DECISIONS §5 with the
  dashboard key exception;
- A13 ways of working (author approves);
- A10 roadmap (author approves; folds in the inputs list and the
  verifier plan);
- contract additions: failure-mode IDs, a `raw_ingest_audit` entry,
  reconciliation invariants, metamorphic relations (author approves).

**Open loops:**
- the promotion method (OPEN_LOOPS);
- the README ↔ contract reconcile (OPEN_LOOPS);
- `architecture.md` drift (A10 inputs).

## 13. ELI5 Topics This Session

None. No ELI5 explanations were requested, so there's no quiz for this
session.

## 14. Files Changed

### Merged to `main` (PR #11)
| File | Change |
|---|---|
| `docs/data_contract.md` | Created (A7). §5.4 contributor definition fixed; §5.1 `merged` re-verified |
| `FOUNDATION_BACKLOG.md` | A7 checked; A10 "Inputs to fold in" list |
| `OPEN_LOOPS.md` | README ↔ contract wording reconcile |

### Merged to `build/agentic` (PRs #12–#15)
| File | Change |
|---|---|
| `docs/adr/0002-agentic-build-out-and-isolated-dev.md` | Created: the operating model |
| `docs/author_setup.md` | Created: accounts and grants the author creates, in order, with commands |
| `docs/access_matrix.md` | Created (A8) |
| `RUNBOOK.md` | Created (A9) |
| `QUESTIONS.md` | Created: the agent → author question queue; Q1 open |
| `DECISIONS.md` | §1 hard vs. soft spend caps and the kill switch; §3 two projects; §4 project IDs |
| `CLAUDE.md` | Current phase (agentic build-out, agent hard limits); `build/agentic` workflow; QUESTIONS.md in the required reading |
| `FOUNDATION_BACKLOG.md` | Header note; Phase B heading restored; B11, C9, C10 added; C1/C2 marked author-only; A8, A9 checked; A10 inputs extended with architecture drift |
| `OPEN_LOOPS.md` | Milestone-promotion method |
| `docs/data_contract.md` | §2, §3.1–§3.3 unpadded URL, 72/72 availability, missing-hour alerting |

### Git refs
| Ref | Purpose |
|---|---|
| tag `baseline-pre-agentic` → `c24242e` | Revert point before any agent work |
| branch `build/agentic` | Integration branch for all agent PRs |

### Outside the repo
| File | Purpose |
|---|---|
| `~/.claude/projects/…/memory/agentic-buildout-plan.md` | Claude memory: the operating model and the author's priorities |
