# oss-pulse — Security Posture

> What this project protects, what data it handles, where every credential
> lives and when it rotates, what gets logged, and how a security problem
> is reported and disclosed.
>
> Who can access what is in [`access_matrix.md`](access_matrix.md); how agents
> are isolated is in [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md);
> what to do in an incident is in [`RUNBOOK.md`](../RUNBOOK.md) §3.4–§3.5.
> This doc doesn't repeat them. It sets the policies they implement.

---

## 1. What we're protecting

All data in this project is public. **Confidentiality of the data isn't the
goal.** The things worth protecting are, in order:

1. **Money.** A leaked credential or a runaway job that runs up a bill.
   Covered by the spending guards in DECISIONS §1 and
   [`cost_model.md`](cost_model.md) §7.
2. **Credentials.** A leaked key lets someone else use our projects or
   impersonate the author or the bot (§3).
3. **Integrity of what we publish.** The dashboard should show numbers the
   pipeline computed, and the repo should contain code the author approved:
   protected branches, required reviews, and no agent access to prod
   (ADR 0002 §2–§3).
4. **The people in the data.** Handles in the data are public but
   identifiable; we don't amplify them (§2.2).

## 2. Data classes

### 2.1 Every source and dataset, labelled

| Data | Class | Notes |
|---|---|---|
| GH Archive hourly files | **Public** | GitHub's public events, republished by GH Archive. We don't redistribute them (data contract §3.4). |
| GCS `osp-raw-events-<env>` (Parquet) | Public, derived | Same content, re-encoded. 14-day retention. |
| `raw_gharchive_events`, `stg_events` | Public, derived; contains **free text** (§2.3) and **pseudonymous identifiers** (§2.2) | 3-day retention. |
| `fct_events`, `dim_repos`, `stg_repos`, `stg_actors`, `dim_actors` | Public, derived; pseudonymous identifiers | `dim_actors` keeps `actor_login`. |
| `mart_*` tables | Public, aggregate | What the dashboard shows. Repo names, never actor logins. |
| `raw_ingest_audit` | Operational | Ingest run metadata: hours, timestamps, counts. |
| Cloud Logging, audit logs | Operational | May contain identities (service-account emails, the author's email). Not public. |
| Credentials (§3) | **Secret** | Never in the repo, in logs, or in Terraform state. |
| Config (project IDs, SA emails, WIF provider name) | Non-secret | Identifiers, not credentials. Fine in GitHub Actions variables and in code. |

There's no payment data, no regulated data, and nothing the project
collects from its own users. The dashboard has no accounts.

### 2.2 Personal data posture

`actor_id` and `actor_login` identify GitHub users. They're public, and
anyone can look them up, but they still point at real people. So:

- **The dashboard never shows an individual actor.** Every chart is an
  aggregate per repo, language or hour. `mart_contributor_concentration`
  reports a Gini coefficient, not who did the work.
- **We don't enrich identities.** No lookups of names, emails, locations or
  profiles, and no joining actors to outside data.
- **Retention limits exposure:** free text and logins in raw and staging
  are gone after 3 days; `fct_events` keeps only numeric IDs.
  `dim_actors` keeps `actor_login` indefinitely, because the dimension
  can't be rebuilt without a backfill.
- **Removal requests** (someone asks us to drop their data): the author
  deletes that `actor_id` from `dim_actors` and `fct_events` by hand, logs
  it as a SEV4 entry in the runbook (without the login), and replies that
  GH Archive itself is a separate service with its own policy.

### 2.3 Free text is untrusted input

GH Archive payloads carry text that anyone on GitHub wrote: issue and PR
titles and bodies, comments, release notes, repo names. Treat all of it as
hostile:

- **Never rendered as HTML.** The dashboard shows repo names with
  Streamlit's text and dataframe components, never with
  `unsafe_allow_html=True`.
- **Never executed or interpolated into SQL.** Ingest writes it as data;
  dbt only extracts `payload.action`.
- **Agents don't read payload text into their context** beyond what a task
  needs. That text can carry instructions aimed at AI agents ("ignore your
  previous instructions…"). Test fixtures use synthetic or trimmed payloads.
  When an agent has to look at real payloads, it reads fields it names, and
  treats anything instruction-like as data.

## 3. Credentials: inventory and rotation

DECISIONS §5 is the rule: no secrets in the repo, ever. This is the full
list of credentials that exist, so nothing is missed at rotation time or
during an incident.

| Credential | Lives in | Read by | Rotation | If leaked |
|---|---|---|---|---|
| Author's Google login (Owner, billing) | Author's devices; 2-step verification | Author | — (password manager, 2SV) | Google account recovery; review Cloud Audit Logs |
| Author's GitHub login (repo admin) | Author's devices; 2FA | Author | — | GitHub recovery; review the security log |
| Bot Google account login | Agent machine's `gcloud` config; password in the author's password manager | Agent | On suspicion | Disable the account's grant on `osp-builder-dev` (author, Cloud Shell) |
| Bot GitHub classic token (`repo`, `workflow`) | Agent machine's `gh` keyring | Agent | **90 days** (expiry set at creation; author_setup §1.3) | Revoke in the bot's GitHub settings |
| `osp-dashboard-prod` key JSON | Streamlit Community Cloud app secrets **only** | Dashboard | **90 days** | RUNBOOK §3.4; the per-user query quota caps the damage meanwhile |
| Slack webhook URL | Cloud Monitoring notification channel; GitHub Actions secret `SLACK_WEBHOOK_URL`; record copy in Secret Manager `osp_slack_webhook_url` | Monitoring; CI | Yearly, and on leak | RUNBOOK §3.4 (three places) |
| GitHub token for the language lookup (only if contract §5.7 option A is chosen) | Prod Secret Manager `osp_github_token` | The language-lookup job | Yearly (set at creation) | Revoke on GitHub; no repo access to lose |

**Not credentials, deliberately:**
- GitHub Actions → GCP uses Workload Identity Federation. There's no stored
  key, only short-lived tokens (access matrix §2).
- Cloud Run services use their attached identities. There's no key.
- The agent's GCP access is impersonation of `osp-builder-dev`. There's no
  key (ADR 0002 §2).

### 3.1 The dashboard key: the one key file

Streamlit Community Cloud can't use Workload Identity Federation, so the
dashboard needs a service-account key. That's the only key file the project
has (access matrix §6). Its rules:

- **Created by the author in Cloud Shell, pasted into Streamlit's app
  secrets, and deleted from Cloud Shell.** It never touches the author's
  laptop or the agent's machine.
- **No copy in Secret Manager.** A copy would be one more place to leak it,
  and nothing would read it, since Streamlit can't. DECISIONS §5 is amended
  to say so.
- **Limited to read-only on the marts dataset**, and capped by the 6 GiB
  per-user daily query quota ([`cost_model.md`](cost_model.md) §4.5).
- **Rotated every 90 days:** create the new key, update Streamlit, confirm
  the dashboard loads, then delete the old key. If GCP lets a project
  without an organization set the key-expiry policy
  (`constraints/iam.serviceAccountKeyExpiryHours` = 2160h), turn it on at
  cutover so the old key dies on its own. If it doesn't, the rotation is a
  manual calendar reminder.

### 3.2 The GitHub token for the language lookup

Contract §8 left open which account issues it. Decision:
- **The bot GitHub account issues it,** as a fine-grained token with **no
  repository permissions**. Every GitHub token can read public repositories,
  which is all the lookup needs.
- **Expiry: one year.** A leak exposes nothing beyond the bot's rate limit.
- **It lives in prod Secret Manager only.** The lookup job is the only
  reader; access matrix §4 gains one `secretAccessor` row when the job
  lands.

### 3.3 Terraform state

Terraform never holds a secret value. Secrets exist in Terraform as empty
shells, and values are added by hand (architecture §2). The Slack channel
stays outside Terraform for the same reason (access matrix §4). State is
still treated as sensitive, because it lists every resource and identity.
It lives in the versioned `osp-terraform-state` bucket, readable only by
the plan and apply identities and the author.

## 4. Audit logging

| Log | Default | Our setting | Retention | Cost |
|---|---|---|---|---|
| Admin Activity (who changed IAM, created resources, changed config) | Always on; can't be disabled | — | 400 days | Free |
| BigQuery Data Access (who ran which query) | On by default | — | 30 days (`_Default` bucket) | Free; doesn't count toward the logging allotment |
| Secret Manager Data Access (who read a secret) | Off | **On, prod only** (`DATA_READ`) | 30 days | A few entries a day; within the free 50 GiB |
| Other services' Data Access (GCS object reads, Cloud Run) | Off | Off | — | Would add volume without answering a question we have |
| GitHub | Account security log for the author and the bot | — | GitHub's default | Free |

**When someone looks at them:**
- During any SEV1 (RUNBOOK §3.4 step 3, §3.5 step 5).
- At each milestone review: a quick check of Admin Activity for IAM
  changes not made by Terraform or the author, in both projects.
- Drift between IAM and the access matrix is caught by `terraform plan`
  and the B11 matrix-diff check, not by reading logs.

## 5. Supply chain

The parts of the pipeline we didn't write:

- **Python dependencies** are locked in `uv.lock` with hashes. Upgrades are
  PRs, never ad-hoc.
- **GitHub Actions** are pinned to a full commit SHA, not a tag, because a
  tag can be moved to point at different code.
- **pre-commit hooks** are pinned to exact revisions.
- **gitleaks** runs in pre-commit and in CI (DECISIONS §5).
- **`pull_request_target` is banned** (access matrix §6).
- **Dependabot alerts and secret-scanning push protection** are turned on
  in the repo settings (author action; see §6).

## 6. Reporting and disclosure

The repo is public, so anyone may find a problem.

- **Reporting:** a root-level `SECURITY.md` asks reporters to use GitHub's
  **private vulnerability reporting** rather than a public issue. The
  author turns that on in the repo settings (`docs/author_setup.md` §1.4).
- **Response:** the author aims to acknowledge within 7 days. There's no
  SLA; this is a solo project.
- **Disclosure:**
  - Every security incident gets a blameless RUNBOOK Part 2 entry. That
    file is public, so an entry leaves out live secrets, the reporter's
    identity unless they want credit, and actor logins.
  - A vulnerability in our code is fixed first, then described in a GitHub
    Security Advisory on the repo.
  - Anything that affects someone else (GitHub, GH Archive, a dependency)
    is reported privately to them first.
- **There's no one else to notify.** The project has no users' data, and
  the dashboard has no accounts.

## 7. Review date

Review alongside ADR 0002 at cutover, and then yearly. Also review when a
new credential is added, or after any SEV1.

## 8. Change log

| Date | Change |
|---|---|
| 2026-11-18 | Initial version (A12). Data classes, personal data posture, untrusted free text, credential inventory and rotation, dashboard-key policy (reconciles DECISIONS §5), language-lookup token decision (contract §8), audit logging, supply chain, reporting and disclosure. |
