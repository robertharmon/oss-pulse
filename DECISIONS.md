# oss-pulse — Operating Decisions

> One-paragraph answers to the questions every subsequent choice depends on.
> Any decision here only changes with a replacement entry below and a note in
> the commit message. If a later ADR supersedes something here, link it.

## 1. GCP account

Dedicated Google account used only for this project (not personal Gmail).
Separates billing, IAM, and audit trails from any real-identity account.

Billing cap: **$0/month target.** Enforced by (1) Google billing alerts at $1
and $5, (2) a BigQuery custom query quota of 10 GB scanned/day, (3)
preferring serverless-and-free services (Cloud Scheduler, Cloud Run,
Streamlit Community Cloud) over always-on VMs. If a specific learning
exercise requires a paid resource (e.g., a Kestra VM for 2 weeks of
orchestrator practice), it's an explicit, time-boxed decision logged as an
ADR, not a drift.

**Project ID:** `oss-pulse-<yyyy>` (locked at project creation, cannot
change).
**Project number:** recorded in `terraform/outputs.tf` after bootstrap.

## 2. Region

`us-central1` for everything (GCS, BigQuery, Cloud Run if used).

- Best free-tier availability on BigQuery
- Lowest egress costs
- No cross-region data movement — a single-region project avoids an entire
  class of latency and billing surprises

Multi-region datasets are explicitly not used. If regulatory or latency
reasons later demand it, that's a new ADR.

## 3. Environments

Two environments only: `dev` and `prod`.

- `dev` — my working environment. Loose data, loose schedules, cheap.
  Datasets suffixed `_dev`.
- `prod` — the "running pipeline" environment. Scheduled by the
  orchestrator. Datasets suffixed `_prod`.

No `staging`. For a solo project, three environments is theater — the
dev/prod split alone exercises the right habit (don't develop against prod)
without adding a tier that will go unused.

Promotion from `dev` to `prod` happens through a PR merge, not a manual
copy.

## 4. Naming conventions

Steal the spirit of color-analytics' CONVENTIONS.md: filenames and
identifiers carry meaning out of context, specific over categorical,
vocabulary consistent.

Specifics for oss-pulse:

- **GCP project ID:** `oss-pulse-<yyyy>`
- **GCS buckets:** `osp-<purpose>-<env>` — e.g. `osp-raw-events-dev`,
  `osp-terraform-state`
- **BigQuery datasets:** `osp_<layer>_<env>` — e.g. `osp_raw_dev`,
  `osp_staging_dev`, `osp_analytics_prod`
- **BigQuery tables:**
  - Raw: `raw_<source>_<entity>` — e.g. `raw_gharchive_events`
  - Staging: `stg_<entity>` — e.g. `stg_events`, `stg_repos`
  - Marts facts: `fct_<grain>` — e.g. `fct_events`
  - Marts dimensions: `dim_<entity>` — e.g. `dim_repos`, `dim_actors`
  - Marts analytical: `mart_<question>` — e.g. `mart_trending_repos`
- **Service accounts:** `osp-<role>-<env>@...` — e.g. `osp-ingest-prod`,
  `osp-dbt-dev`
- **Secret Manager entries:** `osp_<purpose>` — e.g.
  `osp_slack_webhook_url`
- **Python modules:** snake_case; pipeline stages prefixed `sN_` where
  ordering matters
- **dbt models:** match the BigQuery table they produce
- **Terraform resources:** mirror the GCP name, no extra prefixes

## 5. Secrets policy

Zero secrets in the repo. Ever. Not in `.env` files, not in
`terraform.tfvars`, not in notebook outputs, not in commit messages.

- All secrets live in Google Secret Manager
- CI reads them from GitHub Actions secrets, scoped per environment
- Local dev reads them via `gcloud secrets versions access` — never from a
  file
- `gitleaks` runs as a pre-commit hook and as a CI job; a secret-shaped
  string blocks the commit
- Service account keys are not downloaded. Workload Identity Federation is
  used wherever possible; where it isn't, keys live in Secret Manager and
  rotate on a schedule

If a secret ever lands in a commit, the response is: rotate immediately,
scrub via `git filter-repo` only after the key is dead, log it in
`RUNBOOK.md`.

## 6. Error-handling philosophy

**Fail fast** across the whole pipeline.

Rationale: this is batch ELT. Bad data silently flowing through is worse
than a loud crash. Every stage asserts preconditions, raises on violations,
and exits non-zero. The orchestrator catches, retries transient failures,
and alerts on persistent ones.

Specifics:

- **Ingest:** HTTP non-2xx raises. Malformed JSON raises. Zero rows for an
  hour that should have thousands raises.
- **Loads:** schema mismatch between Parquet and BigQuery raises.
- **dbt:** every model has at least one `not_null` and one freshness test.
  Test failure fails the build; downstream models don't run.
- **Dashboard:** a missing mart raises in local dev, degrades gracefully in
  prod (shows "data unavailable" rather than a stack trace to the viewer).

Exception layer: user-facing surfaces (Streamlit) catch and present;
internal layers propagate.

## 7. Resource management convention

Python resources use `with` blocks exclusively. No manual `.close()`.

```python
# Yes
with bigquery.Client() as client:
    client.query(...).result()

# No
client = bigquery.Client()
client.query(...).result()
client.close()  # easy to forget on an exception path
```

Applies to: BigQuery clients, GCS clients, file handles, HTTP sessions
(`requests.Session()`), database connections.

Where a resource needs to span functions, it's passed as an argument from a
caller that owns the `with` block. No module-level globals holding open
resources.

## 8. Testing philosophy

Litmus test for every test: *if I delete one line of my code, does this
test fail?* If not, delete the test.

- **Unit tests** on pure functions: parsing, transforming, filtering.
- **Integration tests** against a BigQuery sandbox project — not mocked.
  Catches schema-and-API mismatches that unit tests miss.
- **dbt tests** on every model: not_null, unique, relationships, custom
  singular tests for business rules.
- **No tests on wiring.** If function A calls function B, that's not a
  test — it's a brittle assertion against current implementation.

Target coverage: not a number. Target: every bug caught in production
spawns a test before the fix merges.

## 9. Commit, branch, and PR conventions

- **Branches:** `<type>/<short-slug>` — e.g. `feat/hourly-ingest`,
  `fix/sqlfluff-trailing-comma`, `chore/bump-dbt-1.9`
- **Commits:** Conventional Commits-ish. `type(scope): subject` where
  scope is a top-level folder. Body explains *why*. Not strict —
  human-readable wins over machine-parseable.
- **PRs:** feature-branch → PR → CI green → self-review (even solo) →
  merge. Squash merge to keep main linear. Branch deleted on merge.
- **PR descriptions:** use the template. Always answer "what could break?"
- **No force-pushes to main.** Ever.

## 10. Scope boundaries (what oss-pulse is NOT)

Said once, loudly, to resist feature creep:

- Not a streaming pipeline — hourly batch only
- Not a Kubernetes workload — single container, scheduled
- Not multi-cloud — GCP only
- Not multi-source — GH Archive only (until v1 ships cleanly)
- No ML models in v1 — analytics only
- No user auth on the dashboard beyond Streamlit's built-in password
- No PagerDuty-style on-call — Slack webhook alerts are the ceiling

Anything in this list requires its own ADR before scope changes.

---

## Change log

| Date | Change | ADR |
|---|---|---|
| 2026-10-05 | Initial version committed. | — |
