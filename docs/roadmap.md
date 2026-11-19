# oss-pulse — Roadmap

> From here to a finished v1: seven milestones, what each one delivers,
> how we know it's done, and what each needs from the author. Covers the
> rest of the foundation backlog and the build that follows it.
>
> **Status:** proposed 2026-11-18 for the author's approval (backlog A10).
> Until `FOUNDATION_BACKLOG.md` is empty, the backlog is the tracker for
> its own items and this doc sequences them. After that, this doc is the
> only tracker.
>
> How the work is done is in [`ways_of_working.md`](ways_of_working.md);
> the operating model is [ADR 0002](adr/0002-agentic-build-out-and-isolated-dev.md).

---

## 1. Where we're going

### 1.1 v1 is done when

1. **All four charts are live** on Streamlit Community Cloud, reading
   prod marts built from real data, with at least 30 days of history.
2. **Prod has run 14 days in a row with no manual fixes.** Planned
   replays and drills don't count against this.
3. **A full month's bill is $0.00–0.50,** in line with
   [`cost_model.md`](cost_model.md).
4. **Every gate is green on `main`,** and every failure mode in the
   contract has a test.
5. **The runbook has been exercised:** at least the D5 drill entry, plus
   any real incidents.
6. **A stranger can follow the README** to understand the project, see
   the dashboard, and find how each part was built and checked.

After v1, the project is in maintenance: scheduled reviews (§5), fixes
through normal PRs, and optional extras (§6).

### 1.2 When `build/agentic` merges into `main`

`main` stays frozen at `baseline-pre-agentic` until the build is done
(ADR 0002 §4). Prod, though, can only be deployed from `main`: the
`prod-apply` and `prod-deploy` GitHub Environments only accept `main`
(access matrix §2). So **the merge has to come before the cutover, not
after it:**

1. The build is **code-complete and verified in dev** (end of milestone 7).
2. The author reviews the whole range and merges `build/agentic` into
   `main` with "Rebase and merge".
3. The author runs the cutover from `main`
   (`docs/cutover_runbook.md`).
4. `build/agentic` is retired. From then on, fixes are normal PRs into
   `main` (DECISIONS §3, §9).

If the cutover goes badly, `main` can be reset to the baseline tag, and
prod has nothing in it yet worth keeping.

## 2. Milestones

Each milestone ends with an `m<N>-done` tag and the author's review
(ways of working §4). Backlog IDs (A–D) are kept where an item came from
the foundation backlog.

### M1 — Foundation docs

Finish writing down what the build is checked against.

| Item | Done when |
|---|---|
| A10 roadmap (this doc), A13 ways of working | Author approved; merged |
| `architecture.md` drift fix | Matches the current decisions: daily dbt via its own Scheduler job, retention instead of "keep forever", no Docker/Artifact-Registry-push story (DECISIONS §10), measured file sizes, no `PushEvent`, retries on the Scheduler job, access corrections from the access matrix, dbt as a Cloud Run service |
| Contract additions | Contract §3.3 failure modes get IDs (`FM-01`…); `raw_ingest_audit` has an entry; reconciliation counts and metamorphic relations are listed as testable statements. Author approved. |
| Backlog housekeeping | The end-of-backlog step that copies this doc to a second `ROADMAP.md` is removed (one roadmap, here) |

**Needs the author:** approvals only.

### M2 — Scaffolding, verifier tooling, and a working dev project

Every gate and check exists before there's code for them to protect.

| Item | Done when |
|---|---|
| B1–B6, B8, B9 | Folder skeleton, `.gitignore`, Python and SQL toolchains, pre-commit, CI jobs, PR template, CODEOWNERS. Each passes on a trivial input and rejects a planted bad one. |
| B11 verifier tooling | Red-proof check, tests-untouched check, failure-mode coverage script, executable-docs runner, `dbt build --empty` job, contract ↔ `schema.yml` and access matrix ↔ Terraform diffs, retention and `full_refresh` checks (cost model §7), subagent definitions, lock hook. **Each one rejects a planted bad input in a drill PR.** |
| Author setup, Part 1 and Part 2 | Branch rules (§1.1), bot accounts (§1.2–1.3), repo security settings (§1.4), dev project, quota, bucket and agent identity (§2.1–2.2, backlog C1/C2/C10 for dev) |
| C9 kill switch, dev | Agent writes the function and deploy script; author deploys it and runs the drill. **Live before any agent BigQuery work in dev.** |
| Dev spike | Measures the open items in cost model §9 (physical vs logical storage, `--empty` billing, JSON column billing, Zstandard Parquet loads, `REQUIRED` vs nullable pyarrow schema, ingest runtime, image sizes) and confirms `insert_overwrite` incremental models run. Results go into the cost model. |
| D1, D2, D4 | Hello-world Python module and dbt model pass CI against dev; a deliberate lint failure turns CI red, then green. |

**Needs the author:** `docs/author_setup.md` Parts 1–2, deploying the
dev kill switch, and approving the check-defining files (CODEOWNERS).
**This is the milestone most likely to wait on the author's time.**

### M3 — Ingest

| Item | Done when |
|---|---|
| Ingest ADR | Decides the Scheduler minute (files went live at `:05:03`–`:05:04` on every hour sampled, so `:05` has no margin; `:15` is the first candidate), the backfill window and its separate path (cost model §5.3), the hour-retry rule, and that ingest writes only with load jobs. Author approved. |
| `s1_gharchive_hour_to_gcs_parquet`, `s2_gharchive_gcs_parquet_to_bq_raw` | Built test-first. Padded ↔ unpadded hour conversion tested for hours 0–9; Zstandard Parquet; `REQUIRED` schema; `WRITE_TRUNCATE` on the hour; reload-the-same-hour leaves the table unchanged |
| `raw_ingest_audit` and the missing-hour rule | First and second 404 log `WARNING`, the third logs `ERROR` (RUNBOOK §3.2); line count = rows loaded, from load-job statistics |
| Raw-layer data quality | Per the decision in §4.1 |
| Red-team round | Ends after 3 failed break attempts in a row |

**Needs the author:** approving the ADR and the hand-computed expected
outputs at milestone start.

### M4 — dbt models

| Item | Done when |
|---|---|
| Staging, core and dimension models | Built test-first with hand-computed `unit_tests`; `insert_overwrite`; `contract: enforced`; retention and `full_refresh: false` as in contract §1 |
| Language source | Per the decision in §4.2 |
| Four marts | Each matches its contract entry, checked by spec reconstruction; snapshot marts partitioned on `as_of_date` |
| Reconciliation and metamorphic tests | Every count in the contract balances in a dbt test that also runs in prod; reload, time-shift, actor-shuffle and equal-activity relations hold |
| Red-team round | As M3 |

**Needs the author:** approving expected outputs at milestone start.

### M5 — Terraform

| Item | Done when |
|---|---|
| C3–C5 | State bucket design, module layout, and every prod resource in code: buckets with lifecycle and soft delete off, datasets with expiration, service accounts and grants exactly as the access matrix says, empty secret shells, Cloud Run services, two Scheduler jobs, the alert policy, the Artifact Registry repo with its cleanup policy, labels (cost model §10) |
| Tests | `terraform test` with mock providers; the access-matrix diff is green; `terraform validate` and `fmt` in CI |
| C6 Terraform CI | Plan on PRs; apply only from `prod-apply` (it first runs for real at cutover) |

**Needs the author:** approving the Terraform (it's CODEOWNERS-protected).

### M6 — Dashboard

| Item | Done when |
|---|---|
| `dashboard/app.py` | Four charts, each loading its mart once and caching (contract §6.1); "data unavailable" instead of a stack trace; tested with Streamlit `AppTest` |
| Query checks | Every dashboard query dry-runs against dev BigQuery in CI; none uses `CURRENT_DATE()` |

**Needs the author:** nothing until cutover (the Streamlit app and its key
are created then).

### M7 — Deploy, operations, cutover

| Item | Done when |
|---|---|
| Deploy workflow | Deploys both services from `main` through `prod-deploy` with `--source` (DECISIONS §10) |
| Alerting | Prod log-based alert policy to the hand-made Slack channel; C7 secrets wired; C8 CI → Slack proven |
| Cutover runbook and smoke test | `docs/cutover_runbook.md` with staged steps (Terraform → one manual ingest → dbt → schedule → alerts → dashboard); its commands pass the executable-docs syntax check |
| Docs polish | README rewritten for a portfolio reader; `architecture.md` §4 trace updated with real numbers |
| Final red-team round | Across the whole pipeline |
| **Merge and cutover** (§1.2) | Author merges into `main`, creates prod (author_setup Part 3), and runs the cutover with the agent reading output. D3 and D5 happen here. |
| v1 | The §1.1 criteria hold |

## 3. Schedule

Targets, not promises. The author's setup time gates M2 and M7; the rest
is agent work that can move quickly once its gates exist.

| Window | Milestones | Gate |
|---|---|---|
| By 2026-12-18 | M1 done; M2 well underway | Author setup Part 1 and Part 2 |
| By 2027-01-17 | M2, M3, M4 | Author approves expected outputs |
| By 2027-02-16 | M5, M6, M7 code-complete; merge and cutover | Author's cutover session |
| +14 days after cutover | v1 | Prod runs clean |

If a window slips, the order doesn't change: no ingest code before M2's
gates exist, and no cutover before every gate is green.

## 4. Decisions this roadmap needs

### 4.1 Raw-layer data quality: Great Expectations or not?

ADR 0001 and the README promise Great Expectations on the raw layer.
Since then, the contract has moved most raw checks into ingest's own
fail-fast assertions and the `REQUIRED` schema.

- **(a) Recommended: keep Great Expectations, in ingest, on the in-memory
  batch** before it's loaded. A small suite mirroring contract §4.1
  (types, accepted values, row counts, timestamp window). No BigQuery
  cost. Keeps ADR 0001's promise, and adds a commonly listed tool to the
  portfolio. Cost: a heavy dependency (bigger ingest image, a few cents of
  Artifact Registry storage at most).
- **(b) Drop it,** and amend ADR 0001 and the README. Ingest assertions plus
  dbt tests already cover the same rules. Simpler and smaller.

### 4.2 Where `primary_language` comes from (contract §5.7)

Two of the four charts are split by language.

- **(a) Recommended: look it up from GitHub's API,** only for repos that
  matter to the charts (repos with a PR opened or merged in the window),
  cached in `dim_repos` and refreshed weekly. Uses the no-permission token
  from `security.md` §3.2. Exact design in an M4 ADR, including staying
  under GitHub's 5,000 requests an hour.
- **(b) Leave it NULL.** Both language charts show a single "(unknown)"
  slice, which makes them close to pointless.

### 4.3 Confirmations

- The v1 definition (§1.1).
- Merging into `main` **before** the cutover (§1.2).
- Optional extras stay out of v1 (§6).

## 5. Scheduled reviews

| Review | When |
|---|---|
| Cost model | By 2027-08-01, before alerting charges can start |
| ADR 0001 (tech stack) | 2027-04-05 |
| ADR 0002, security doc | At cutover |
| Ways of working | At each milestone review |

## 6. After v1 (optional, not planned)

- **Local Dagster practice** (ADR 0001): a time-boxed, local-only exercise
  running the same pipeline as Dagster assets. No cloud cost.
- **A metric-absence alert** for "ingest never ran" (cost model §8.1):
  about $0.35/month once alerting is billed.
- **Spend cap budgets** on Cloud Run as a second hard cap, at ADR 0002's
  review.

## 7. Change log

| Date | Change |
|---|---|
| 2026-11-18 | Initial version (A10), proposed for the author's approval. Folds in the A10 inputs from `FOUNDATION_BACKLOG.md`. |
