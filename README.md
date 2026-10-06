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
   increase in stars, PRs, or pushes.
2. **Language contributor share** — percentage of unique contributors
   touching each language, month over month.
3. **Contributor concentration per repo** — Gini coefficient of commits per
   author. Is a repo sustained by one person or many?
4. **Time-of-day activity patterns** — commit and PR distribution by hour,
   split by primary language of the repo (a rough geography proxy).

Each becomes one `mart_*` table and one chart on the dashboard.

## Scope boundaries

See [`DECISIONS.md`](DECISIONS.md) §10 for the full list. In brief: hourly
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

A full map will land once the skeleton is in place. For now:

```
oss-pulse/
├── README.md                  ← this file
├── DECISIONS.md               ← locked operating decisions
├── FOUNDATION_BACKLOG.md      ← phased foundation work (ordered)
├── OPEN_LOOPS.md              ← ad-hoc housekeeping queue
└── docs/
    └── adr/                   ← Architecture Decision Records (coming)
```

## Running locally

Not yet runnable. This section will be filled in once the walking skeleton
is in place.

## License

TBD. Will be added before the repo is made public.
