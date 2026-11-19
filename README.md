# oss-pulse

An hourly ELT pipeline over public GitHub activity data, built as a data
engineering portfolio project.

Every hour, the pipeline pulls the previous hour of public GitHub events from
[GH Archive](https://www.gharchive.org/), lands the raw JSON in Google Cloud
Storage, loads it into BigQuery, transforms it with dbt into analytical marts,
and serves the results through a small Streamlit dashboard.

---

## Why this exists

This repo is one half of a two-project portfolio demonstrating end-to-end data
engineering practice. The other half ([color-analytics][color-analytics]) is an
image-processing-heavy pipeline that exercises Python, Postgres, and
GPU-accelerated compute. oss-pulse is deliberately the opposite shape — a
warehouse-centered, SQL-heavy ELT pipeline that exercises the modern cloud
data stack:

- Cloud warehouse (BigQuery)
- Object storage (GCS)
- Transformation framework (dbt)
- Orchestration (Cloud Scheduler + Cloud Run, with optional local Kestra for
  practice)
- Infrastructure-as-code (Terraform)
- CI/CD with branch protection (GitHub Actions)
- Data quality (dbt tests + Great Expectations)
- Observability + lineage (dbt docs, Cloud Logging, Slack alerts)
- Downstream consumer (Streamlit dashboard)

Together, the two projects show the ability to work across both ends of the
data-engineering spectrum.

[color-analytics]: ../../Codebase_ColorAnalytics

## The questions it answers

The entire pipeline exists to serve a small set of analytical questions. The
mart tables and dashboard are built directly against this list:

1. **Trending repos this week** — repos with the largest week-over-week
   increase in stars, PRs opened, or PRs merged.
2. **Language contributor share** — percentage of unique contributors
   (actors who opened or merged a PR) touching each language, month over
   month.
3. **Contributor concentration per repo** — Gini coefficient of PRs opened
   per actor. Is a repo's work proposed by one person or many?
4. **Time-of-day activity patterns** — distribution of PRs opened, PRs
   merged, issues opened and stars by hour, split by primary language of
   the repo (a rough geography proxy).

Each becomes one `mart_*` table and one chart on the dashboard.

GH Archive's current public feed carries no push events (`PushEvent`): none
appeared in any hour sampled since October 2026. So no question is phrased
in terms of commits or pushes. [`docs/data_contract.md`](docs/data_contract.md) §4.3 and §5 have
the details.

## Scope boundaries

See [`DECISIONS.md`](DECISIONS.md) §11 for the full list. In brief: hourly
batch only (no streaming), single cloud (GCP), single source (GH Archive),
no ML models, no PagerDuty-grade on-call. Anything beyond this list requires
an ADR before scope changes.

## Status

**Foundation phase.** The repo is being built in a disciplined,
scaffolding-first order. Phased foundation work is tracked in
[`FOUNDATION_BACKLOG.md`](FOUNDATION_BACKLOG.md). Small ad-hoc chores
that don't belong in the phased plan live in
[`OPEN_LOOPS.md`](OPEN_LOOPS.md). The pipeline itself is not yet
running — foundation documents and infrastructure come first, by
intention.

## Repository map

Each code folder has a short README saying what belongs in it.

```
oss-pulse/
├── README.md, SECURITY.md     ← this file; how to report a security problem
├── CLAUDE.md                  ← Claude Code session-startup instructions
├── DECISIONS.md               ← locked operating decisions
├── CONVENTIONS.md             ← naming, Python/SQL style, PRs, comments
├── FOUNDATION_BACKLOG.md      ← foundation work (Phase A done; B–D open)
├── OPEN_LOOPS.md, QUESTIONS.md← small chores; questions for the author
├── RUNBOOK.md                 ← alert routing, procedures, incident log
├── ingest/                    ← hourly ingest service (GH Archive → GCS → raw)
├── dbt/                       ← dbt project and the daily build service
├── dashboard/                 ← Streamlit app
├── killswitch/                ← billing kill-switch function
├── terraform/                 ← GCP infrastructure as code
├── scripts/                   ← CI verifier scripts
├── tests/                     ← Python tests, fixtures, expected outputs
├── .github/                   ← CI workflows, PR template, CODEOWNERS
├── documentation/             ← per-session docs + decision log
└── docs/
    ├── roadmap.md             ← milestones to v1 (the tracker)
    ├── ways_of_working.md     ← roles, definition of done, when to ask
    ├── architecture.md        ← system diagram + end-to-end record trace
    ├── data_contract.md       ← tables, failure modes, balancing counts
    ├── access_matrix.md       ← who/what can access each resource
    ├── security.md            ← credentials, data classes, disclosure
    ├── cost_model.md          ← cadence, retention, quotas, spend
    ├── author_setup.md        ← accounts and settings only the author creates
    └── adr/                   ← Architecture Decision Records
```

## Running locally

Not yet runnable. This section will be filled in once the walking skeleton
is in place.

## License

TBD. Will be added before the repo is made public.
