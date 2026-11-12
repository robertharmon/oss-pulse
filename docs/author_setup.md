# Author setup checklist

> Accounts and grants that only the author creates. Agents never create
> accounts, touch billing, or apply IAM ([ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md)).
> Work top to bottom; each part has a "done when" check. Commands marked
> **(Cloud Shell)** run in the Cloud Console's Cloud Shell as the author,
> **never on the agent's machine**.
>
> Placeholders: `<yyyy>` is the year in the project ID, `<bot-email>` is
> the bot Google account's address, `<bot-github>` is the bot's GitHub
> username.

---

## Part 1 — Agent identities (before milestone 2)

### 1.1 Bot Google account
1. Create a new Google account used only by the build agent, e.g.
   `osp-build-agent-<something>@gmail.com`.
2. Turn on 2-step verification. Keep the password in your password
   manager. The agent never sees it.

### 1.2 Bot GitHub account
1. Sign up for a GitHub account with `<bot-email>`. Turn on 2FA.
2. Invite it to `robertharmon/oss-pulse` as a collaborator with **Write**
   (Settings → Collaborators). Not Maintain, not Admin.
3. Signed in as the bot, create a **fine-grained personal access token**:
   - Repository access: only `robertharmon/oss-pulse`.
   - Permissions:
     - Contents: read/write.
     - Pull requests: read/write.
     - Workflows: read/write (needed to add CI files; CODEOWNERS review
       guards changes to them).
     - Metadata: read.
   - Nothing else. Specifically, no Administration and no Secrets.
   - Expiry: 90 days.
4. Hand the token to the agent's machine **by hand**:
   ```
   gh auth logout --hostname github.com          # removes YOUR login
   gh auth login --with-token < token.txt         # then delete token.txt
   gh auth status                                 # should show <bot-github>
   ```

**Done when:** `gh auth status` on the agent's machine shows the bot,
and `gh api repos/robertharmon/oss-pulse --jq .permissions` shows
`"admin": false`.

**Open question before this step:** how commits are attributed once the
bot pushes. See `QUESTIONS.md` Q1.

### 1.3 Branch rules for `build/agentic` (as yourself, in the GitHub UI)
These land together with backlog B11, once the CI checks exist to require.
The agent will prepare the exact ruleset JSON and the `CODEOWNERS` file:
- A ruleset targeting `build/agentic`: require a PR, require status
  checks, block force-pushes and deletion, **no bypass for the bot**.
- "Require review from Code Owners" for the paths in `CODEOWNERS`.

---

## Part 2 — Dev project (before milestone 2's BigQuery work)

### 2.1 Project and billing (Console)
1. Create project `oss-pulse-dev-<yyyy>`. Link your billing account.
2. Billing → Budgets & alerts → new budget scoped to this project:
   $2/month, email alerts at 50% ($1) and 100% ($2). Under "Manage
   notifications", connect a Pub/Sub topic `osp-budget-dev` (used by the
   kill switch in 2.3).
3. IAM & Admin → Quotas → filter "BigQuery API" → **Query usage per day**
   → set to 10 GB (10,240 MiB).

### 2.2 Agent service account (Cloud Shell)
```
PROJECT=oss-pulse-dev-<yyyy>
gcloud services enable bigquery.googleapis.com storage.googleapis.com \
  iamcredentials.googleapis.com --project=$PROJECT
gcloud iam service-accounts create osp-builder-dev --project=$PROJECT \
  --display-name="oss-pulse build agent (dev only)"
SA=osp-builder-dev@$PROJECT.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT \
  --member=serviceAccount:$SA --role=roles/bigquery.user
gcloud iam service-accounts add-iam-policy-binding $SA --project=$PROJECT \
  --member=user:<bot-email> --role=roles/iam.serviceAccountTokenCreator
```
- The bot gets **no** project role. It can only mint tokens for this one
  service account.
- If the agent later hits a "quota project" or `serviceusage` permission
  error, also grant the service account
  `roles/serviceusage.serviceUsageConsumer`. The agent will say so in
  `QUESTIONS.md`.
- The dev bucket and its grant come with Terraform (C5). The agent writes
  them, and you apply the IAM part.

### 2.3 Kill switch (after the agent delivers the function, backlog C9)
The agent writes the function and a deploy script. You deploy it from
Cloud Shell, because it needs billing permissions the agent must never
hold. It starts in **simulate mode** (logs only). Run the drill, then
switch it live.

### 2.4 Agent's machine
1. Install the Google Cloud CLI.
2. Log in as the **bot**, never as yourself:
   ```
   gcloud auth login <bot-email>
   gcloud auth application-default login \
     --impersonate-service-account=osp-builder-dev@oss-pulse-dev-<yyyy>.iam.gserviceaccount.com
   gcloud config set project oss-pulse-dev-<yyyy>
   ```
3. Confirm your own account isn't present: `gcloud auth list` should show
   only `<bot-email>`.

**Done when:** as the bot, `bq query --use_legacy_sql=false 'select 1'`
succeeds in dev, and `gcloud billing projects describe
oss-pulse-dev-<yyyy>` fails with a permission error.

---

## Part 3 — Prod project (at cutover)

Prod setup follows `docs/cutover_runbook.md`, written by the agent near the
end of the build. It mirrors Part 2 (budget $5, quota, kill switch), with
no grants to the bot at all. You run it from your own login, in a session
where the agent reads the output but holds no prod credentials.

---

## Change log

| Date | Change |
|---|---|
| 2026-11-11 | Initial version, per ADR 0002. |
