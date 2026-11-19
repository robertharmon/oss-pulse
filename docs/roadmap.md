# oss-pulse — Roadmap

> From here to a finished v1: seven milestones, what each one delivers,
> how we know it's done, and what each needs from the author.
>
> **Status:** approved by the author 2026-11-18 (backlog A10), including
> the decisions in §4. **This is a tracker:** each item carries a status marker
> (`[ ]` open, `[~]` in progress, `[x]` done, `[-]` skipped). Items that
> came from `FOUNDATION_BACKLOG.md` keep their IDs (A–D) and are ticked in
> both places until the backlog is archived.
>
> How the work is done is in [`ways_of_working.md`](ways_of_working.md);
> the operating model is [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md).

---

## 1. Where we're going

### 1.1 v1 is done when

1. **All four charts are live** on Streamlit Community Cloud, reading
   prod marts that cover at least 30 days of events. (The history comes
   from a backfill run during the cutover, before the clock in point 2
   starts.)
2. **Prod has run 14 days in a row with no manual intervention.** Any
   unplanned replay, re-run or fix counts as intervention. Only scheduled
   drills don't.
3. **One full calendar month's invoice is $0.00–0.50** for both projects
   together, in line with [`cost_model.md`](cost_model.md).
4. **Every gate is green on `main`,** and every failure-mode ID in the
   contract has a test.
5. **The runbook has been exercised:** at least the D5 drill entry, plus
   any real incidents.
6. **The README works for a stranger.** A reviewer subagent given only the
   README can answer five set questions: what the project does, which
   questions it answers, where the live dashboard is, how data gets from
   GH Archive to a chart, and how correctness is checked.

So v1 lands at the end of the first full calendar month after the cutover.
After that, the project is in maintenance: scheduled reviews (§5), fixes
through PRs into `main`, and optional extras (§6).

### 1.2 When `build/agentic` merges into `main`

`main` stays frozen at `baseline-pre-agentic` until the build is done
(ADR 0002 §4). Prod, though, can only be deployed from `main`: the
`prod-apply` and `prod-deploy` GitHub Environments only accept `main`
(access matrix §2). So **the merge comes before the cutover**, as the
author confirmed on 2026-11-18:

1. The build is **code-complete, and verified as far as dev allows** (end
   of M7). Dev has no Cloud Run, Scheduler, Secret Manager or alerting
   (access matrix §3), so those parts are verified only by `terraform
   validate`, mock-provider tests and review until the cutover. §2 marks
   each done-when that moves to the cutover.
2. **The GitHub Environments exist first.** The author creates
   `prod-plan`, `prod-apply` and `prod-deploy` with their protection rules
   (author_setup Part 3) **before** the merge. Otherwise the first workflow
   that names them would create them unprotected.
3. The author reviews the whole range and merges `build/agentic` into
   `main` with "Rebase and merge".
4. The author runs the cutover from `main` (`docs/cutover_runbook.md`).
5. `build/agentic` is retired. From then on, every change is a PR into
   `main` (ways of working §4.1).

**If the cutover goes badly,** the fix is a revert PR, never a reset:
force-pushing `main` is forbidden (DECISIONS §9) and blocked by
`protect-main`. Prod holds nothing yet that can't be torn down and
re-applied.

## 2. Milestones

Each milestone ends with an `m<N>-done` tag and the author's review
(ways of working §4).

**Approval load.** CODEOWNERS covers test fixtures and expected outputs,
dbt `schema.yml` files, tool configs and `terraform/**` (ADR 0002 §3).
So most PRs in M2–M5 need the author's approval, not only the milestone
start. The builder batches them (ways of working §2.2); how fast the
author clears that batch sets the pace of those milestones.

### M1 — Foundation docs

- [x] **A11** cost model, with its decisions applied to the contract,
  access matrix and runbook.
- [x] **A12** security posture (`docs/security.md`).
- [x] **A10** roadmap (this doc) and **A13** ways of working. Approved and
  merged; `CLAUDE.md` points at both.
- [x] **`architecture.md` drift fix.** Done when it matches the current
  decisions:
  - daily dbt from its own Scheduler job; ingest doesn't invoke dbt;
  - retention instead of "keep forever";
  - no Docker or Artifact-Registry-push story (DECISIONS §10);
  - measured file sizes, no `PushEvent`, and retries as the contract
    specifies (FM-03: inside ingest's run; the Scheduler job doesn't retry);
  - the access matrix's corrections to §7;
  - pointers to the data contract, access matrix, runbook, cost model and
    security doc, which all exist now;
  - `raw_ingest_audit` in the diagram;
  - the dashboard key in Streamlit secrets, not Secret Manager.

  It **doesn't** decide whether dbt runs as a Cloud Run service or job:
  the ingest ADR does.
- [x] **Contract additions** (approved 2026-11-18). Done when:
  - contract failure modes have IDs (`FM-01`…) and §3.3's "Cloud Run
    auto-retries 3×" is replaced by the real retry rule;
  - `raw_ingest_audit` has an entry;
  - the reconciliation counts and metamorphic relations are listed as
    testable statements;
  - the author has approved them.
- [x] Backlog housekeeping: no second `ROADMAP.md` copy.

**Needs the author:** approvals only.

### M2 — Scaffolding, verifier tooling, and a working dev project

**Order matters here:** author setup Part 1 → Part 2 (including CI's dev
identity) → kill switch live → anything that queries dev BigQuery.

- [ ] **Author setup Part 1:** branch rules, bot accounts, repo security
  settings, `ci-alerts` environment (author_setup §1.1–1.4).
- [ ] **Author setup Part 2:** dev project, quota, bucket, agent identity
  (C1/C2/C10 for dev), and **CI's dev identity and WIF pool** (§2.5).
- [ ] **C9 kill switch, dev.** The agent writes the function and deploy
  script; the author deploys it and runs the drill. **Live before any
  agent BigQuery work in dev.**
- [x] **B1–B6, B8, B9:** folder skeleton, `.gitignore`, Python and SQL
  toolchains, pre-commit (hooks pinned by SHA), CI jobs (actions pinned by
  SHA), PR template, CODEOWNERS.
- [ ] **B11 verifier tooling.** The checks:
  - red proof against the stubs commit, assertion failures only;
  - no mixed test/non-test commits;
  - failure-mode coverage;
  - executable docs;
  - `dbt build --empty`;
  - contract ↔ `schema.yml` and access matrix ↔ Terraform diffs;
  - retention, soft-delete, cleanup-policy and `full_refresh: false`
    checks (cost model §7);
  - dev datasets without the 7-day expiration (ADR 0002 §1);
  - workflows using `pull_request_target` (access matrix §6);
  - subagent definitions and the lock hook.

  **Done when, for each check:** a drill PR plants a bad input, the check
  goes red, **the check is a required status check** in the
  `build/agentic` ruleset, and the bot's attempt to merge the drill PR is
  refused.
- [ ] **Author: make each check required** in the `protect-build-agentic`
  ruleset as it lands, and add the `.claude/settings.json` deny rules
  from ADR 0002 §2 (agents never edit that file).
- [ ] **Dev spike.** Done when the cost model §9 items that dev can
  measure are measured and written into the cost model:
  - physical vs logical storage, including time travel;
  - what `--empty` and JSON-column reads bill;
  - Zstandard Parquet loads;
  - `REQUIRED` vs nullable pyarrow schema;
  - `insert_overwrite` incremental models.

  (Ingest runtime is measured in M3; Cloud Run runtime and image sizes at
  the cutover.)
- [~] **D1, D2, D4:** (D1 and D4 done; D2 needs dev BigQuery) a hello-world Python module and dbt model pass CI
  against dev; a deliberate lint failure turns CI red, then green.

**Needs the author:** Parts 1–2, deploying the dev kill switch, making
checks required, the settings deny rules, and CODEOWNERS approvals.
**This is the milestone most likely to wait on the author's time.**

### M3 — Ingest

- [x] **Ingest ADR** ([ADR 0003](adr/0003-ingest-and-build-as-cloud-run-jobs.md), accepted 2026-11-18). It decides:
  - the Scheduler minute: files went live at `:05:03`–`:05:04` on every
    hour sampled, so `:05` has no margin, and `:15` is the first
    candidate;
  - the backfill window and its separate path (cost model §5.3), sized
    so the cutover backfill gives the 30 days v1 needs;
  - the hour-retry rule, and that ingest writes only with load jobs;
  - whether dbt runs as a Cloud Run service or job.
- [ ] **`s1_gharchive_hour_to_gcs_parquet`,
  `s2_gharchive_gcs_parquet_to_bq_raw`.** Built test-first. Done when:
  - padded ↔ unpadded hour conversion is tested for hours 0–9;
  - Parquet is Zstandard, and the schema is `REQUIRED` where the contract
    says so;
  - an hour is written with `WRITE_TRUNCATE`, and reloading the same hour
    leaves the table unchanged;
  - load and query jobs carry the `component` label (cost model §10);
  - the local runtime and memory for one hour are recorded.
- [ ] **Great Expectations, in ingest** (§4.1). The suite *is* ingest's
  batch validation: one implementation, not a second copy of the same
  rules. Each expectation maps to a failure-mode ID.
- [ ] **`raw_ingest_audit` and the missing-hour rule.** The first and
  second 404s log `WARNING`, the third logs `ERROR` (RUNBOOK §3.2). Line
  count = rows loaded, from load-job statistics.
- [ ] **Red-team round** (ways of working §4).

**Needs the author:** the ADR, expected outputs, CODEOWNERS approvals.

### M4 — dbt models

- [ ] **Staging, core and dimension models.** Built test-first with
  hand-computed unit tests. Done when they use `insert_overwrite` and
  `contract: enforced`, follow contract §1's retention and
  `full_refresh: false`, apply `actor_suppressions`, and label their jobs
  (cost model §10).
- [ ] **Language lookup** (§4.2). An ADR first, then the build.
- [ ] **Four marts.** Each matches its contract entry, checked by the
  spec-reconstructor's structured diff. Snapshot marts are partitioned on
  `as_of_date` and carry `repo_name`.
- [ ] **Reconciliation and metamorphic tests.** Every count in the
  contract balances in a dbt test that also runs in prod. The reload,
  time-shift, actor-shuffle and equal-activity relations hold.
- [ ] **Red-team round.**

**Needs the author:** expected outputs, the language ADR, CODEOWNERS
approvals.

### M5 — Terraform

- [ ] **C3–C5 in code.** Every prod resource:
  - buckets with lifecycle rules and soft delete off;
  - datasets with expiration;
  - service accounts and grants exactly as the access matrix says;
  - empty secret shells;
  - the two Cloud Run jobs, two Scheduler jobs (plus the language lookup if
    its ADR needs one), the alert policy;
  - the Artifact Registry repo with its cleanup policy;
  - labels (cost model §10).

  Done when `terraform test` (mock providers), `validate`, `fmt` and the
  access-matrix diff are green. **Moves to the cutover:** C3's
  `terraform init` against the state bucket, and C5's "apply from a clean
  clone".
- [ ] **C6 Terraform CI.** Before the merge: `fmt`, `validate` and
  `terraform test` on every PR. `plan` and `apply` against prod need prod
  to exist, so **they first run at the cutover**, through `prod-plan` and
  `prod-apply`.

**Needs the author:** CODEOWNERS approvals (all of `terraform/**`).

### M6 — Dashboard

- [ ] **`dashboard/app.py`.** Done when:
  - four charts each load their mart once and cache it (contract §6.1);
  - a missing mart shows "data unavailable" instead of a stack trace;
  - the app is tested with Streamlit `AppTest` against fixtures.
- [ ] **Query checks.** Every dashboard query dry-runs against dev
  BigQuery in CI, and none uses `CURRENT_DATE()`.

**Needs the author:** nothing until the cutover, when the Streamlit app
and its key are created.

### M7 — Deploy, operations, cutover

- [ ] **Deploy workflow.** Deploys both Cloud Run jobs from `main` through
  `prod-deploy`, with `--source` (DECISIONS §10). First runs at the
  cutover.
- [ ] **Alerting.** The prod log-based alert policy to the hand-made Slack
  channel (C7, C8). CI → Slack can be proven before the merge through
  `ci-alerts`; prod alerting at the cutover.
- [ ] **Cutover runbook and smoke test.** `docs/cutover_runbook.md` with
  staged steps: Environments check → Terraform → one manual ingest →
  backfill → dbt → schedule → alerts → dashboard. Includes C10's check
  that the bot gets 403 on every prod resource, and that the Compute
  Engine default account doesn't hold `editor`. Its commands pass the
  executable-docs syntax check.
- [ ] **Docs polish.** The README rewritten for a portfolio reader (v1
  point 6); the `architecture.md` §4 trace updated with real numbers.
- [ ] **Final red-team round** across the whole pipeline.
- [ ] **Merge and cutover** (§1.2), done by the author. D3 and D5 happen
  here.
- [ ] **v1** (§1.1).

## 3. Schedule

Targets, not promises. The author's setup and approval time gates M2–M5
and the cutover. The rest is agent work that moves quickly once its gates
exist.

| Window | Milestones | Gate |
|---|---|---|
| By 2026-12-18 | M1 done; M2 well underway | Author setup Parts 1–2 |
| By 2027-01-17 | M2, M3, M4 | Expected outputs and CODEOWNERS approvals |
| By 2027-02-16 | M5, M6, M7 code-complete; merge and cutover | Author's cutover session |
| End of the first full calendar month after the cutover (≈ 2027-03-31) | v1 | Prod runs clean; the month's invoice |

If a window slips, the order doesn't change: no ingest code before M2's
gates are required checks, and no cutover before every gate is green.

## 4. Decisions (approved 2026-11-18)

### 4.1 Raw-layer data quality: keep Great Expectations, in ingest

- **Decision:** a Great Expectations suite validates each hour's batch in
  memory, before it's loaded.
- **It's the only implementation** of those rules. Ingest's own
  "assertions" are the suite, not a second copy, so failure-mode coverage
  maps each rule to one place.
- **Why keep it:** ADR 0001 and the README promise it, and it's a widely
  listed tool, which matters for a portfolio project. Honestly, the same
  rules would also work as plain Python checks.
- **Costs:** no BigQuery cost; a heavier ingest image (a few cents of
  Artifact Registry at most); more memory for the conversion, measured in
  M3.
- **Not chosen:** dropping it (simpler); running it only in CI against
  fixtures (cheaper, but wouldn't check live data).

### 4.2 `primary_language` from GitHub's API

- **Decision:** look up each repo's language from GitHub's API, cache it
  in `dim_repos`, and refresh it weekly. Otherwise both language charts
  are a single "(unknown)" slice.
- **Scope:** every repo that appears in a language-split mart (PRs,
  issues and stars). Narrower scopes would leave stars and issues on
  PR-less repos as "(unknown)" in `mart_time_of_day_activity`.
- **Costs, beyond "free":**
  - a separate small job: the lookup is Python, and can't run inside
    dbt;
  - its own service account and a `secretAccessor` grant;
  - the token from `security.md` §3.2;
  - a schedule: riding the daily dbt Scheduler job, or a third job (the
    last free one, cost model §6);
  - dev tests from recorded responses only, since dev has no Secret
    Manager.
- **Staying under GitHub's 5,000 requests/hour** is designed in the M4
  ADR.

### 4.3 Confirmed

- The v1 definition (§1.1).
- Merging into `main` **before** the cutover (§1.2).
- Optional extras stay out of v1 (§6).

## 5. Scheduled reviews

| Review | When |
|---|---|
| Cost model | By 2027-08-01, before alerting charges can start |
| ADR 0001 (tech stack) | 2027-04-05 |
| ADR 0002, security doc | At the cutover |
| Ways of working | At each milestone review |
| Credential ages (security §3.4) | At each milestone review, then monthly |

## 6. After v1 (optional, not planned)

- **Local Dagster practice** (ADR 0001): a time-boxed, local-only exercise
  running the same pipeline as Dagster assets. No cloud cost.
- **A metric-absence alert** for "ingest never ran" (cost model §8.1):
  about $0.35/month once alerting is billed.
- **Spend cap budgets** on Cloud Run as a second hard cap. Considered at
  ADR 0002's cutover review, not after v1.

## 7. Change log

| Date | Change |
|---|---|
| 2026-11-18 | Initial version (A10). Folds in the A10 inputs from `FOUNDATION_BACKLOG.md`. Revised after independent review: dev CI identity in M2; A12 in M1; B11 checks must be required; v1 criteria made measurable and the date moved to after a full invoice month; merge-before-cutover details (Environments first, revert not reset); done-whens that move to the cutover; approval load; fuller costs for both decisions. §4 decisions approved by the author. |
| 2026-11-18 | Signed off by the author. M1: A10, A13 and the contract additions done; only the `architecture.md` drift fix remains. |
| 2026-11-18 | M1 done (tag `m1-done`). M2: B1–B6, B8, B9, D1, D4 done. |
| 2026-11-18 | M3: ingest ADR done (ADR 0003). M2: C9 kill-switch code done (deploy is the author's). |
