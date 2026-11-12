# oss-pulse — Access Matrix

> Who and what can read or write each project, dataset, bucket, secret,
> service, and the Terraform state. Even for a solo project, this defines
> the service accounts and their roles.
>
> **This file is the authority. Terraform implements it exactly.** The
> [bindings table](#4-bindings-the-canonical-table) is designed to be
> machine-checked. Backlog B11 adds a CI script that diffs it against the
> IAM resources in `terraform/` and fails the build on drift in either
> direction. To change access, change this table and the Terraform in the
> same PR.
>
> Environments, agent identities and spending caps come from
> [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md):
> - dev lives in `oss-pulse-dev-<yyyy>`, prod in `oss-pulse-<yyyy>`;
> - both are billed and hard-capped;
> - agents reach dev only, through their own bot identity.

---

## 1. Principles

- **Least privilege, scoped as narrowly as the resource allows.** Grant on
  the dataset, bucket, secret, service or service account, not the
  project, unless the permission only exists at project level (e.g.
  running BigQuery jobs).
- **One service account per job, per environment.** A buggy or
  compromised job can only reach what that job needs.
- **No service-account key files**, with one documented exception (§6).
  - Cloud Run services use their attached identity.
  - GitHub Actions uses Workload Identity Federation (short-lived tokens).
  - The agent's bot account can only mint tokens for one dev service
    account.
- **No credential on the agent's machine reaches prod, billing, or IAM.**
- **Every grant states why it exists.**
- **Be honest about all-powerful identities.** Where an identity is
  effectively Owner, say so, and say what actually guards it.

## 2. Principals

Member strings are written as they'll appear in Terraform. In §4,
`<name>@…` is shorthand for `<name>@<that table's project>.iam.gserviceaccount.com`,
and `principalSet://…dev…/` or `…prod…/` for the full pool path shown
below. The B11 diff script expands both.
`<author-email>`, `<bot-email>`, `<yyyy>`, `<pool>` and `<prod-project-number>`
are filled in at setup. The GitHub repository is pinned by its immutable
numeric ID, `1406578436` (owner ID `1310922`), not its name.

| Principal | Member string | Env | Used by |
|---|---|---|---|
| Author | `user:<author-email>` | dev, prod | The author, from the Console, Cloud Shell, or the cutover session |
| Bot Google account | `user:<bot-email>` | dev | The AI build agent's `gcloud` login. Its only grant is minting tokens for `osp-builder-dev`. |
| Build agent SA | `serviceAccount:osp-builder-dev@oss-pulse-dev-<yyyy>.iam.gserviceaccount.com` | dev | What the agent actually acts as |
| Dev CI SA | `serviceAccount:osp-ci-dev@oss-pulse-dev-<yyyy>.iam.gserviceaccount.com` | dev | GitHub Actions PR checks that need real BigQuery |
| Ingest SA | `serviceAccount:osp-ingest-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Cloud Run ingest service runtime |
| dbt SA | `serviceAccount:osp-dbt-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Cloud Run dbt service runtime |
| Scheduler SA | `serviceAccount:osp-scheduler-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Cloud Scheduler's identity when invoking ingest |
| Dashboard SA | `serviceAccount:osp-dashboard-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Streamlit Community Cloud app |
| Build SA | `serviceAccount:osp-build-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Cloud Build when building the services from source |
| Terraform plan SA | `serviceAccount:osp-tf-plan-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | `terraform plan` in the `prod-plan` GitHub Environment |
| Terraform apply SA | `serviceAccount:osp-tf-apply-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | `terraform apply` in the `prod-apply` GitHub Environment |
| Deploy SA | `serviceAccount:osp-deploy-prod@oss-pulse-<yyyy>.iam.gserviceaccount.com` | prod | Service deploys in the `prod-deploy` GitHub Environment |
| Kill-switch SA | `serviceAccount:osp-killswitch-<env>@<project>.iam.gserviceaccount.com` | dev, prod | The billing kill-switch function and its Pub/Sub trigger (DECISIONS §1) |

### GitHub identities (WIF principal sets)

A workload identity pool in each project trusts GitHub's OIDC issuer.
- **Provider attribute condition**, which every token must pass:
  `assertion.repository_id == '1406578436' && assertion.event_name != 'pull_request_target'`.
- **Mapped attributes:**
  `attribute.repository_id = assertion.repository_id` and
  `attribute.gh_env = assertion.environment`. GitHub only sends the
  `environment` claim for jobs that name one, so jobs without an
  environment can never match a `gh_env` principal set. Setup verifies
  that such tokens are refused rather than mapped to an empty value.

| Principal set | Member string | Matches |
|---|---|---|
| Any workflow in this repo (dev pool) | `principalSet://iam.googleapis.com/projects/<dev-project-number>/locations/global/workloadIdentityPools/<pool>/attribute.repository_id/1406578436` | Any branch, including agent branches. Fine, because it only unlocks `osp-ci-dev`. |
| `prod-plan` environment | `principalSet://iam.googleapis.com/projects/<prod-project-number>/locations/global/workloadIdentityPools/<pool>/attribute.gh_env/prod-plan` | Jobs using GitHub Environment `prod-plan` |
| `prod-apply` environment | `principalSet://…/attribute.gh_env/prod-apply` | Jobs using GitHub Environment `prod-apply` |
| `prod-deploy` environment | `principalSet://…/attribute.gh_env/prod-deploy` | Jobs using GitHub Environment `prod-deploy` |

**GitHub Environment protection** is configured by the author and is what
actually guards prod:
- **`prod-plan`:**
  - The author is a required reviewer, so a job can only get a prod-plan
    token after the author approves that run.
  - Deployment branches are limited to `main` and `build/agentic`. Both are
    ruleset-protected, and changes to `.github/**` there need the author's
    code-owner review.
  - So the workflow asking for the token was itself reviewed. An agent
    branch can't even request it. (GitHub's approval screen doesn't show
    the workflow diff, which is why the branch limit matters.)
- **`prod-apply` / `prod-deploy`:** the author is a required reviewer,
  **and** deployment is limited to the `main` branch.

The bot has write access but not admin, so it can't change these settings.

## 3. What "dev" hosts

The dev project is billed but capped (DECISIONS §1).
- **The agent can only use BigQuery and one bucket**, `osp-raw-events-dev`,
  so that's all it builds against.
- **The only other thing in dev is the kill switch:** one Cloud Run
  function, plus its Pub/Sub topic and budget, deployed by the author.
- Pipeline Cloud Run services, Scheduler, Secret Manager and alerting are
  prod-only until cutover. The `-dev` pipeline runtime identities aren't
  created.
- **Dev datasets** (`osp_raw_dev`, `osp_staging_dev`, `osp_analytics_dev`)
  are created by the author with a 7-day default table expiration.
  - The builder can also create its own scratch datasets (project-level
    `dataEditor`), and becomes their owner implicitly. That ownership
    includes changing those datasets' access lists. It's an IAM-like power,
    but only over its own dev scratch data.
  - It also means the 7-day expiration is a default the builder could skip
    on a dataset it creates. **The budget and kill switch are the real
    storage cap.** B11 adds a check that flags any dev dataset without the
    expiration.
- **Dev Terraform state** is local and disposable, kept out of git by
  `.gitignore`. Dev holds nothing worth a state bucket.

## 4. Bindings (the canonical table)

One row per real binding. The diff script compares (Member, Scope, Role,
Condition):
- **Scope** is one of:
  - `project:<id>`;
  - `dataset:<project>.<dataset>`;
  - `bucket:<name>`;
  - `secret:<project>/<name>`;
  - `run-service:<project>/us-central1/<name>`;
  - `sa:<email-local-part>` (a grant *on* that service account, letting the
    member act as it, in the project its row names).
- **Condition** is `-` when there is none.

### 4.1 Dev (`oss-pulse-dev-<yyyy>`)

| Member | Scope | Role | Condition | Why |
|---|---|---|---|---|
| `user:<author-email>` | `project:oss-pulse-dev-<yyyy>` | `roles/owner` | - | Someone must own it. |
| `user:<bot-email>` | `sa:osp-builder-dev` | `roles/iam.serviceAccountTokenCreator` | - | The bot's only power: minting short-lived tokens for the build SA. No project role at all. |
| `serviceAccount:osp-builder-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/bigquery.dataEditor` | - | Read and write every dev dataset, including the author-created `osp_*_dev`, and create scratch datasets (see §3 for the implicit ownership that brings). |
| `serviceAccount:osp-builder-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/bigquery.jobUser` | - | Run queries and load jobs. |
| `serviceAccount:osp-builder-dev@…` | `bucket:osp-raw-events-dev` | `roles/storage.objectUser` | - | Test the ingest GCS step for real. Read, write, overwrite. |
| `serviceAccount:osp-ci-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/bigquery.dataEditor` | - | Each PR run creates a throwaway dataset, loads the checked-in fixtures into it, builds, and deletes it. It doesn't read shared dev tables, which expire weekly. |
| `serviceAccount:osp-ci-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/bigquery.jobUser` | - | Run the build's queries and load jobs. |
| `principalSet://…dev…/attribute.repository_id/1406578436` | `sa:osp-ci-dev` | `roles/iam.workloadIdentityUser` | - | Any workflow in this repo may act as dev CI. Dev only. |
| `serviceAccount:osp-killswitch-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/billing.projectManager` | - | Unlink billing when the budget is crossed. |
| `serviceAccount:osp-killswitch-dev@…` | `project:oss-pulse-dev-<yyyy>` | `roles/browser` | - | Google's "modify project billing" permissions need Project Browser alongside Project Billing Manager. |
| `serviceAccount:osp-killswitch-dev@…` | `billing-account:<billing-account-id>` | `roles/billing.viewer` | - | Also required by Google to change a project's billing link. Applied by the author on the billing account. |
| `serviceAccount:osp-killswitch-dev@…` | `run-service:oss-pulse-dev-<yyyy>/us-central1/osp-killswitch-dev` | `roles/run.invoker` | - | The Pub/Sub trigger runs as this identity and must be allowed to call the function. |

### 4.2 Prod (`oss-pulse-<yyyy>`)

| Member | Scope | Role | Condition | Why |
|---|---|---|---|---|
| `user:<author-email>` | `project:oss-pulse-<yyyy>` | `roles/owner` | - | Solo project. Unavoidable. |
| `serviceAccount:osp-ingest-prod@…` | `bucket:osp-raw-events-prod` | `roles/storage.objectUser` | - | Write each hour's Parquet. Needs delete as well as create, because re-ingesting an hour overwrites its file. |
| `serviceAccount:osp-ingest-prod@…` | `dataset:oss-pulse-<yyyy>.osp_raw_prod` | `roles/bigquery.dataEditor` | - | Load jobs write each hour's partition of `raw_gharchive_events` (overwriting it on replay) and write `raw_ingest_audit`. |
| `serviceAccount:osp-ingest-prod@…` | `project:oss-pulse-<yyyy>` | `roles/bigquery.jobUser` | - | Load jobs are BigQuery jobs. |
| `serviceAccount:osp-ingest-prod@…` | `run-service:oss-pulse-<yyyy>/us-central1/osp-dbt-prod` | `roles/run.invoker` | - | Ingest triggers the dbt build when its load finishes. |
| `serviceAccount:osp-dbt-prod@…` | `dataset:oss-pulse-<yyyy>.osp_raw_prod` | `roles/bigquery.dataViewer` | - | Read raw. Never writes it. |
| `serviceAccount:osp-dbt-prod@…` | `dataset:oss-pulse-<yyyy>.osp_staging_prod` | `roles/bigquery.dataEditor` | - | Build staging models. |
| `serviceAccount:osp-dbt-prod@…` | `dataset:oss-pulse-<yyyy>.osp_analytics_prod` | `roles/bigquery.dataEditor` | - | Build facts, dimensions and marts. |
| `serviceAccount:osp-dbt-prod@…` | `project:oss-pulse-<yyyy>` | `roles/bigquery.jobUser` | - | dbt runs queries. |
| `serviceAccount:osp-scheduler-prod@…` | `run-service:oss-pulse-<yyyy>/us-central1/osp-ingest-prod` | `roles/run.invoker` | - | The hourly trigger. Nothing else. |
| `serviceAccount:osp-dashboard-prod@…` | `dataset:oss-pulse-<yyyy>.osp_analytics_prod` | `roles/bigquery.dataViewer` | - | Read marts only. Can't see raw or staging. |
| `serviceAccount:osp-dashboard-prod@…` | `project:oss-pulse-<yyyy>` | `roles/bigquery.jobUser` | - | A `SELECT` is a query job; read access alone can't run one. A per-user query quota caps this identity (§6). |
| `serviceAccount:osp-build-prod@…` | `project:oss-pulse-<yyyy>` | `roles/run.builder` | - | Cloud Build runs as this identity to build images from source. Replaces the Compute Engine default service account, which gets broad `editor` by default. |
| `serviceAccount:osp-deploy-prod@…` | `project:oss-pulse-<yyyy>` | `roles/run.sourceDeveloper` | - | `gcloud run deploy --source` (DECISIONS §10). |
| `serviceAccount:osp-deploy-prod@…` | `project:oss-pulse-<yyyy>` | `roles/serviceusage.serviceUsageConsumer` | - | Required alongside `run.sourceDeveloper` for source deploys. |
| `serviceAccount:osp-deploy-prod@…` | `sa:osp-ingest-prod` | `roles/iam.serviceAccountUser` | - | Deploy a service that runs *as* the ingest identity. |
| `serviceAccount:osp-deploy-prod@…` | `sa:osp-dbt-prod` | `roles/iam.serviceAccountUser` | - | Same, for dbt. |
| `serviceAccount:osp-deploy-prod@…` | `sa:osp-build-prod` | `roles/iam.serviceAccountUser` | - | Submit builds that run as the build identity. |
| `serviceAccount:osp-tf-plan-prod@…` | `project:oss-pulse-<yyyy>` | `roles/viewer` | - | `plan` reads every resource's current state. Note that `viewer` includes reading BigQuery data, which is why this identity sits behind the `prod-plan` environment. |
| `serviceAccount:osp-tf-plan-prod@…` | `project:oss-pulse-<yyyy>` | `roles/iam.securityReviewer` | - | `plan` must read IAM policies to diff them; `viewer` doesn't include that. |
| `serviceAccount:osp-tf-plan-prod@…` | `bucket:osp-terraform-state` | `roles/storage.objectViewer` | - | Read state. Plan runs with `-lock=false`, so it never writes. |
| `serviceAccount:osp-tf-apply-prod@…` | `project:oss-pulse-<yyyy>` | `roles/editor` | - | Create and change resources. |
| `serviceAccount:osp-tf-apply-prod@…` | `project:oss-pulse-<yyyy>` | `roles/iam.securityAdmin` | - | Get and set IAM policy on any resource (bucket, dataset, service, service account), which the per-resource rows above require. |
| `serviceAccount:osp-tf-apply-prod@…` | `bucket:osp-terraform-state` | `roles/storage.objectAdmin` | - | Read, write and lock state. |
| `principalSet://…prod…/attribute.gh_env/prod-plan` | `sa:osp-tf-plan-prod` | `roles/iam.workloadIdentityUser` | - | Only `prod-plan` jobs (author-approved) can act as the plan identity. |
| `principalSet://…prod…/attribute.gh_env/prod-apply` | `sa:osp-tf-apply-prod` | `roles/iam.workloadIdentityUser` | - | Only `prod-apply` jobs (author-approved, `main` only). |
| `principalSet://…prod…/attribute.gh_env/prod-deploy` | `sa:osp-deploy-prod` | `roles/iam.workloadIdentityUser` | - | Only `prod-deploy` jobs (author-approved, `main` only). |
| `serviceAccount:osp-killswitch-prod@…` | `project:oss-pulse-<yyyy>` | `roles/billing.projectManager` | - | As in dev. |
| `serviceAccount:osp-killswitch-prod@…` | `project:oss-pulse-<yyyy>` | `roles/browser` | - | As in dev. |
| `serviceAccount:osp-killswitch-prod@…` | `billing-account:<billing-account-id>` | `roles/billing.viewer` | - | As in dev. |
| `serviceAccount:osp-killswitch-prod@…` | `run-service:oss-pulse-<yyyy>/us-central1/osp-killswitch-prod` | `roles/run.invoker` | - | As in dev. |

**The all-powerful identity, stated plainly:** `osp-tf-apply-prod` has
`editor` plus `iam.securityAdmin`. Together these are effectively Owner:
it can act as any service account and grant itself anything. Terraform
needs this to manage IAM. **Nothing in IAM narrows it.** What guards it is
outside IAM: its token is only issued to jobs in the `prod-apply`
environment, which needs the author's approval and only runs from `main`,
which only the author merges into.

**Not granted, on purpose:**
- Nobody but the author has `owner` or billing roles. Nobody but the author
  and the kill-switch identities can touch billing.
- The bot account and `osp-builder-dev` have nothing in prod, and no IAM,
  Secret Manager or Cloud Run roles anywhere.
- `osp-dbt-prod` has no GCS access. dbt reads raw from BigQuery, never from
  the bucket.
- `osp-dashboard-prod` has nothing outside `osp_analytics_prod`.
- **No identity reads `osp_slack_webhook_url` programmatically.**
  - The Slack notification channel is **created by hand, outside
    Terraform**. Terraform receives only the channel's ID, as a plain
    variable.
  - Managing the channel in Terraform would copy the webhook URL into
    Terraform state on every refresh, even with `ignore_changes`.
  - The Secret Manager entry is the author's record copy.
- The **Compute Engine default service account must not hold `editor`.**
  It's removed at cutover, and Cloud Build uses `osp-build-prod` instead.
  A grant that must be *absent* can't be a §4 row, so B11's diff script
  checks it explicitly.

**Confirmed during the build, then updated here:**
- Whether `run.builder` alone covers everything `osp-build-prod` needs
  (Artifact Registry push, logs, source bucket read).
- Whether the three kill-switch grants above suffice. Google's own
  sample uses the much broader `billing.admin`.
- That `gcloud run deploy --source` accepts the custom build identity
  (`--build-service-account`) and its required logging setting.
- The language-lookup job (data contract §5.7, option A), if chosen, adds
  one `secretAccessor` grant on `osp_github_token`.

## 5. Resource view

The same grants, read by resource ("who can touch X?"). If this and §4
disagree, §4 wins.

| Resource | Write | Read |
|---|---|---|
| GCS `osp-raw-events-dev` | `osp-builder-dev` | `osp-builder-dev`; author |
| BigQuery `osp_*_dev` | `osp-builder-dev`; per-PR CI datasets by `osp-ci-dev` | `osp-builder-dev`; `osp-ci-dev` (its own per-PR datasets); author |
| GCS `osp-raw-events-prod` | `osp-ingest-prod` | `osp-ingest-prod`; author |
| GCS `osp-terraform-state` | `osp-tf-apply-prod`; author | `osp-tf-plan-prod` |
| BigQuery `osp_raw_prod` | `osp-ingest-prod` | `osp-dbt-prod`; author; `osp-tf-plan-prod` (via `viewer`) |
| BigQuery `osp_staging_prod` | `osp-dbt-prod` | author; `osp-tf-plan-prod` (via `viewer`) |
| BigQuery `osp_analytics_prod` | `osp-dbt-prod` | `osp-dashboard-prod`; author; `osp-tf-plan-prod` (via `viewer`) |
| Secret `osp_slack_webhook_url` | author | author |
| Cloud Run `osp-ingest-prod` | `osp-deploy-prod` (deploys) | invoked by `osp-scheduler-prod` |
| Cloud Run `osp-dbt-prod` | `osp-deploy-prod` (deploys) | invoked by `osp-ingest-prod` |

## 6. Credentials and controls outside IAM

| Item | Lives in | Notes |
|---|---|---|
| `osp-dashboard-prod` key JSON | Streamlit Community Cloud app secrets | **The one key-file exception.** Streamlit Community Cloud can't use Workload Identity Federation. Scoped to read-only on marts, with a **per-user BigQuery query quota** so a leaked key can't use up the project's 10 GB/day and stall dbt. This contradicts DECISIONS §5 ("keys live in Secret Manager") as written; A12 (`docs/security.md`, pending) reconciles §5 and sets the rotation schedule. |
| Bot GitHub account's fine-grained token | The agent machine's `gh` login | Repo-scoped, **write** not admin, 90-day expiry (`docs/author_setup.md` §1.2). Can't change rulesets, environments or secrets. |
| Bot Google account's login | The agent machine's `gcloud` config | Can only mint tokens for `osp-builder-dev` (§4.1). |
| Slack webhook for CI alerts | GitHub Actions secret `SLACK_WEBHOOK_URL` | Allowed by DECISIONS §5. |
| WIF provider name, service-account emails | GitHub Actions variables (not secrets) | Identifiers, not credentials. |

**Public-repo note:**
- **The repo is public.** Workflows triggered by `pull_request` from forks
  get no secrets and no OIDC token.
- **`pull_request_target` does get them, so it's banned.** The WIF provider
  condition rejects tokens from it, and a CI check (B11) will reject any
  workflow file that uses it.
- **Workflows running inside a fork's own repository can't get a token:**
  the provider condition requires this repository's numeric ID, and a fork
  has a different one. (Fork *pull requests* run in this repository; the
  `pull_request` rule above is what covers those.)

## 7. Change rules

- **Any change to §4 ships in the same PR as the Terraform that implements
  it.** Once B11 lands, CI fails the build if they disagree.
- **`docs/access_matrix.md` and `terraform/**` are CODEOWNERS-protected.**
  An agent can propose an access change, but the author approves it.
- **Prod grants are applied only by `prod-apply`** (author-approved,
  `main` only). **Dev grants to the bot or to `osp-builder-dev` are applied
  by the author by hand** (`docs/author_setup.md`), never by the agent.
- **Adding a principal** means a new row in §2 and its grants in §4. Never
  a broader grant on an existing identity "to make it work."

## Change log

| Date | Change |
|---|---|
| 2026-11-11 | Second review pass: `prod-plan` limited to protected branches; Slack channel kept out of Terraform; kill-switch grants completed (Browser, billing-account Viewer, invoker); builder and CI SAs moved to explicit `dataEditor` + `jobUser`; CI loads fixtures per run instead of reading expiring shared tables; Compute-default `editor` absence becomes a B11 check. |
| 2026-11-11 | Initial version (backlog A8), per ADR 0002. Corrects `architecture.md` §7 in four places: dbt has no GCS access; the dashboard also needs `bigquery.jobUser`; the separate "reviewer" identity is dropped (the solo author is Owner, so it would add an identity without removing any access); and "no human developer access in prod" doesn't hold for a solo Owner. Adds a dedicated build identity, environment-gated prod CI identities, and kill-switch identities. |
