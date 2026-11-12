# oss-pulse — Access Matrix

> Who and what can read or write each project, dataset, bucket, secret,
> service and the Terraform state. Even for a solo project, this table
> defines the service accounts and their roles.
>
> **This file is the authority. Terraform implements it exactly.** The
> [Bindings](#3-bindings-the-canonical-table) table is machine-checked: a
> CI script diffs it against the IAM bindings declared in `terraform/`,
> and any drift in either direction fails the build. To change access,
> change this table and the Terraform in the same PR.
>
> Environments and the two-project split come from
> [ADR 0002](adr/0002-agentic-build-out-and-sandbox-dev.md): dev lives in
> `oss-pulse-dev-<yyyy>` (no billing), prod in `oss-pulse-<yyyy>` (billed).

---

## 1. Principles

- **Least privilege, scoped as narrowly as the resource allows.** Grant on
  the dataset, bucket, secret or service, not the project, unless the
  permission only exists at project level (e.g. running BigQuery jobs).
- **One service account per job, per environment.** If a job is
  compromised or buggy, it can only reach what that one job needs.
- **No service-account key files**, with one documented exception
  (§5).
  - Cloud Run services use their attached identity.
  - GitHub Actions uses Workload Identity Federation (short-lived tokens).
  - The author and the build agent use impersonation.
- **Agents never hold a credential for the prod project.**
- **Writers are not readers by default.** Each grant states why it exists.

## 2. Principals

| Principal | Kind | Env | Used by |
|---|---|---|---|
| Author (`user:` the author's dedicated Google account) | Human | dev, prod | The author, day to day, through `gcloud auth application-default login` |
| `osp-builder-dev` | Service account | dev | The AI build agent, through impersonation by the author's login |
| `osp-ci-dev` | Service account | dev | GitHub Actions PR checks that need real BigQuery (WIF) |
| `osp-ingest-<env>` | Service account | dev (identity only), prod | Cloud Run ingest service runtime |
| `osp-dbt-<env>` | Service account | dev (identity only), prod | Cloud Run dbt service runtime |
| `osp-scheduler-<env>` | Service account | prod | Cloud Scheduler, to invoke the ingest service |
| `osp-dashboard-<env>` | Service account | prod | Streamlit Community Cloud app |
| `osp-tf-plan-prod` | Service account | prod | GitHub Actions `terraform plan` on PRs (WIF, any branch of this repo) |
| `osp-tf-apply-prod` | Service account | prod | GitHub Actions `terraform apply` on merge (WIF, `main` only) |
| `osp-deploy-prod` | Service account | prod | GitHub Actions deploy of Cloud Run services on merge (WIF, `main` only) |

**dev (identity only):** the dev project has no billing, so Cloud Run and
GCS can't run there (see §6). The `-dev` runtime identities still exist so
Terraform's dev and prod configurations stay the same shape. They hold no
grants in dev.

## 3. Bindings (the canonical table)

Column meanings:
- **Scope** is where the grant is attached:
  - `project`;
  - `dataset:<name>`;
  - `bucket:<name>`;
  - `secret:<name>`;
  - `service:<cloud-run-service>`;
  - `sa:<service-account>` (a grant *on* a service account, letting the
    member act as it).
- `<env>` rows exist once per environment listed in **Env**.

| Member | Scope | Role | Env | Why |
|---|---|---|---|---|
| Author | `project` | `roles/owner` | dev, prod | Solo project; someone must own it. Unavoidable. |
| Author | `sa:osp-builder-dev` | `roles/iam.serviceAccountTokenCreator` | dev | Lets the author's login mint short-lived tokens for the build agent. Explicit, so the agent path doesn't depend on what `owner` happens to include. |
| `osp-builder-dev` | `project` | `roles/bigquery.user` | dev | Run queries and create the agent's own scratch datasets. |
| `osp-builder-dev` | `dataset:osp_raw_dev` | `roles/bigquery.dataEditor` | dev | Load test data into raw. |
| `osp-builder-dev` | `dataset:osp_staging_dev` | `roles/bigquery.dataEditor` | dev | Build staging models. |
| `osp-builder-dev` | `dataset:osp_analytics_dev` | `roles/bigquery.dataEditor` | dev | Build marts. |
| `osp-ci-dev` | `project` | `roles/bigquery.user` | dev | Run per-PR builds in throwaway datasets that CI creates and deletes. |
| `osp-ci-dev` | `sa:osp-ci-dev` | `roles/iam.workloadIdentityUser` → GitHub principal set, repo `robertharmon/oss-pulse` | dev | WIF: only workflows from this repo can act as the CI identity. |
| `osp-ingest-<env>` | `bucket:osp-raw-events-<env>` | `roles/storage.objectUser` | prod | Write each hour's Parquet. Needs delete as well as create, because re-ingesting an hour overwrites its file (the pipeline is idempotent on hour). |
| `osp-ingest-<env>` | `dataset:osp_raw_<env>` | `roles/bigquery.dataEditor` | prod | Load jobs append to `raw_gharchive_events` and write `raw_ingest_audit`. |
| `osp-ingest-<env>` | `project` | `roles/bigquery.jobUser` | prod | Load jobs are BigQuery jobs. |
| `osp-ingest-<env>` | `service:osp-dbt-<env>` | `roles/run.invoker` | prod | Ingest triggers the dbt build when its load finishes. |
| `osp-dbt-<env>` | `dataset:osp_raw_<env>` | `roles/bigquery.dataViewer` | prod | Read raw. Never writes it. |
| `osp-dbt-<env>` | `dataset:osp_staging_<env>` | `roles/bigquery.dataEditor` | prod | Build staging models. |
| `osp-dbt-<env>` | `dataset:osp_analytics_<env>` | `roles/bigquery.dataEditor` | prod | Build facts, dimensions and marts. |
| `osp-dbt-<env>` | `project` | `roles/bigquery.jobUser` | prod | dbt runs queries. |
| `osp-scheduler-<env>` | `service:osp-ingest-<env>` | `roles/run.invoker` | prod | The hourly trigger. Nothing else. |
| `osp-dashboard-<env>` | `dataset:osp_analytics_<env>` | `roles/bigquery.dataViewer` | prod | Read marts only. Cannot see raw or staging. |
| `osp-dashboard-<env>` | `project` | `roles/bigquery.jobUser` | prod | A `SELECT` is a query job. Without this, read access alone can't run a query. |
| `osp-tf-plan-prod` | `project` | `roles/viewer` | prod | `terraform plan` reads current state of every resource. |
| `osp-tf-plan-prod` | `project` | `roles/iam.securityReviewer` | prod | Plan must read IAM policies to diff them; `viewer` doesn't include that. |
| `osp-tf-plan-prod` | `bucket:osp-terraform-state` | `roles/storage.objectViewer` | prod | Read state. Plan runs with `-lock=false`, so it never writes. |
| `osp-tf-plan-prod` | `sa:osp-tf-plan-prod` | `roles/iam.workloadIdentityUser` → GitHub principal set, repo `robertharmon/oss-pulse` | prod | WIF for PR plans. |
| `osp-tf-apply-prod` | `project` | `roles/editor` | prod | Create and change resources. |
| `osp-tf-apply-prod` | `project` | `roles/resourcemanager.projectIamAdmin` | prod | Apply the bindings in this table. `editor` can't change IAM. |
| `osp-tf-apply-prod` | `bucket:osp-terraform-state` | `roles/storage.objectAdmin` | prod | Read, write and lock state. |
| `osp-tf-apply-prod` | `secret:osp_slack_webhook_url` | `roles/secretmanager.secretAccessor` | prod | Read the webhook URL when creating the alert notification channel. |
| `osp-tf-apply-prod` | `sa:osp-tf-apply-prod` | `roles/iam.workloadIdentityUser` → GitHub principal set, repo `robertharmon/oss-pulse`, ref `refs/heads/main` | prod | WIF, restricted to the protected `main` branch. A PR branch can't apply. |
| `osp-deploy-prod` | `project` | `roles/run.developer` | prod | Deploy new revisions of the two Cloud Run services. |
| `osp-deploy-prod` | `project` | `roles/cloudbuild.builds.editor` | prod | `gcloud run deploy --source` builds the image in Cloud Build (DECISIONS §10). |
| `osp-deploy-prod` | `sa:osp-ingest-prod` | `roles/iam.serviceAccountUser` | prod | Deploy a service that runs *as* the ingest identity. |
| `osp-deploy-prod` | `sa:osp-dbt-prod` | `roles/iam.serviceAccountUser` | prod | Same, for the dbt service. |
| `osp-deploy-prod` | `sa:osp-deploy-prod` | `roles/iam.workloadIdentityUser` → GitHub principal set, repo `robertharmon/oss-pulse`, ref `refs/heads/main` | prod | WIF, `main` only. |

**Not granted, on purpose:**
- Nobody but the author has `owner`, billing roles, or the ability to
  create projects.
- `osp-builder-dev` and `osp-ci-dev` have nothing in prod. They also have no
  IAM, Storage, Secret Manager or Cloud Run roles in dev.
- `osp-dbt-<env>` has no GCS access. dbt reads raw from BigQuery, never
  from the bucket. (`architecture.md` §7 says the dbt identity reads the
  bucket; that's corrected here.)
- `osp-dashboard-<env>` has nothing outside `osp_analytics_<env>`.

**To be confirmed during the build:**
- Cloud Build's deploy path (`--source`) also uploads source to a staging
  bucket and pushes to Artifact Registry using Cloud Build's own service
  account. The exact extra roles `osp-deploy-prod` needs are confirmed in
  the deploy-workflow PR, and this table is updated in the same PR.
- **The language-lookup job** (data contract §5.7, option A) would add one
  `secretAccessor` grant on `osp_github_token` for whichever identity runs
  it. Added when that option is chosen.

## 4. Resource view

The same grants, read by resource. Useful when the question is "who can
touch X?". If this view and §3 ever disagree, §3 wins.

| Resource | Env | Write | Read |
|---|---|---|---|
| GCS `osp-raw-events-prod` | prod | `osp-ingest-prod` | `osp-ingest-prod`; author |
| GCS `osp-terraform-state` | prod | `osp-tf-apply-prod`; author | `osp-tf-plan-prod` |
| BigQuery `osp_raw_<env>` | dev | `osp-builder-dev`; per-PR CI datasets are separate | author; `osp-builder-dev` |
| BigQuery `osp_raw_<env>` | prod | `osp-ingest-prod` | `osp-dbt-prod`; author |
| BigQuery `osp_staging_<env>` | dev | `osp-builder-dev` | same |
| BigQuery `osp_staging_<env>` | prod | `osp-dbt-prod` | author |
| BigQuery `osp_analytics_<env>` | dev | `osp-builder-dev` | same |
| BigQuery `osp_analytics_<env>` | prod | `osp-dbt-prod` | `osp-dashboard-prod`; author |
| Secret `osp_slack_webhook_url` | prod | author (sets the value by hand) | `osp-tf-apply-prod` |
| Cloud Run `osp-ingest-prod` | prod | `osp-deploy-prod` (deploys) | invoked by `osp-scheduler-prod` |
| Cloud Run `osp-dbt-prod` | prod | `osp-deploy-prod` (deploys) | invoked by `osp-ingest-prod` |

## 5. Credentials outside GCP

| Credential | Lives in | Used by | Notes |
|---|---|---|---|
| `osp-dashboard-prod` key JSON | Streamlit Community Cloud app secrets | The dashboard | **The one key-file exception.** Streamlit Community Cloud can't use Workload Identity Federation, so it needs a key. Scoped to read-only on marts (§3). Rotation schedule lives in `docs/security.md`. Never stored in the repo or on the laptop beyond the moment of pasting it in. |
| Slack webhook URL for CI alerts | GitHub Actions secret `SLACK_WEBHOOK_URL` | CI failure notifications | Same webhook as the Secret Manager copy. Allowed by DECISIONS §5 (CI reads secrets from GitHub Actions secrets). |
| WIF provider and service-account emails | GitHub Actions variables (not secrets) | CI workflows | Identifiers, not credentials. A token is only issued to workflows that match the provider's repo and branch condition. |

**Public repo note:** the repo is public. Workflows triggered by pull
requests from forks don't receive OIDC tokens or secrets, so a fork can't
reach any identity above. The WIF conditions pin the repository by name
as a second guard.

## 6. What the dev project can't host

Without billing, the dev project runs BigQuery only.
- **GCS, Secret Manager, Cloud Run and Cloud Scheduler** are expected to
  need a billing account. Confirm this in the milestone-2 sandbox spike and
  update this section.
- In dev, ingest writes Parquet to the local filesystem and loads it into
  BigQuery from there.
- **Dev Terraform state** is local and disposable, kept out of git by
  `.gitignore`. Hosting it in a bucket would need billing, and the dev
  project holds nothing worth protecting.

## 7. Change rules

- **Any change to §3 ships in the same PR as the Terraform that implements
  it.** CI fails the build if they disagree.
- **Prod grants need the author's review.** Agents may propose them in a PR
  but can't apply them: `osp-tf-apply-prod` only acts from `main`, and
  only the author merges to `main`.
- **Adding a principal** means a new row in §2 and its grants in §3. Never
  a broader grant on an existing identity "to make it work."

## Change log

| Date | Change |
|---|---|
| 2026-11-11 | Initial version (backlog A8). Two-project model per ADR 0002. Corrects `architecture.md` §7: dbt has no GCS access; the dashboard also needs `bigquery.jobUser` to run queries. |
