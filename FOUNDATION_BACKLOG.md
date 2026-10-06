# Foundation Backlog

> The ordered list of work that must happen **before** oss-pulse starts
> ingesting data. Each item has an owner (currently all solo), a clear "done"
> criterion, and a status marker. Work the list top-to-bottom; mark items
> complete as they land.
>
> **This file is the canonical source of truth for where the foundation
> phase stands.** Every session starts by reading it and ends by updating it.

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

- [ ] **A4. ADR 0001 — tech stack & rationale** — why BigQuery over
  Snowflake/Databricks, why dbt, why Cloud Scheduler + Cloud Run over
  Airflow/Kestra, why Terraform. Michael Nygard ADR format
  (`Context / Decision / Consequences`). Done when: committed under
  `docs/adr/0001-tech-stack.md`.

- [ ] **A5. Architecture doc + diagram** — `docs/architecture.md`. System
  diagram, component responsibilities, data flow narrative, failure
  boundaries, security boundaries. ASCII diagram is fine; hand-drawn PNG is
  fine. Done when: a reader can trace one record from GH Archive to the
  Streamlit chart without reading any other doc.

- [ ] **A6. CONVENTIONS.md** — naming (adapted from color-analytics'
  conventions), SQL style, Python style, branch names, commit format, PR
  titles, when comments are required. Done when: committed; subsequent code
  review decisions reference it.

- [ ] **A7. Data contract** — `docs/data_contract.md`. Upstream sources
  (GH Archive) with known SLAs and failure modes, tables we produce (grain,
  freshness, columns), downstream consumers (the Streamlit dashboard,
  initially — ourselves). Versioning rule: how we add/deprecate columns.
  Done when: every mart table has a contract entry before it's built.

- [ ] **A8. Access matrix** — `docs/access_matrix.md`. Who/what can read and
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

- [ ] **B10. ADR template** — `docs/adr/0000-template.md` for future ADRs.
  Done when: committed and referenced by ADR 0001.

## Phase C — Cloud bootstrap

The one unavoidable manual action (create a GCP project + a bootstrap
service account), then everything else is Terraform. By the end of this
phase, the cloud account mirrors what the operating docs promise.

- [ ] **C1. GCP project created** — dedicated Google account, project ID
  per DECISIONS.md §1, billing linked, alerts set at $1 and $5. Done when:
  project exists, billing alerts are live.

- [ ] **C2. BigQuery scan quota** — custom quota at 10 GB/day per project
  per DECISIONS.md §1. Done when: a deliberate 11 GB `SELECT` is rejected.

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
