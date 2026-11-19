# oss-pulse — Ways of Working

> How the work actually gets done: who does what, what a session looks
> like, what "done" means for a PR, and when to stop and ask instead of
> pressing on. It's the solo-plus-agents version of a team's engineering
> agreements.
>
> The operating model it serves is
> [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md); the plan it
> executes is [`roadmap.md`](roadmap.md). Branch, commit and PR mechanics
> are in DECISIONS §9 and [`CONVENTIONS.md`](../CONVENTIONS.md). This doc
> doesn't repeat them.

---

## 1. Who does what

| Role | Who | Does | Doesn't |
|---|---|---|---|
| **Author** | Robert | Sets scope. Approves specs, expected test outputs, and changes to check-defining files (CODEOWNERS). Answers `QUESTIONS.md`. Creates accounts and sets repo rules. Reviews each milestone. Merges `build/agentic` into `main` and runs the prod cutover. | Review every PR. Write most of the code. |
| **Builder** | The main Claude session | Picks the next item, writes code and docs, runs the per-PR loop (§3), merges into `build/agentic`, keeps the trackers current. | Create accounts, touch billing, run IAM changes, touch prod, or edit `.claude/settings.json` permissions (CLAUDE.md "Agent hard limits"). |
| **Test-writer** | Subagent | Writes failing tests from the spec and interfaces only. Never sees the implementation. | Fix code. |
| **Reviewer** | Subagent | Reads the diff plus the spec, hunts for bugs and for weakened, skipped or deleted checks. Gets none of the builder's reasoning. | Approve its own suggestions. |
| **Spec-reconstructor** | Subagent | Reads only the code, writes the contract entry it implies. A script diffs the structured fields (grain, columns, types, tests) against `docs/data_contract.md`; the reviewer judges any prose differences. | See the contract first. |
| **Red team** | Subagent | At the end of each code milestone, writes realistic inputs meant to break the pipeline, as failing tests. | Change production code. |

**The role boundaries are enforced where they can be.** A lock hook
(`scripts/lock_paths_hook.py`, ADR 0002 §2) denies the builder and other
agents writes to test paths, denies the reviewer all writes, and keeps the
spec-reconstructor out of `docs/`. It doesn't see shell commands; CI's
`commit-paths` and `red-proof` checks cover that gap.

**The author's time is the scarcest resource.** Everything below is
designed so the author's involvement is limited to decisions only the
author can make: scope, cost, security, accounts, ambiguous specs, check
changes, and milestone review.

## 2. A working session

### 2.1 Start

1. Read the required list in `CLAUDE.md` (the `SessionStart` hook asks for
   this).
2. Check `QUESTIONS.md` for new answers, and act on them first.
3. Pick the next open item. **Trackers:** `FOUNDATION_BACKLOG.md` for its
   own items until it's empty, and [`roadmap.md`](roadmap.md) for
   everything else. Both carry status markers. Pair it with a cheap
   `OPEN_LOOPS.md` item if one fits.

### 2.2 During

- **One item, one branch, one PR.** If the PR description needs "also",
  it's two PRs (CONVENTIONS §6).
- **Blocked on the author?** Write the question in `QUESTIONS.md` with a
  recommendation (§5), then move to the next unblocked item. Don't wait.
- **PRs waiting for the author's approval** (they touch CODEOWNERS paths)
  are batched: one message listing them, at most once a day. Meanwhile
  the builder works on items that don't need approval.
- **Found something off-plan?** Small and cheap: add it to
  `OPEN_LOOPS.md`. Bigger: raise it with the author before doing it (§6).
- **Keep the author posted** in a line or two when they're watching:
  what's done, what's next, anything waiting on them.

### 2.3 End

A session ends at a clean point: every PR merged or explicitly parked, no
uncommitted work.
1. Update the trackers' status markers and change logs.
2. Write the session doc (`documentation/SessionNN_…`) and update
   `DECISION_LOG.md`, if the session produced decisions, code, or
   findings worth keeping.
3. Tell the author the status (done / blocked / needs a decision), what
   needs them, and what's next.

## 3. What "done" means for a PR

A PR is done when **every gate for its kind is green, every check it
needs is a required status check, and the reviewer's findings are fixed
or answered in the PR.** Not when the code "works on my machine."

### 3.1 Code with executable behavior (ingest, dbt models, Terraform, dashboard)

Test-first. Each step is its own commit, so the PR's commits and CI runs
show the order. (The squash commit on `build/agentic` links back to the
PR.)

**Test paths** are, explicitly: `tests/**`, `dbt/tests/**`,
`dbt/models/**/_unit_tests.yml` (dbt unit tests live in their own files,
never mixed into a model's `schema.yml`), and `terraform/tests/**`.

1. **Spec exists.** The contract entry, ADR or roadmap item says what to
   build, and the author has approved it. Expected outputs for
   hand-computed tests are approved at milestone start.
2. **Stubs.** The builder commits the interfaces only: function
   signatures that raise `NotImplementedError`, dbt models that select
   zero rows with the contract's column types, empty Terraform modules
   with their variables. Code that imports and compiles, but does
   nothing.
3. **Red.** The test-writer commits the tests, touching **only** test
   paths. CI runs every new or changed test against the stubs commit, and
   **each one must fail on an assertion.** An import error, compile error
   or missing fixture doesn't count, because it proves nothing about
   behavior.
4. **Green.** The builder implements. **Commits that touch non-test paths
   may not touch test paths, and the reverse.** CI rejects a commit that
   mixes them.
5. **When a test is wrong.** The builder doesn't edit it. It asks in
   `QUESTIONS.md`; once the author answers, the test-writer commits a
   tests-only fix. CI re-proves the fixed test red against the same
   stubs commit.
   - **Limit, stated plainly:** every commit is authored as Robert and
     pushed by the same bot (DECISIONS §9), so CI can't tell the
     test-writer's commits from the builder's. That a test fix came from
     the test-writer, after an answered question, is checked by the
     reviewer subagent and linked in the PR description. It's a review
     check, not a mechanical one.
6. **Gates:** lint, type check, SQL lint and secret scan (backlog B3–B6);
   unit tests; dbt build on fixtures; `dbt build --empty` and dry-runs;
   failure-mode coverage; the docs-vs-code diffs (B11). Until a gate
   exists, the PR says what was run by hand instead.
7. **Review.** The reviewer subagent. For ingest and dbt, also the
   spec-reconstructor.
8. **Merge.** Squash into `build/agentic`. Delete the branch.

### 3.2 Docs and decisions

1. Facts in the doc are measured or sourced, not remembered. Numbers say
   how they were measured; prices and limits link to the live page.
2. The reviewer subagent checks it against the docs it must agree with.
3. **Decisions the doc makes that belong to the author** (§5) are asked,
   not assumed. The doc says "proposed" until the author answers.
4. Every doc a decision touches is updated in the same PR, or in a
   follow-up PR in the same session. A decision recorded in one place and
   contradicted in another is a bug.

### 3.3 Config and scaffolding (folders, `.gitignore`, templates, rulesets)

No test-first. Instead, a **planted-bad-input drill**: show the gate
rejecting something it should reject (a staged secret, a lint error, an
unpinned action), **and** show that the bot can't merge the drill PR
while the check is red. A check that goes red but isn't required binds
nothing.

## 4. Milestones

- **A milestone ends with:**
  - all gates green on `build/agentic`;
  - for code milestones, a red-team round. Each break attempt targets a
    distinct failure-mode ID or contract clause and is logged in the
    round's PR. The round ends after 3 logged attempts in a row fail to
    break anything;
  - a `m<N>-done` tag on the branch tip (ADR 0002 §4).
- **The author's review:** a GitHub compare link from the previous tag to
  the new one, a one-page walkthrough of what changed and why, and a short
  quiz on the new concepts (only if the author asked for ELI5
  explanations during the milestone). The author's findings become PRs
  into `build/agentic`.
- **`main` stays frozen until the build is code-complete and verified**
  (roadmap §1.2). Then the author merges it with "Rebase and merge" and
  runs the cutover from `main`.

### 4.1 After the merge into `main`

- `build/agentic` is retired. Every change is a PR into `main`, which needs
  the author's approval (`protect-main`).
- **Rollback is a revert PR**, never a reset or force-push (DECISIONS §9).
- The per-PR loop (§3) is unchanged.

## 5. When to ask the author

**Ask** (in `QUESTIONS.md`, or directly if the author is present):
- **Scope:** anything outside DECISIONS §11, or a new table, mart or
  service.
- **Cost:** anything that could cost money, or change the cost model's
  numbers by more than a rounding error.
- **Security:** any new credential, grant or exposure.
- **Accounts:** anything that needs one.
- **An ambiguous spec,** where two reasonable readings lead to different
  code.
- **Weakening a check.** Loosening a test, a threshold, a quota or a
  ruleset, even when it's "obviously" too strict.

**Don't ask** when the docs already answer it, when there's a convention
for it, or when it's reversible and inside the current item's scope. Pick
the obvious option and say so in the PR.

**How to ask:** one question, a recommendation, the cost of each option,
and what's blocked meanwhile. The answer should fit in one word.

## 6. Scope creep

A request or idea that doesn't fit the current item:

| It is… | Do |
|---|---|
| A one-line fix to something in this PR's files | Fix it in this PR and mention it |
| A small chore elsewhere | Add it to `OPEN_LOOPS.md` |
| A real gap in the plan | Add it to the roadmap or backlog, as a new item or as an input to an existing one, and tell the author |
| A change to the project's shape (new source, new mart, streaming, ML) | Stop. That's an ADR first (DECISIONS §11) |

**"While I'm in here…" is the warning sign.** Finish the item, then
decide.

## 7. Stop rules

Stop, don't push through, when:
- **A check fails and the fix is to weaken it.** Ask instead (§5).
- **The dev project's spend, quota or kill switch fires,** or a query
  would bill more than about 1 GB. Find out why before re-running.
- **A command would need credentials the agent shouldn't have** (prod,
  billing, IAM, the author's login). That's a design problem, not a
  permissions prompt to click through.
- **The same failure happens three times** with three different fixes.
  Step back and write down what's actually known.
- **The work stops matching the spec** and the spec looks wrong. Fix the
  spec first, with approval, then the code.

## 8. Review date

Review at each milestone review. Change it when a rule here was ignored
twice. Either the rule is wrong, or it needs a check that enforces it.

## 9. Change log

| Date | Change |
|---|---|
| 2026-11-18 | Initial version (A13), proposed for the author's approval. Records the per-PR loop from the 2026-11-11 build-out plan in the repo. Revised after independent review: stubs commit and assertion-only red proof; explicit test paths; no mixed commits; test fixes re-proven red, with the commit-identity limit stated; required checks for drills; red-team attempts logged per failure mode; post-merge rules; approval batching; trackers. |
| 2026-11-18 | Approved by the author. |
