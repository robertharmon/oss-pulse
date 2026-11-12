# ADR 0002 — Agentic build-out against a no-billing sandbox dev project

> **Status:** Accepted
> **Date:** 2026-11-11
> **Authors:** Robert Harmon

## Context

By November 2026 the foundation phase was half done (A1–A7, A14, B7, B10)
and the author had much less time to work on the project than at the start.
The rest of the work (foundation items plus the whole content phase) is
mostly mechanical given the docs that already exist: the data contract,
architecture, conventions and decisions. That makes it a good fit for
AI coding agents, provided three things hold:

1. **No surprise cloud costs.** DECISIONS §1 relied on billing alerts at
   $1 and $5. Those alerts **only send email; they do not stop spending.**
   An agent iterating against a billed project could spend real money
   before anyone reads the email.
2. **Security.** An agent must never hold credentials that can touch
   billing, IAM, or production data.
3. **The author creates every account.** No agent creates projects,
   billing accounts, or identities.

A second constraint: agents are good at satisfying a check and bad at
noticing when the check itself is wrong. Correctness has to come from
verifiers the agent can't quietly weaken, not from the agent's own
judgment.

## Decision

**1. Two GCP projects instead of one.**

| Project | Billing | Purpose | Who touches it |
|---|---|---|---|
| `oss-pulse-dev-<yyyy>` | **None linked** (BigQuery sandbox mode) | `dev` environment: where agents build and test | Agents (through a narrow service account) and the author |
| `oss-pulse-<yyyy>` | Linked, with budget alerts and the 10 GB/day query quota | `prod` environment | The author only; created at cutover |

With no billing account linked, the dev project can't be charged at all.
When it hits a free-tier limit, the work stops instead of spending.
Dataset names keep their `_dev` / `_prod` suffix even though the project
already separates them. That way a query pointed at the wrong project
fails loudly ("dataset not found") instead of silently reading the other
environment.

**2. Agents build; the author cuts over.**

- Agents write and test all code against the dev project.
- Pipeline pieces the sandbox can't run (GCS, Cloud Run, Cloud Scheduler,
  Secret Manager, alerting) are tested locally, offline, or with Terraform
  mock providers.
- At the end, agents produce `docs/cutover_runbook.md` and a smoke-test
  script. The author creates the prod project, then runs the runbook in
  stages (Terraform → one manual ingest → dbt → schedule → alerts) with an
  agent reading output and fixing failures.

**3. Agent credentials are narrow and short-lived.**

- One service account in the dev project, with BigQuery roles only.
- Agents borrow it through the author's login (`gcloud` service-account
  impersonation). No key files are ever created.
- Claude Code permission rules deny `gcloud billing`, `gcloud iam`,
  `gcloud projects`, and any command naming the prod project ID.

**4. Work flows through an integration branch.**

- `main` was tagged `baseline-pre-agentic` before any agent work began.
- Agents branch from and squash-merge into `build/agentic`. The author
  promotes each finished milestone to `main` through a reviewed PR.
- Reverting the whole effort means deleting `build/agentic`.

**5. Correctness comes from test-first development plus verifiers.**

- Wherever code has executable behavior, tests are written first, by an
  agent that sees only the spec and never the implementation.
- CI proves the new tests fail before the code exists, and blocks any
  later commit in the PR from editing them.
- Seven verifier types (metamorphic tests, reconciliation counts, BigQuery
  validity checks, executable docs, spec reconstruction, red-team rounds,
  failure-mode coverage) are specified in the content-phase roadmap
  (`docs/roadmap.md`).

## Alternatives considered

- **One billed project with `_dev` / `_prod` datasets** (the original
  DECISIONS §3). Simplest, and matches how many small teams work.
  Rejected because nothing hard-caps spend: the query quota caps queries,
  but storage and every non-BigQuery service stay uncapped, and an agent
  iterating unattended is exactly the case where an uncapped mistake
  happens.
- **Fully offline development** (DuckDB stand-in plus recorded fixtures).
  Zero cost and zero cloud risk. Rejected because BigQuery-specific SQL,
  JSON functions and load-job behavior would first meet real BigQuery at
  cutover. That would push most of the debugging onto the author's limited
  time, which is the opposite of the goal.
- **A billed dev project with BigQuery-only roles and the query quota.**
  Exposure would be a few cents of storage a month. Kept as the
  **fallback** if the sandbox turns out to block something essential. The
  open question is whether sandbox mode allows the `MERGE` statements dbt's
  incremental models use; the milestone-2 spike settles it.
- **Human review of every agent PR.** Safest, but caps throughput at the
  author's review time across roughly 40 PRs. Rejected in favor of
  milestone-level review plus mechanical verifiers.

## Consequences

**Positive:**
- Dev spend is impossible, not just unlikely.
- Agents never hold a credential that can reach billing, IAM, or prod.
- The two-project split is a cost-control and isolation story an
  interviewer can follow, and it's how larger teams separate environments.
- The baseline tag plus integration branch make the entire agentic effort
  one `git branch -D` away from undone.

**Negative / cost:**
- The pipeline's cloud plumbing (GCS, Cloud Run, Scheduler, secrets,
  alerts, CI authentication to prod) is first exercised for real at
  cutover. First-deploy failures, mostly permission errors, concentrate in
  that one session. Staged cutover keeps each failure small.
- Sandbox limits still to be confirmed: storage cap, default 60-day table
  expiry, and possibly DML restrictions. If DML is blocked, the fallback
  above applies.
- Two projects means two sets of IAM and two Terraform variable sets.
- Verifier tooling is real up-front work (milestone 2) before any pipeline
  code lands.

**Neutral but worth noting:**
- `main` moves in milestone-sized jumps rather than PR-sized ones. Each
  agent PR's red → green history stays visible on GitHub under
  `build/agentic`.

## Review date

Revisit at cutover, or earlier if:

- The milestone-2 spike shows the sandbox can't run dbt incremental
  models. In that case, decide on the billed-dev fallback.
- Agent-produced PRs repeatedly need rework after milestone review. That
  would mean the verifiers aren't catching what they should.

## References

- [`DECISIONS.md`](../../DECISIONS.md) §1 (budget), §3 (environments),
  §5 (secrets): updated alongside this ADR.
- [ADR 0001](0001-tech-stack.md): the stack this ADR operates.
- [`FOUNDATION_BACKLOG.md`](../../FOUNDATION_BACKLOG.md) A10: the roadmap
  that sequences the agentic milestones.
