# Foundation Backlog

> The ordered list of work that must happen **before** oss-pulse starts
> ingesting data. Each item has an owner (currently all solo), a clear "done"
> criterion, and a status marker. Work the list top-to-bottom; mark items
> complete as they land.
>
> **This file is the canonical source of truth for where the foundation
> phase stands.** Every session starts by reading it and ends by updating it.
>
> **Since 2026-11-11 the build-out is agentic**
> ([ADR 0002](docs/adr/0002-agentic-build-out-and-isolated-dev.md)):
> - Dev and prod are separate, capped GCP projects.
> - Pipeline building proceeds against dev once Phases A and B are done.
>   It doesn't wait for the rest of Phases C and D.
> - Phase C items marked *(author)* need the author's accounts and are done
>   by the author. See [`docs/author_setup.md`](docs/author_setup.md).

Status markers:
- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[-]` deliberately skipped (with reason)

---

## Phase A — Foundation documents

Documents that make implicit assumptions explicit. Written before any code
or cloud resources so every subsequent choice has something to check against.

- [x] **A1. README.md one-pager** — the "what and why" the whole repo serves.
  Done when: a stranger reading only the README understands what oss-pulse
  is, what questions it answers, and what's in scope.

- [x] **A2. DECISIONS.md v1** — operating decisions (GCP account, region,
  environments, naming, secrets, error handling, resource management, testing,
  branching, scope boundaries). Already drafted; needs to land as a file.
  Done when: committed to the repo with the $0 budget edit applied.

- [x] **A3. FOUNDATION_BACKLOG.md** — this file. Done when: committed and
  reviewed; subsequent sessions open by reading it.

- [x] **A4. ADR 0001 — tech stack & rationale** — why BigQuery over
  Snowflake/Databricks, why dbt, why Cloud Scheduler + Cloud Run over
  Airflow/Kestra, why Terraform. Michael Nygard ADR format
  (`Context / Decision / Consequences`). Done when: committed under
  `docs/adr/0001-tech-stack.md`.

- [x] **A5. Architecture doc + diagram** — `docs/architecture.md`. System
  diagram, component responsibilities, data flow narrative, failure
  boundaries, security boundaries. ASCII diagram is fine; hand-drawn PNG is
  fine. Done when: a reader can trace one record from GH Archive to the
  Streamlit chart without reading any other doc.

- [x] **A6. CONVENTIONS.md** — naming (adapted from color-analytics'
  conventions), SQL style, Python style, branch names, commit format, PR
  titles, when comments are required. Done when: committed; subsequent code
  review decisions reference it.

- [x] **A7. Data contract** — `docs/data_contract.md`. Upstream sources
  (GH Archive) with known SLAs and failure modes, tables we produce (grain,
  freshness, columns), downstream consumers (the Streamlit dashboard,
  initially — ourselves). Versioning rule: how we add/deprecate columns.
  Done when: every mart table has a contract entry before it's built.

- [x] **A8. Access matrix** — `docs/access_matrix.md`. Who/what can read and
  write each dataset, bucket, secret, and Terraform state. Even solo, this
  defines the service-account roles. Done when: Terraform IAM later
  implements exactly this table.

- [ ] **A9. On-call & incident runbook** — `RUNBOOK.md`. Alert routing
  (Slack webhook), incident template (timeline, impact, root cause,
  follow-ups), severity levels with concrete examples. Starts mostly empty;
  grows with every real incident. Done when: committed and ready to accept
  entries.

- [ ] **A10. 90-day roadmap** — `docs/roadmap.md`. Milestones for months 1,
  2, 3 with measurable "done" criteria for each. Done when: committed and
  reviewed; serves as the content-phase sequencer after foundation ends.

  **Inputs to fold in** (gaps found 2026-11-11 that no backlog item covers):
  - **Agentic build-out plan** — TDD + verifier workflow, `build/agentic`
    integration branch, no-billing sandbox dev project, staged manual
    cutover. This is the content-phase operating model; record it via ADR
    + DECISIONS §1/§3 updates.
  - **Ingest ADR** — scheduler offset (`5 * * * *` has ~0 margin; see
    `docs/data_contract.md` §8) and initial backfill window.
  - **`raw_ingest_audit` table + miss-rate alert job** (contract §3.3) —
    not yet in `docs/architecture.md`.
  - **`primary_language` source** (contract §5.7) — GitHub API + token in
    Secret Manager, or NULL. Two marts depend on it.
  - **Great Expectations on raw** — promised by ADR 0001 and README; no
    item yet.
  - **Cloud Run services, Scheduler job, alert policy in Terraform** — C5
    covers buckets/datasets/SAs/secrets only.
  - **Deploy workflow** — nothing builds/deploys services on merge (C6 is
    Terraform-only).
  - **Production alert path** — C8 proves CI → Slack, not Cloud Logging →
    Slack.
  - **Storage retention vs. free tiers** — "keep forever" in
    `architecture.md` §3 will exceed GCS (5 GB) and BigQuery (10 GB) free
    storage within months; belongs in A11.
  - **`architecture.md` drift** — still says Docker/Artifact Registry
    (contradicts DECISIONS §10), 0.5–1 GB files (measured 2–14 MB),
    PushEvent in trending, "Cloud Run auto-retries 3×" (retries live on
    the Scheduler job), and "data contract not yet written". Also from
    the access matrix: §7 has dbt reading the bucket (it doesn't), a
    "reviewer" SA (dropped), "no human access in prod" (the solo author
    is Owner), and line ~135 puts the Streamlit key in Secret Manager
    (it lives in Streamlit secrets). Line ~97 calls dbt a Cloud Run "job";
    the matrix assumes a service. Pick one in the ingest ADR.
  - **License + making the repo public** (README "License" section).
  - **v1 "done" definition** — when is the project finished?
  - **`ROADMAP.md` duplication** — the "When this backlog is empty" step 2
    copies `docs/roadmap.md` to a second file; keep one.

- [ ] **A11. Budget & cost model** — `docs/cost_model.md`. Expected monthly
  spend by service (should be $0), the BigQuery scan quota, cost-alerting
  mechanism, attribution via labels. Done when: committed, and the quotas it
  references match what Terraform will apply in Phase C.

- [ ] **A12. Security posture doc** — `docs/security.md`. Data classes
  handled (all public here — label each source), secrets rotation policy,
  audit logging posture, incident disclosure path. Done when: committed, and
  informs the Secret Manager + IAM wiring in Phase C.

- [ ] **A13. Solo-project ways-of-working** — `docs/ways_of_working.md`.
  The solo analog of a team's engineering agreements: session cadence,
  self-review discipline, when to interrupt a session vs. ship-and-move-on,
  what "done" means for a solo PR. Done when: committed; subsequent sessions
  reference it when scope creeps.

- [x] **A14. CLAUDE.md — Claude Code project orientation** — `CLAUDE.md`
  at the repo root. Short file that orients a new Claude Code session on
  the project: pointer to `FOUNDATION_BACKLOG.md` as the task tracker,
  pointer to `DECISIONS.md` for locked choices, pointer to `OPEN_LOOPS.md`
  for ad-hoc chores, pointer to `docs/adr/` for rationale, workflow
  reflexes (branch names, commit style, no AI-attribution rule),
  current-phase reminder. Done when: committed at repo root. _Added
  retroactively 2026-10-06 to close the "how does a new session know
  what to do" gap; realized after A4 landed._

## Phase B — Repo scaffolding

The dressed-but-empty repo. Every tool and gate that will protect subsequent
code lands here, even when there's no code to protect yet. "Walking
skeleton": all guardrails on, no content.

- [ ] **B1. Folder skeleton** — top-level directories (`ingest/`, `dbt/`,
  `dashboard/`, `terraform/`, `tests/`, `docs/`, `.github/`) with one-line
  READMEs explaining what belongs in each. Done when: a stranger knows where
  any file type goes without asking.

- [ ] **B2. `.gitignore`** — Python, Terraform state, dbt artifacts, secrets,
  notebook checkpoints, OS cruft. Done when: committed; nothing in those
  categories can be accidentally staged.

- [ ] **B3. Python toolchain** — `pyproject.toml`, `uv` as package manager,
  `ruff` (lint + format), `mypy` strict, `pytest` + `pytest-cov`. Done when:
  `uv run ruff check .`, `uv run mypy .`, and `uv run pytest` all pass on
  a dummy module.

- [ ] **B4. SQL toolchain** — `sqlfluff` with the BigQuery dialect, config in
  `.sqlfluff`. Done when: `sqlfluff lint` runs cleanly against a trivial
  `.sql` file.

- [ ] **B5. Pre-commit hooks** — `.pre-commit-config.yaml` running ruff,
  mypy, sqlfluff, and `gitleaks` on changed files. Done when:
  `pre-commit install` wired, a staged test commit catches a planted bad
  file.

- [ ] **B6. CI workflow stubs** — `.github/workflows/ci.yml` with stub jobs
  for lint-python, typecheck, lint-sql, test-python, terraform-fmt,
  terraform-validate, and secret-scan. Each passes trivially on an empty
  repo. Done when: a dummy PR shows all seven jobs green.

- [x] **B7. Branch protection** — `main` protected: require PR, require
  passing CI, no self-approval dismissal, no force pushes, require signed
  commits (nice-to-have). Done when: trying to push directly to `main` is
  rejected. _Completed 2026-10-05 ahead of schedule, immediately after the
  initial push, via a GitHub ruleset named `protect-main` (Active). Rule
  set requires PR, blocks force pushes, restricts deletions. Status-check
  requirements will be added once CI jobs exist (B6)._

- [ ] **B8. PR template** — `.github/pull_request_template.md` with what
  changed, why, how tested, breaking changes, rollback plan. Done when: PRs
  auto-populate.

- [ ] **B9. CODEOWNERS** — even if just you, the right habit. Done when:
  committed.

- [x] **B10. ADR template** — `docs/adr/0000-template.md` for future ADRs.
  Done when: committed and referenced by ADR 0001.

- [ ] **B11. Verifier tooling and branch rules** — the machinery that makes
  agent work trustworthy (ADR 0002 §3, §5). Includes:
  - the red-proof check (new tests must fail against the base branch);
  - the tests-untouched-after-red check;
  - the failure-mode coverage script;
  - the executable-docs runner;
  - the `dbt build --empty` CI job;
  - the docs ↔ code diff scripts (contract ↔ `schema.yml`, access matrix ↔
    Terraform IAM);
  - subagent definitions in `.claude/agents/`;
  - the lock hook;
  - the `build/agentic` ruleset and CODEOWNERS.

  Done when: each verifier rejects a deliberately planted bad input in a
  drill PR.

## Phase C — Cloud bootstrap

The one unavoidable manual action (create a GCP project + a bootstrap
service account), then everything else is Terraform. By the end of this
phase, the cloud account mirrors what the operating docs promise.

- [ ] **C1. GCP projects created** *(author)* — dedicated Google account;
  dev project `oss-pulse-dev-<yyyy>` and prod project `oss-pulse-<yyyy>`
  per DECISIONS.md §1; billing linked; budget alerts at $1 and $5. Done
  when: both projects exist and billing alerts are live. Prod may wait
  until cutover.

- [ ] **C2. BigQuery scan quota** *(author)* — custom quota at 10 GB/day
  per project per DECISIONS.md §1. Done when: a deliberate 11 GB `SELECT`
  is rejected.

- [ ] **C3. Terraform remote state bucket** — GCS bucket for Terraform
  state, versioned, lifecycle-protected. The one bucket Terraform doesn't
  manage. Done when: `terraform init` points at it.

- [ ] **C4. Terraform repo structure** — `terraform/` with `main.tf`,
  `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`. Done when:
  `terraform fmt` and `terraform validate` pass in CI.

- [ ] **C5. Terraform-managed foundation** — GCS data bucket (empty),
  BigQuery datasets (`osp_raw_dev`, `osp_staging_dev`, `osp_analytics_dev`,
  and the `_prod` versions), service accounts per access matrix, Secret
  Manager entries (placeholder values). Done when: `terraform apply`
  succeeds end-to-end from a clean clone.

- [ ] **C6. Terraform CI** — `.github/workflows/terraform.yml` runs
  `terraform plan` on PRs and `terraform apply` on merge to main. Done when:
  a trivial Terraform change opens as a PR, shows the plan in the PR, and
  applies on merge.

- [ ] **C7. Secrets wired** — real values populated in Secret Manager
  (Slack webhook URL at minimum); GitHub Actions secrets configured to
  authenticate CI to GCP (preferring Workload Identity Federation over
  long-lived keys). Done when: a CI job can read a secret end-to-end.

- [ ] **C8. Alerting webhook end-to-end** — a dummy workflow failure posts
  to Slack. Done when: a planted failure in CI results in a Slack message
  within 1 minute.

- [ ] **C9. Billing kill switch** *(author deploys; agent writes the
  function)* — budget → Pub/Sub → Cloud Run function that unlinks billing,
  on each project (DECISIONS §1). Done when: a simulated over-budget
  notification unlinks billing on the dev project, and re-linking restores
  it.

- [ ] **C10. Agent identities** *(author)* — bot Google account, bot GitHub
  account with write access, and the dev-only `osp-builder-dev` service
  account with token-minting granted to the bot (ADR 0002 §2). Done when:
  the agent's machine has no author login (including in Windows Credential
  Manager), the bot can query dev BigQuery, gets 403 on billing, and a
  bot-opened PR into `main` can't be merged without the author's approval.
  Once prod exists, it also gets 403 on every prod resource.

## Phase D — Walking-skeleton smoke test

One PR that touches every surface the project will use for the next 4
months. Any surface misconfigured gets caught here, with nothing at stake.

- [ ] **D1. Hello-world Python module** — `ingest/hello.py` with a trivial
  function and a passing unit test. Done when: lint, typecheck, and test
  pass in CI.

- [ ] **D2. Hello-world dbt model** — a `SELECT 1 AS n` model in a sandbox
  dataset. Done when: `dbt build` runs in CI against the dev dataset.

- [ ] **D3. Hello-world Terraform change** — a label update on the data
  bucket, opened as a PR. Done when: the PR shows a `terraform plan` diff,
  passes CI, and applies on merge.

- [ ] **D4. Deliberate CI failure drill** — one PR that intentionally
  breaks a lint rule to confirm the gate rejects it. Done when: CI goes red
  on that PR, green after the fix.

- [ ] **D5. Deliberate incident drill** — a planted failure fires the
  Slack webhook; log the "incident" in RUNBOOK.md using the template. Done
  when: RUNBOOK.md has its first (synthetic) entry.

---

## When this backlog is empty

The foundation phase is complete. oss-pulse moves from "scaffolding only" to
"building content." At that point:

1. Archive this file to `docs/foundation_backlog_closed.md` for provenance.
2. Create `ROADMAP.md` from the content-phase plan in `docs/roadmap.md`.
3. Open the first content-phase PR: the real GH Archive ingest job.

---

## Change log

| Date | Change |
|---|---|
| 2026-10-05 | Initial draft created at repo bootstrap. |
| 2026-10-05 | B7 (branch protection) closed early via `protect-main` ruleset. |
| 2026-10-05 | A4 (ADR 0001 — tech stack) and B10 (ADR template) closed together. |
| 2026-10-06 | A14 added retroactively — project CLAUDE.md for session orientation. |
| 2026-10-05 | A5 (architecture doc + diagram) closed. |
| 2026-10-06 | A6 (CONVENTIONS.md) closed. |
| 2026-10-07 | A7 (data contract) closed. |
| 2026-11-11 | Agentic build-out adopted (ADR 0002): header note added, B11 (verifier tooling) added, C1/C2 marked author-only and C1 split into two projects, C9 (kill switch) and C10 (agent identities) added. |
| 2026-11-11 | A8 (access matrix) closed. |
