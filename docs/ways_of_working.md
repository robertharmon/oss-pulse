# oss-pulse — Ways of Working

> How the work actually gets done: who does what, what a session looks
> like, what "done" means for a PR, and when to stop and ask instead of
> pressing on. It's the solo-plus-agents version of a team's engineering
> agreements.
>
> The operating model it serves is
> [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md). Branch, commit
> and PR mechanics are in DECISIONS §9 and [`CONVENTIONS.md`](../CONVENTIONS.md).
> This doc doesn't repeat them.

---

## 1. Who does what

| Role | Who | Does | Doesn't |
|---|---|---|---|
| **Author** | Robert | Sets scope. Approves specs, expected test outputs, and changes to check-defining files. Answers `QUESTIONS.md`. Creates accounts. Reviews each milestone. Runs the prod cutover. Does the final merge into `main`. | Review every PR. Write most of the code. |
| **Builder** | The main Claude session | Picks the next item, writes code and docs, runs the per-PR loop (§3), merges into `build/agentic`, keeps the trackers current. | Create accounts, touch billing, run IAM changes, touch prod, or edit `.claude/settings.json` permissions (CLAUDE.md "Agent hard limits"). |
| **Test-writer** | Subagent | Writes failing tests from the spec and interfaces only. Never sees the implementation. | Fix code. |
| **Reviewer** | Subagent | Reads the diff plus the spec, hunts for bugs and for weakened, skipped or deleted checks. Gets none of the builder's reasoning. | Approve its own suggestions. |
| **Spec-reconstructor** | Subagent | Reads only the code, writes the contract entry it implies. A script diffs that against `docs/data_contract.md`. | See the contract first. |
| **Red team** | Subagent | At the end of each code milestone, writes realistic inputs meant to break the pipeline, as failing tests. | Change production code. |

**The author's time is the scarcest resource.** Everything below is
designed so the author's involvement is limited to decisions only the author can make:
scope, cost, security, accounts, ambiguous specs, and milestone review.

## 2. A working session

### 2.1 Start

1. Read the required list in `CLAUDE.md` (the `SessionStart` hook asks for
   this).
2. Check `QUESTIONS.md` for new answers, and act on them first.
3. Pick the next unchecked item in the tracker (`FOUNDATION_BACKLOG.md`,
   then `ROADMAP.md` once A10 lands). Pair it with a cheap
   `OPEN_LOOPS.md` item if one fits.

### 2.2 During

- **One item, one branch, one PR.** If the PR description needs "also",
  it's two PRs (CONVENTIONS §6).
- **Blocked on the author?** Write the question in `QUESTIONS.md` with a
  recommendation (§5), then move to the next unblocked item. Don't wait.
- **Found something off-plan?** Small and cheap: add it to
  `OPEN_LOOPS.md`. Bigger: raise it with the author before doing it
  (§6).
- **Keep the author posted** in a line or two when they're watching: what's
  done, what's next, anything waiting on the author.

### 2.3 End

A session ends at a clean point: every PR merged or explicitly parked, no
uncommitted work.
1. Update the tracker's checkboxes and change log.
2. Write the session doc (`documentation/SessionNN_…`) and update
   `DECISION_LOG.md`, if the session produced decisions, code, or
   findings worth keeping.
3. Tell the author the status (done / blocked / needs a decision), what
   needs the author, and what's next.

## 3. What "done" means for a PR

A PR is done when **every gate for its kind is green and the reviewer's
findings are fixed or answered in the PR.** Not when the code "works on my
machine."

### 3.1 Code with executable behavior (ingest, dbt models, Terraform, dashboard)

Test-first, in this order. Each step is a separate commit, so the history
shows it.
1. **Spec exists.** The contract entry, ADR or roadmap item says what to
   build, and the author has approved it. Expected outputs for
   hand-computed tests are approved at milestone start.
2. **Red.** The test-writer commits failing tests (`test(<scope>): …`).
   CI runs them against the base branch, and **they must fail.** A test
   that passes before the code exists proves nothing.
3. **Green.** The builder implements. **Commits after the red commit may
   not touch `tests/`.** CI enforces this. If the builder thinks a test is
   wrong, it says so in `QUESTIONS.md` and the test-writer re-derives the
   test from the spec. The builder never edits it.
4. **Gates:** lint, type check, SQL lint, secret scan, unit tests, dbt
   build on fixtures, `dbt build --empty` / dry-run, failure-mode
   coverage, docs-vs-code diffs. Each gate is added by backlog B11; until
   a gate exists, its PR says what was run by hand.
5. **Review.** The reviewer subagent. For ingest and dbt, also the
   spec-reconstructor.
6. **Merge.** Squash into `build/agentic`. Delete the branch.

### 3.2 Docs and decisions

1. Facts in the doc are measured or sourced, not remembered. Numbers say
   how they were measured; prices and limits link to the live page.
2. The reviewer subagent checks it against the docs it must agree with.
3. **Decisions the doc makes that belong to the author** (§5) are asked,
   not assumed. The doc says "proposed" until the author answers.
4. Every doc a decision touches is updated in the same PR, or in a
   follow-up PR in the same session. A decision recorded in one place and
   contradicted in another is a bug.

### 3.3 Config and scaffolding (folders, `.gitignore`, templates)

No test-first. Instead, a **planted-bad-input drill**: show the gate
rejecting something it should reject (a staged secret, a lint error, a
direct push).

## 4. Milestones

- **A milestone ends with:** all gates green on `build/agentic`; for code
  milestones, a red-team round that stops after 3 failed break attempts in
  a row; and a `m<N>-done` tag on the branch tip (ADR 0002 §4).
- **The author's review:** a GitHub compare link from the previous tag to
  the new one, a one-page walkthrough of what changed and why, and a short
  quiz on the new concepts (only if the author asked for ELI5 explanations during
  the milestone). The author's findings become PRs into `build/agentic`.
- **Nothing reaches `main`** until the author decides the project is done:
  then one PR, merged with "Rebase and merge".

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
| A real gap in the plan | Add it to the tracker, as a new item or as an input to an existing one, and tell the author |
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
| 2026-11-18 | Initial version (A13), proposed for the author's approval. Records the per-PR loop from the 2026-11-11 build-out plan in the repo. |
