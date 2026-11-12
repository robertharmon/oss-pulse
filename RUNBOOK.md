# oss-pulse — Runbook

> What to do when something breaks, and the record of every time it did.
> Part 1 is the playbook (alert routing, severity, standard procedures).
> Part 2 is the incident log, which starts empty and grows with every real
> incident.
>
> Failure modes and their expected handling are defined in
> [`docs/data_contract.md`](docs/data_contract.md) §3.3 and
> [`docs/architecture.md`](docs/architecture.md) §6. This file says what a
> *person* does about them.

---

# Part 1 — Playbook

## 1. Alert routing

There's one on-call person (the author) and one channel. PagerDuty-style
paging is out of scope (DECISIONS §11).

| Source | Fires when | Lands in |
|---|---|---|
| Cloud Logging alert policy (prod) | Any `ERROR` log from `osp-ingest-prod` or `osp-dbt-prod` (this includes dbt test failures, which exit non-zero) | Slack, through the webhook in Secret Manager `osp_slack_webhook_url` |
| Ingest, missing-hour rule (prod) | An hour is still missing (HTTP 404) after 3 attempts (data contract §3.3) | Same Slack channel |
| GitHub Actions | A workflow fails on `main` or `build/agentic` | Same Slack channel, through GitHub secret `SLACK_WEBHOOK_URL` |
| Google budget alert (dev, prod) | Spend crosses $1 / $2 (dev) or $1 / $5 (prod) | Email to the author. **Notification only. It doesn't stop spending** (DECISIONS §1). |
| Billing kill switch (dev, prod) | Spend crosses the budget ($2 dev, $5 prod) | It **unlinks billing**, so every service in that project stops. You'll find out from the budget email and from everything else failing. See §3.5. |

A missing hour is rare: every hour probed in Nov 2026 was present (data
contract §3.2). A first 404 is recorded in `raw_ingest_audit` and retried
on the next runs. It alerts only if the hour is still missing after 3
attempts.

## 2. Severity levels

| Sev | Meaning | Examples | Response |
|---|---|---|---|
| **SEV1** | Money is being spent unexpectedly, or a credential is exposed | A budget alert fires. A secret is found in a commit or log. An unknown principal appears in IAM. | Drop everything. Contain first (§3.4, §3.5), log after. |
| **SEV2** | The pipeline is down, or data is wrong | No successful ingest for 6+ hours. A dbt test fails on a mart. Every hour in a day is missing. The dashboard shows wrong numbers. | Same day. Fix forward through a PR, then replay the affected hours. |
| **SEV3** | Degraded but self-limiting | One transient 5xx that exhausted retries. A late GH Archive hour. The dashboard is down because Streamlit Community Cloud itself is down. | Next working session. Replay if needed. |
| **SEV4** | Cosmetic or near-miss | A flaky CI job. A docs mismatch found by a verifier. | Fix when convenient. Log only if there's a lesson. |

**Rule of thumb:** if you're unsure between two levels, pick the higher one
and downgrade later.

## 3. Standard procedures

These are the expected responses. Each one is filled in with exact
commands once the component it touches exists. Until then, it records the
*intended* procedure so the build matches it.

### 3.1 Replay one hour

The pipeline is idempotent on hour: re-running an hour replaces its data
instead of duplicating it.

1. Confirm the hour exists upstream:
   `curl -sI https://data.gharchive.org/<YYYY-MM-DD-H>.json.gz`.
   A 200 means it's available.
2. Re-trigger the ingest service with body `{"hour": "<YYYY-MM-DD-HH>"}`.
   _(Exact command lands with the ingest service.)_
3. Check that `raw_ingest_audit` shows a new successful run for the hour,
   and that dbt finished green.

### 3.2 Missing hour (GH Archive 404)

Rare. Ingest retries automatically on the next scheduled runs.
- **First, rule out our own bug.** GH Archive URLs use an *unpadded* hour
  (`2026-11-10-5.json.gz`, not `-05`). Check the exact URL ingest
  requested in Cloud Logging, and `curl -sI` it by hand.
- If the alert fires (still missing after 3 attempts), check GH Archive
  for a known outage, then replay the affected hours once they're published
  (§3.1).
- If an hour is still missing after 48 hours, accept it as lost (data
  contract §3.4) and note it in the incident log only if it's part of a
  larger outage.

### 3.3 dbt test failure

1. Read the failing test name in the alert or Cloud Logging.
2. Decide: is the data really wrong, or is the test too strict?
3. Either way, the fix is a PR, never a manual edit in BigQuery:
   - **Data is wrong:** patch the model upstream.
   - **Test is too strict:** relax it, with a reason in the PR.
4. After merge, re-run `dbt build`, and replay hours if raw data was
   affected (§3.1).

Marts stay stale (not wrong) until then. The dashboard shows the last good
build.

### 3.4 Secret leaked

From DECISIONS §5. Order matters.
1. **Rotate first.** Revoke or regenerate the credential at its source:
   Slack for the webhook, GCP for a key, GitHub for a token.
2. Update the new value where it lives: Secret Manager, GitHub Actions
   secrets, or Streamlit secrets.
3. Only after the old credential is dead, scrub history with
   `git filter-repo` if it was committed.
4. Log it as a SEV1 incident (Part 2).

### 3.5 Unexpected spend, or the kill switch fired

Applies to both projects; each has its own budget and kill switch
(DECISIONS §1).
1. Open Billing → Reports for the project and find the service and SKU.
2. **If the kill switch hasn't fired and spend is still growing,** stop the
   source: pause the Scheduler job, delete the runaway resource, or as a
   last resort unlink billing yourself.
3. **If the kill switch fired,** billing is already unlinked and every
   service in that project is stopped.
   - **Don't re-link until the cause is fixed,** or it'll just fire again.
   - Google warns that resources may be lost when billing is unlinked.
     Everything here is re-derivable from GH Archive and git. After
     re-linking, re-apply Terraform and replay hours (§3.1) as needed.
4. Find the cause, fix it via PR, and add a guard so it can't recur, such
   as a quota, a lifecycle rule or a Terraform constraint.
5. If the cause was agent activity in dev, also review what the bot
   identity did (Cloud Audit Logs) before re-linking.
6. Log it as SEV1.

### 3.6 Dashboard shows "data unavailable"

1. Check that the mart tables exist and are fresh in `osp_analytics_prod`.
2. If the marts are fine, check the Streamlit app's secrets (the
   `osp-dashboard-prod` key), and rotate if expired (`docs/security.md`).
3. If Streamlit Community Cloud itself is down, it's SEV3. Wait.

## 4. Incident template

Copy this into Part 2, newest at the top. Write it within a day while it's
fresh. Blameless: describe what happened and why the system allowed it,
not who slipped.

```markdown
## YYYY-MM-DD — <short title>  (SEVn)

**Status:** resolved | monitoring | open
**Detected:** <time UTC>, by <alert / verifier / noticed by hand>
**Resolved:** <time UTC>  (duration: <h:mm>)

### Impact
What broke, for how long, and what a dashboard viewer would have seen.
Which hours or tables were affected.

### Timeline (UTC)
- HH:MM — first signal
- HH:MM — …
- HH:MM — resolved

### Root cause
The actual cause, not the symptom. Why did the system allow it?

### What went well / what didn't
- …

### Follow-ups
- [ ] <action> — tracked in <PR / OPEN_LOOPS / backlog item>
```

---

# Part 2 — Incident log

_(No incidents yet. The first entry will be the synthetic drill from
backlog D5.)_
