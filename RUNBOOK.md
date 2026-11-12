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
| Cloud Logging alert policy (prod) | Any `ERROR` log from `osp-ingest-prod` or `osp-dbt-prod` (this includes dbt test failures, which exit non-zero) | Slack, through a notification channel created by hand. Its webhook URL is also kept as a record in Secret Manager `osp_slack_webhook_url`; nothing reads it from there. |
| Ingest, missing-hour rule (prod) | An hour is still missing (HTTP 404) after 3 attempts (data contract §3.3) | Same Slack channel |
| GitHub Actions | A workflow fails on `main` or `build/agentic` | Same Slack channel, through GitHub secret `SLACK_WEBHOOK_URL` |
| Google budget alert (dev, prod) | Spend crosses $1 / $2 (dev) or $1 / $5 (prod) | Email to the author. **Notification only. It doesn't stop spending** (DECISIONS §1). |
| Billing kill switch (dev, prod) | Spend crosses the budget ($2 dev, $5 prod) | It **unlinks billing**, so every service in that project stops. You'll find out from the budget email and from everything else failing. See §3.5. |

A missing hour is rare: every hour probed in Nov 2026 was present (data
contract §3.2).
- **First and second 404s** for an hour are logged at `WARNING` (not
  `ERROR`, so they don't page), recorded in `raw_ingest_audit`, and
  retried on the next runs.
- **The third failed attempt** logs at `ERROR`, which alerts. Until then
  the hour isn't a failure, just not published yet. That's how
  DECISIONS §6's "non-2xx raises" applies to an hour GH Archive may still
  be writing.

## 2. Severity levels

| Sev | Meaning | Examples | Response |
|---|---|---|---|
| **SEV1** | Money is being spent unexpectedly, or a credential is exposed | A budget alert fires. A secret is found in a commit or log. An unknown principal appears in IAM. | Drop everything. Contain first (§3.4, §3.5), log after. |
| **SEV2** | The pipeline is down, or data is wrong | Raw data is staler than its 2-hour freshness target (data contract §4.1), so freshness tests fail. A dbt test fails on a mart. Several hours in a row missing. The dashboard shows wrong numbers. | Same day. Fix forward through a PR, then replay the affected hours. |
| **SEV3** | Degraded but self-limiting | One transient 5xx that exhausted retries. A late GH Archive hour. The dashboard is down because Streamlit Community Cloud itself is down. | Next working session. Replay if needed. |
| **SEV4** | Cosmetic or near-miss | A flaky CI job. A docs mismatch found by a verifier. | Fix when convenient. Log only if there's a lesson. |

**Rule of thumb:** if you're unsure between two levels, pick the higher one
and downgrade later.

## 3. Standard procedures

These are the expected responses. Each one is filled in with exact
commands once the component it touches exists. Until then, it records the
*intended* procedure so the build matches it.

### 3.1 Replay one hour

The pipeline is idempotent on hour: re-running an hour **overwrites**
that hour's partition in `raw_gharchive_events` (a load job with
`WRITE_TRUNCATE` aimed at the single hour partition) and its Parquet file
in GCS, instead of appending a duplicate copy.

Example for 05:00 UTC on 2026-11-10. GH Archive's URL uses the
**unpadded** hour; the project's own hour string is **padded**.

1. Confirm the hour exists upstream:
   `curl -sI https://data.gharchive.org/2026-11-10-5.json.gz`.
   A 200 means it's available.
2. Re-trigger the ingest service with body `{"hour": "2026-11-10-05"}`.
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
- If GH Archive still hasn't published it a day later, accept the hour
  as lost (data contract §3.4: "a lost hour is lost"). Lost hours are rare
  now, so **log each one** in Part 2 (per `docs/architecture.md` §6), even
  if it's a one-line SEV3 entry.

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
2. **Update every place the new value is used.** For the Slack webhook
   that's three places, and missing the first silently breaks prod alerts:
   - the Cloud Monitoring **notification channel** (set by hand; nothing
     reads it from Secret Manager),
   - the GitHub Actions secret `SLACK_WEBHOOK_URL`,
   - the record copy in Secret Manager.

   For the dashboard key, it's Streamlit's app secrets.
3. **Check whether the old credential was used.** Look in Cloud Audit
   Logs (GCP), the GitHub security log, or Slack's app logs for activity
   between the leak and the rotation.
4. **Only after the old credential is dead,** scrub history with
   `git filter-repo` if it was committed. On this public repo that means:
   - a force-push to `main`, which DECISIONS §9 and `protect-main`
     otherwise forbid, so use the admin bypass for this one push and note
     it in the incident;
   - asking GitHub Support to purge cached views and pull-request refs
     that still contain the secret.
5. Log it as a SEV1 incident (Part 2).

### 3.5 Unexpected spend, or the kill switch fired

Applies to both projects; each has its own budget and kill switch
(DECISIONS §1).
1. Open Billing → Reports for the project and find the service and SKU.
2. **If the kill switch hasn't fired and spend is still growing,** stop the
   source: pause the Scheduler job (prod only; dev has none), delete the
   runaway resource, or as a last resort unlink billing yourself.
3. **If the kill switch fired,** billing is already unlinked and every
   service in that project is stopped.
   - **Don't re-link until the cause is fixed.**
   - **Then defuse the switch before re-linking.** Budgets track
     month-to-date spend, which is still over the cap, so the next budget
     notification would unlink billing again straight away. Either raise
     the budget amount for the rest of the month, or pause the kill-switch
     function. Wait for the month to roll over before re-arming it.
   - Google warns that resources may be lost when billing is unlinked.
   - **Rebuilt automatically:** data and tables (re-derivable from GH
     Archive), code (in git), and infrastructure (re-apply Terraform, then
     replay hours, §3.1).
   - **Restored by hand:**
     - Terraform state bucket, if lost: re-import or rebuild state.
     - Secret values and the Slack notification channel.
     - The Streamlit dashboard key.
     - The kill switch's own deployment.
   - **Lost for good:** `raw_ingest_audit` history, which can't be
     re-derived.
4. Find the cause, fix it via PR, and add a guard so it can't recur, such
   as a quota, a lifecycle rule or a Terraform constraint.
5. If the cause was agent activity in dev, also review what the bot
   identity did (Cloud Audit Logs) before re-linking.
6. Log it as SEV1.

### 3.6 Dashboard shows "data unavailable"

1. Check that the mart tables exist and are fresh in `osp_analytics_prod`.
2. If the marts are fine, check whether the dashboard identity hit its
   **per-user daily query quota** (access matrix §6). That's the most
   likely cause, and it resets daily. Heavy traffic or a leaked key can
   cause it. If it's a leak, treat it as §3.4.
3. Otherwise, check the Streamlit app's secrets (the `osp-dashboard-prod`
   key). Keys don't expire on their own, but one may have been rotated or
   deleted. The rotation schedule lands in `docs/security.md` (A12).
4. If Streamlit Community Cloud itself is down, it's SEV3. Wait.

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
