# ADR 0002 — Agentic build-out with isolated agent identities and a capped dev project

> **Status:** Accepted
> **Date:** 2026-11-11
> **Authors:** Robert Harmon

## Context

By November 2026 the foundation phase was half done (A1–A7, A14, B7, B10)
and the author had much less time for the project than at the start. The
remaining work is largely mechanical given the existing docs (data
contract, architecture, conventions, decisions). That makes it a good fit
for AI coding agents, as long as four things hold:

1. **No surprise cloud costs.** DECISIONS §1 relied on billing alerts at
   $1 and $5. Those alerts **only send email. They don't stop spending.**
2. **Security.** An agent must not be able to reach billing, IAM, prod,
   or the repo's protection rules, **even by accident or through a
   workaround.** A rule that only says "don't" isn't enough.
3. **The author creates every account.**
4. **Agents can't quietly weaken their own checks.** Agents are good at
   satisfying a check and bad at noticing when the check itself is wrong.

**Two findings shaped this decision:**

- **Agents were running with the author's credentials.** At the time, the
  agent worked in the author's own terminal: the GitHub CLI was logged in
  as the repo owner (admin), and any `gcloud` login there would have been
  the project Owner, with billing rights. Service-account impersonation
  doesn't fix that, because the powerful login underneath is still on
  disk. Command deny-lists match command text and are easy to get around.
  Isolation has to come from *which credentials exist on the machine*,
  not from rules about how they're used.
- **BigQuery's no-billing sandbox can't run this project.** It was the
  first choice for dev because it can't be charged. Google's sandbox
  documentation rules it out:
  - It doesn't support DML (`INSERT` / `UPDATE` / `DELETE` / `MERGE`), so
    dbt incremental models can't run.
  - Storage is a 10 GiB *lifetime* limit that deleting data doesn't refund.
  - All tables and partitions expire after 60 days.

## Decision

### 1. Two GCP projects, both billed, both hard-capped

| Project | Purpose | Who has credentials |
|---|---|---|
| `oss-pulse-dev-<yyyy>` | `dev`: where agents build and test | The agent's own Google identity (§2), and the author |
| `oss-pulse-<yyyy>` | `prod`: the running pipeline | The author only; first brought up at cutover |

Spending guards, applied to **both** projects:

| Guard | What it does | Hard or soft |
|---|---|---|
| **Billing kill switch** (Google's documented "disable billing with notifications" pattern) | A budget publishes to Pub/Sub. A small Cloud Run function **unlinks billing** from the project when spend crosses the budget. Dev threshold: $2/month. Prod threshold: $5/month. | Hard, with a lag. Budget notifications arrive with some delay, so a small overshoot is possible. Unlinking shuts down every service in the project until billing is re-linked by hand. |
| **BigQuery custom query quota** | Rejects queries past a daily scan limit. Dev: 10 GB/day. Prod: 10 GB/day, plus a per-user quota on the dashboard identity so a leaked dashboard key can't starve dbt. | Hard |
| **Dev default table expiration** | Every dev dataset auto-deletes tables 7 days after creation, so dev storage can't pile up. Test fixtures are reloaded on demand. | Hard (bounds storage) |
| **Agent identity scope** | The agent's identity can only use BigQuery and the dev bucket. It can't create resources in any other service (§2). | Hard (IAM) |
| **Budget email alerts** at $1 and $5 | Early warning. | Soft. Email only. |

The kill switch's function needs permission to unlink billing. Google's
sample grants it `roles/billing.admin` on the billing account, which is
far broader than needed. The setup tries the narrowest grant that works
(project-level billing management), and records what was actually
required in the access matrix.

Dataset names keep their `_dev` / `_prod` suffix even though the project
already separates environments. That way a query pointed at the wrong
project fails loudly ("dataset not found") instead of silently reading the
other environment.

### 2. Agents get their own, weaker identities

| Where | Agent identity | Can | Can't |
|---|---|---|---|
| GitHub | A **bot GitHub account** created by the author, added to the repo as a collaborator with **write** (not admin) | Push branches, open PRs, merge PRs into `build/agentic` when the branch rules allow | Change branch rules, rulesets, secrets or settings. Bypass required checks or required reviews. Merge to `main`. |
| GCP | A **bot Google account** created by the author (the same identity's email can back the GitHub bot). Its only grant is permission to mint short-lived tokens for `osp-builder-dev`. | Act as `osp-builder-dev`: BigQuery in the dev project, and objects in the dev bucket | Anything in prod. Billing. IAM. Creating projects. |

- **The author's Owner login stays off the agent's machine.** No `gcloud`
  login as the author exists there during the build. The author uses the
  Cloud Console or Cloud Shell for owner tasks, and logs in locally only for
  the cutover session.
- **No service-account key files** for the agent. The bot Google account's
  login can only mint tokens for one dev-only service account.
- **Claude Code permission rules** in `.claude/settings.json` deny
  `gcloud billing`, `gcloud iam`, `gcloud projects`, and commands naming the
  prod project ID. These are defense in depth: easy to get around, and
  not relied on.

### 3. Branch rules make the verifiers binding

- **A ruleset on `build/agentic`** requires PRs, requires every CI check to
  pass, and blocks force-pushes. The bot has no bypass.
- **CODEOWNERS plus required code-owner review** for:
  - `.github/**`,
  - `tests/fixtures/**`, `tests/expected/**`,
  - `docs/data_contract.md`,
  - the verifier scripts.

  A PR touching these needs the author's approval. So an agent can't weaken
  a check in the same PR that would otherwise fail it.
- **Workflows triggered by PRs never get prod credentials.**
  - Prod-touching jobs (`terraform plan` / `apply` against prod, deploys)
    run only from a GitHub Environment that requires the author's approval.
  - Workload Identity Federation conditions pin the repository by its
    immutable numeric ID.
  - `pull_request_target` is banned.

### 4. Work flows through an integration branch

- `main` was tagged `baseline-pre-agentic` before any agent work began.
- Agents branch from `build/agentic` and squash-merge into it.
- The author decides when and how a milestone is promoted to `main`.
  - Squash-merging a long-lived branch into `main` more than once makes
    git re-show already-merged changes.
  - The promotion method (merge commit, or resetting `build/agentic` to
    `main` after each squash) is decided before the first promotion, and
    tracked in `OPEN_LOOPS.md`.
- Abandoning the effort means deleting `build/agentic` (locally and on
  GitHub). `main` and the baseline tag are untouched until a milestone is
  promoted.

### 5. Correctness comes from test-first development plus verifiers

Built in milestone 2 and specified in the content-phase roadmap:
- **Test-first:** tests are written first, by an agent that sees only the
  spec and never the implementation.
- **CI proves the tests start red:** the new tests must fail before the
  code exists.
- **Tests are frozen after that:** later commits in the PR can't touch
  them.
- **Seven verifier types:**
  - metamorphic tests,
  - reconciliation counts,
  - BigQuery validity checks,
  - executable docs,
  - spec reconstruction,
  - red-team rounds,
  - failure-mode coverage.

### 6. Agents build; the author cuts over

- Agents write and test against the dev project.
- At the end, agents produce `docs/cutover_runbook.md` and a smoke-test
  script. The author brings up prod in stages (Terraform → one manual
  ingest → dbt → schedule → alerts), with an agent reading output and
  fixing failures.
- This first bring-up is manual. After that, prod changes follow the normal
  PR-and-merge promotion in DECISIONS §3.

## Alternatives considered

- **No-billing BigQuery sandbox for dev.** Can't be charged at all. This
  was the first choice. Rejected because it has no DML (dbt incremental
  models can't run), its 10 GiB lifetime storage isn't refunded on
  deletion, and everything expires at 60 days. The pipeline's riskiest
  logic would go untested until cutover.
- **One billed project with `_dev` / `_prod` datasets** (the original
  DECISIONS §3). Simplest. Rejected because an agent with dev access would
  share a project, and therefore a blast radius, with prod data and prod
  services.
- **Fully offline development** (DuckDB stand-in plus recorded fixtures).
  Zero cost. Rejected because BigQuery-specific SQL and load behavior would
  first meet real BigQuery at cutover.
- **Agent uses the author's credentials, restricted by permission rules.**
  No extra accounts. Rejected because the restriction is text matching on
  commands. The credentials would still reach billing, prod and the repo
  settings.
- **A separate Windows user for agent work.** The strongest isolation on
  the machine. Rejected for now as more setup than needed once the
  author's powerful logins are simply absent. It's the next step if that
  ever stops holding.
- **Human review of every agent PR.** Caps throughput at the author's
  review time across roughly 40 PRs. Replaced by review of the files that
  define the checks, plus milestone review.

## Consequences

**Positive:**
- Spend is bounded by mechanisms that act on their own: the kill switch,
  quotas and expiration. It doesn't depend on someone reading email.
- The agent's credentials can't reach billing, IAM, prod or repo settings,
  because those credentials don't exist on its machine.
- Dev runs real BigQuery with DML and a real bucket, so incremental models
  and the GCS step are tested before cutover.
- Two capped projects plus bot identities make a clear isolation story.
  It's how larger teams separate environments and machine users.

**Negative / cost:**
- The author creates more accounts up front: a bot Google account, a bot
  GitHub account, two projects, and the kill switch.
- The kill switch is blunt. If it fires on prod, the whole pipeline stops
  until the author re-links billing. For a $0-target portfolio project,
  that's the intended trade.
- Required code-owner review on check-defining files means some agent PRs
  wait on the author. These should be rare after milestone 2.
- Cloud Run, Scheduler, Secret Manager and alerting still first run as a
  whole at cutover, unless milestone work exercises them in dev.

## Review date

Revisit at cutover, or earlier if:
- The kill switch fires.
- An agent PR is found to have weakened a check despite these rules.
- The author's review queue becomes the bottleneck.

## References

- [`DECISIONS.md`](../../DECISIONS.md) §1 (budget), §3 (environments),
  §4 (naming): updated alongside this ADR.
- [ADR 0001](0001-tech-stack.md): the stack this ADR operates.
- [`docs/author_setup.md`](../author_setup.md): the account setup this ADR
  requires, in order.
- Google Cloud: [BigQuery sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox)
  limits; [disable billing with notifications](https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications)
  (the kill-switch pattern and its caveats).
