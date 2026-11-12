# Author setup checklist

> Accounts, grants and settings that only the author creates. Agents never
> create accounts, touch billing, apply IAM, or change repo settings
> ([ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md)).
> Work top to bottom; each part has a "done when" check.
>
> - Commands marked **(Cloud Shell)** run in the Cloud Console's Cloud
>   Shell as the author, **never on the agent's machine**.
> - Commands marked **(agent machine)** run in a terminal on the machine
>   where the agent works.
>
> Placeholders: `<yyyy>` is the year in the project ID, `<bot-email>` is
> the bot Google account's address, `<bot-github>` is the bot's GitHub
> username.

---

## Part 1 — GitHub (do now, before the bot exists)

### 1.1 Branch rules (GitHub UI, as yourself)
1. **Settings → Rules → `protect-main` → edit:**
   - Turn on **Require a pull request before merging → Required
     approvals: 1**, and **Require review from Code Owners**.
   - Under **Bypass list**, add the **Repository admin** role, set to "For
     pull requests only". You (admin) can still merge your own PRs; the
     bot (Write) can't merge anything into `main`.
2. **Settings → Rules → New branch ruleset `protect-build-agentic`**,
   targeting branch `build/agentic`:
   - Require a pull request before merging (0 approvals for now).
   - Block force pushes. Restrict deletions.
   - **Bypass list: none.**
   - Required status checks and code-owner review get added with backlog
     B11. The agent will tell you exactly which.

### 1.2 Bot Google account
1. Create a new Google account used only by the build agent, e.g.
   `osp-build-agent-<something>@gmail.com`.
2. Turn on 2-step verification. Keep the password in your password
   manager; the agent never sees it.

### 1.3 Bot GitHub account
1. Sign up for a GitHub account with `<bot-email>`. Turn on 2FA.
2. Invite it to `robertharmon/oss-pulse` as a collaborator with **Write**
   (Settings → Collaborators). Not Maintain, not Admin.
3. Signed in as the bot, create a **classic personal access token** with
   scopes **`repo`** and **`workflow`** only, expiring in 90 days.
   - Fine-grained tokens can't act on a personal-account repo where the
     bot is only a collaborator.
   - The classic token's reach is still limited by the bot's Write role,
     and the bot has access to no other repos.
4. **(agent machine)** Remove *your* GitHub credentials, then log in as
   the bot. Your login lives in two places, so clear both:
   ```
   gh auth logout --hostname github.com
   cmdkey /list | findstr github                      # find stored git credentials
   cmdkey /delete:git:https://github.com              # remove each one listed
   gh auth login --with-token < token.txt             # then delete token.txt
   gh auth setup-git                                  # git now pushes via the bot's gh login
   ```
5. Answer `QUESTIONS.md` Q1 (commit attribution) before the agent's first
   bot push.

**Done when:**
- `gh auth status` shows `<bot-github>`.
- `gh api repos/robertharmon/oss-pulse --jq .permissions.admin` prints
  `false`.
- `cmdkey /list | findstr github` shows nothing of yours.
- A test PR the bot opens into `main` can't be merged by the bot.

---

## Part 2 — Dev project (before milestone 2's BigQuery work)

### 2.1 Project, billing and quota (Console)
1. Create project `oss-pulse-dev-<yyyy>`. Link your billing account.
2. **Pub/Sub topic first:** enable the Pub/Sub API and create topic
   `osp-budget-dev`.
3. **Billing → Budgets & alerts → new budget**, scoped to this project:
   - Amount: $2/month.
   - Email alerts at 50% ($1) and 100% ($2).
   - Under "Manage notifications", connect topic `osp-budget-dev`.
4. **IAM & Admin → Quotas**, filter "BigQuery API" → **Query usage per
   day** → 10 GB (10,240 MiB).

### 2.2 Agent identity, bucket (Cloud Shell)
```
PROJECT=oss-pulse-dev-<yyyy>
gcloud services enable bigquery.googleapis.com storage.googleapis.com \
  iamcredentials.googleapis.com --project=$PROJECT

gcloud iam service-accounts create osp-builder-dev --project=$PROJECT \
  --display-name="oss-pulse build agent (dev only)"
SA=osp-builder-dev@$PROJECT.iam.gserviceaccount.com

# What the agent can do (dev only): build datasets/tables and run queries.
gcloud projects add-iam-policy-binding $PROJECT \
  --member=serviceAccount:$SA --role=roles/bigquery.dataEditor
gcloud projects add-iam-policy-binding $PROJECT \
  --member=serviceAccount:$SA --role=roles/bigquery.jobUser

# The dev bucket, with 7-day auto-delete, and the agent's access to it.
gcloud storage buckets create gs://osp-raw-events-dev --project=$PROJECT \
  --location=us-central1 --uniform-bucket-level-access
cat > /tmp/lifecycle.json <<'JSON'
{"rule": [{"action": {"type": "Delete"}, "condition": {"age": 7}}]}
JSON
gcloud storage buckets update gs://osp-raw-events-dev --lifecycle-file=/tmp/lifecycle.json
gcloud storage buckets add-iam-policy-binding gs://osp-raw-events-dev \
  --member=serviceAccount:$SA --role=roles/storage.objectUser

# The bot's only power: minting short-lived tokens for that service account.
gcloud iam service-accounts add-iam-policy-binding $SA --project=$PROJECT \
  --member=user:<bot-email> --role=roles/iam.serviceAccountTokenCreator
```
- **Bucket names are global.** If `osp-raw-events-dev` is taken, pick a
  suffixed name and tell the agent; it updates DECISIONS §4 and the access
  matrix.
- **If the agent later hits a "quota project" or `serviceusage`
  permission error,** also grant the service account
  `roles/serviceusage.serviceUsageConsumer`. The agent will say so in
  `QUESTIONS.md`.

### 2.3 Kill switch (after the agent delivers the function, backlog C9)
The agent writes the function and a deploy script. You deploy it from
Cloud Shell, because it needs billing permissions the agent must never
hold.
- It starts in **simulate mode** (logs only).
- Run the drill, then switch it live.
- Note: Google's design unlinks billing on the project the function runs
  in, so it also shuts itself off. That's expected.

### 2.4 Agent's machine
1. Install the Google Cloud CLI.
2. **(agent machine)** Log in as the **bot**, never as yourself, and
   route every call through the service account:
   ```
   gcloud auth login <bot-email>
   gcloud config set project oss-pulse-dev-<yyyy>
   gcloud config set auth/impersonate_service_account \
     osp-builder-dev@oss-pulse-dev-<yyyy>.iam.gserviceaccount.com
   gcloud auth application-default login \
     --impersonate-service-account=osp-builder-dev@oss-pulse-dev-<yyyy>.iam.gserviceaccount.com
   ```
3. Confirm your own account isn't present: `gcloud auth list` shows only
   `<bot-email>`.

**Done when** (agent machine):
- `bq query --use_legacy_sql=false 'select 1'` succeeds. If `bq` ignores
  the impersonation setting and fails with permission denied, the agent
  falls back to the Python client (which uses the impersonated
  application-default login) and records that in the cutover runbook.
- `gcloud billing projects describe oss-pulse-dev-<yyyy>` fails with a
  permission error.

---

## Part 3 — Prod project (at cutover)

Prod setup follows `docs/cutover_runbook.md`, written by the agent near the
end of the build. It mirrors Part 2 (budget $5, quota, kill switch), with
**no grants to the bot at all**, plus the GitHub Environments
(`prod-plan`, `prod-apply`, `prod-deploy`) with you as required reviewer.
You run it from your own login, in a session where the agent reads the
output but holds no prod credentials.

---

## Change log

| Date | Change |
|---|---|
| 2026-11-11 | Initial version, per ADR 0002. |
| 2026-11-11 | Review fixes: branch rules moved to Part 1 (`main` requires approval, `build/agentic` protected now); classic token instead of fine-grained; clear Windows Credential Manager; agent SA gets `dataEditor` + `jobUser`; dev bucket with 7-day lifecycle; Pub/Sub topic created before the budget; `gcloud` impersonation configured. |
