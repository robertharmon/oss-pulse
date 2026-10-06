# ADR 0001 — Adopt a BigQuery + dbt + Serverless-GCP stack

> **Status:** Accepted
> **Date:** 2026-10-05
> **Authors:** Robert Harmon

## Context

oss-pulse is an hourly ELT pipeline over public GitHub Archive data,
built as the second half of a two-project data-engineering portfolio.
The first half ([color-analytics][color-analytics]) is image-processing-heavy —
Python, Postgres, GPU-accelerated compute, no cloud warehouse. oss-pulse
is deliberately the opposite shape: a warehouse-centered, SQL-heavy
pipeline that exercises the modern cloud data stack.

The decision is which specific tools fill each layer of that stack. It
is one of the first substantive decisions the project needs to make,
because every subsequent choice (where secrets live, what Terraform
manages, what the orchestrator schedules, what the dashboard reads
from) presupposes answers to this one.

**Hard constraints:**

- **$0/month target** ([`DECISIONS.md`](../../DECISIONS.md) §1). Every
  layer must have a free tier that realistically supports a running
  pipeline, not just a trial.
- **Solo development.** No teammates to onboard, no team conventions to
  honor. But the stack should be one that *scales* to a real team if the
  patterns are ever reused.
- **Portfolio-shaped.** The stack choices are themselves a signal to
  readers of the repo. "Why these tools, why not others" is a question
  a reviewer will ask; the answer should be legible.

**Soft constraints:**

- **Learning value.** Preference for tools that fill gaps in the
  author's experience. The author has prior experience with Python,
  Docker, and Postgres; no prior experience with cloud warehouses, dbt,
  orchestrators, IaC, or CI/CD.
- **Industry recognition.** All else equal, prefer tools that show up
  often in data-engineering job postings over niche or declining tools.
- **Simplicity under $0.** Favor serverless, pay-per-use services over
  always-on VMs. A left-on VM is the single most common way to blow a
  free-tier budget.

## Decision

The stack:

| Layer | Tool | Role |
|---|---|---|
| Cloud provider | **Google Cloud Platform (GCP)** | Everything cloud |
| Warehouse | **BigQuery** | The analytical database |
| Object storage | **Google Cloud Storage (GCS)** | Raw-data landing (Parquet) |
| Transformation | **dbt Core** (open source) | SQL models, tests, docs, lineage |
| Orchestration | **Cloud Scheduler → Cloud Run** | Schedule + run containers; no orchestrator VM |
| Secondary orchestrator (local practice) | **Dagster or Kestra** (local Docker, time-boxed) | Hands-on UI experience with a real orchestrator |
| Infrastructure-as-code | **Terraform** | All GCP resources |
| Secrets | **Google Secret Manager** | Credentials and config secrets |
| Ingest runtime | **Python 3.11 in Docker** | HTTP fetch, Parquet writing |
| Package management | **uv** | Fast, lockfile-based |
| Lint / format | **ruff** | Replaces black + isort + flake8 |
| Type check | **mypy** (strict) | Static type checking |
| SQL lint | **sqlfluff** (BigQuery dialect) | Enforces SQL style |
| Pre-commit | **pre-commit** | Local gates before CI |
| Secret scanning | **gitleaks** | Blocks secret-shaped strings |
| CI / CD | **GitHub Actions** | Runs linters, tests, Terraform |
| Data quality | **dbt tests** + **Great Expectations** (raw layer) | Two-layer coverage |
| Observability | **Cloud Logging** + **Slack webhook** | Failure alerts |
| Dashboard | **Streamlit Community Cloud** | Hosted free; reads from BigQuery |

Local prototyping may use **DuckDB** as a stand-in for BigQuery during
the first days of a change — the SQL dialect overlap is high enough that
most queries port straight over, and DuckDB needs no cloud auth to
iterate against. BigQuery is the authoritative warehouse for anything
that lands on `main`.

## Alternatives considered

### Cloud provider

- **AWS.** Industry-dominant and more commonly listed in job posts than
  GCP. Rejected because its free-tier BigQuery equivalent (Athena +
  Glue) is more operationally fiddly and the data warehouse story is
  split across multiple services. The on-ramp cost for a learner is
  higher without a learning benefit.
- **Azure.** Mostly relevant in enterprise + Microsoft shops; weaker
  free tier for independent learners. Rejected on free-tier friendliness.

### Warehouse

- **Snowflake.** Industry-leader and arguably more employable than
  BigQuery. Rejected because the free tier is a 30-day trial, not an
  always-free allocation. A pipeline running for months is incompatible
  with the budget constraint.
- **Databricks.** Appears more often than BigQuery in job postings,
  especially for ML-adjacent roles. Rejected because (a) the always-free
  tier (Community Edition) is restrictive and doesn't match the real
  product, (b) oss-pulse is pure SQL analytics with no ML or Spark-shaped
  compute, so Databricks's unique strengths wouldn't be exercised, (c)
  the setup overhead is higher. Databricks is a candidate for a *second*
  learning project, not this one. See the "Related future work" section.
- **DuckDB alone.** Could run the whole pipeline locally with no cloud
  warehouse at all. Rejected because the portfolio value is specifically
  in demonstrating experience with a *cloud* warehouse — the single
  largest gap vs. a professional DE profile.

### Orchestration

- **Apache Airflow.** The industry standard; appears on the most job
  listings. Rejected as the *primary* orchestrator here because it
  requires an always-on process (webserver + scheduler + workers) that
  pushes the project outside the $0 budget. Local Airflow in Docker is
  possible but notoriously heavy for a small pipeline. Kept as a
  future-project candidate.
- **Dagster.** Modern, pleasant developer experience, strong asset-based
  mental model. Chosen as the preferred *local-practice* orchestrator
  during time-boxed learning sprints, so the author gets hands-on UI
  experience with a real orchestrator without eating the budget.
- **Kestra.** Simpler to learn (YAML DAGs), used by the DataTalks.Club
  Zoomcamp. Second choice for local practice; Dagster edges it on
  general industry adoption.
- **Prefect.** Comparable to Dagster. Not picked only because carrying
  three orchestrators in one head is one too many.
- **Cloud Scheduler + Cloud Run (chosen).** Not really an "orchestrator"
  in the DAG-view sense — it's a cron trigger that invokes a container.
  Chosen because it's genuinely free at this scale and the pipeline is
  linear enough (ingest → dbt build → done) that a full DAG framework is
  overkill for the production path.

### Transformation

- **dbt.** No real alternative. dbt is the default modern-stack
  transformation framework; every other option (SQLMesh, Dataform,
  custom Jinja + Python) is either strictly less capable, strictly less
  recognized, or both. The one close call is **SQLMesh**, which is
  newer and arguably more correct in some ways (semantic versioning of
  models, better incremental semantics). Rejected because dbt's industry
  recognition is overwhelming at the entry-level DE hiring stage —
  "dbt" is a resume-filter keyword, "SQLMesh" is not yet.

### Infrastructure-as-code

- **Pulumi.** Terraform's modern competitor; lets you write infra in
  Python/TypeScript. Rejected because Terraform is strictly more
  recognized in DE job postings and the HCL learning curve is modest.
- **Click-ops in the GCP console.** Rejected on principle — the whole
  point of IaC is reproducibility and reviewability.

### Ingest runtime

- **Airbyte or Fivetran** (hosted ingestion services). Rejected because
  the free tier doesn't cover a custom source well, and the point of
  oss-pulse is to practice *writing* an ingest job, not to outsource it.
  Airbyte is a candidate for a future project that focuses on managed
  pipelines.
- **Pure Python without Docker.** Would work locally, but containerizing
  the ingest is required for Cloud Run (the chosen orchestrator
  surface) and is a learning target in itself.

### Dashboard

- **Looker Studio** (Google's BI tool, free). Rejected because its
  interface is a dashboard-builder GUI, not code — nothing meaningful
  to put in version control, no code-review opportunity.
- **Metabase.** Would work but requires either hosting (not free) or
  running locally (defeats the "operates somewhere other than my
  laptop" goal).
- **Evidence.dev.** Interesting (code-driven BI, markdown-plus-SQL
  files). Could substitute for Streamlit in a later iteration.
  Rejected now only because Streamlit is more universally recognized
  and the author knows it already.

## Consequences

### Positive

- **$0/month is actually reachable.** Every service in the stack has a
  genuine free tier or free-tier-friendly pricing. The budget constraint
  can be enforced by architecture, not vigilance.
- **The stack maps directly onto the most common gaps in the author's
  current experience** — cloud warehouse, dbt, orchestrator, IaC,
  CI/CD, cloud storage.
- **Each tool is independently employable.** BigQuery, dbt, Terraform,
  GitHub Actions, Python, Docker, Streamlit are all top-tier job-posting
  keywords.
- **Local prototyping stays fast.** DuckDB mimics BigQuery closely
  enough that most SQL ports over with no changes, and the dev loop
  doesn't require network round-trips.
- **The pipeline is portable in principle.** dbt swaps BigQuery for
  Snowflake or Databricks with a single `profiles.yml` adapter change.
  If a future employer uses one of those, the models themselves migrate
  with minimal rewriting.

### Negative / cost

- **No real orchestrator UI in production.** Cloud Scheduler + Cloud Run
  gives schedule + retry + logs, but not the "DAG view with task
  status" interface that Airflow or Dagster provide. The author
  compensates by running Dagster locally for time-boxed practice, but
  real production operational experience with those tools remains a
  gap this project doesn't close.
- **GCP ≠ AWS.** AWS appears in more job postings than GCP. Learning GCP
  teaches 70-80% of what transfers directly (SQL, Python, Docker, IaC
  patterns, Terraform, CI/CD, lineage, data modeling), but AWS-specific
  services (Lambda, EMR, Redshift idioms, S3-vs-GCS defaults) remain
  gaps. Mitigation: the same stack rebuilt on AWS would be a strong
  "I know both" portfolio piece in a later project.
- **No Spark exposure.** Databricks and Spark are increasingly common
  in enterprise DE roles. This stack doesn't exercise them. Explicitly
  deferred to a future project.
- **Serverless orchestration lacks some operational realism.** Running
  "the VM filled its disk" or "the cluster crashed at 3am" scenarios
  isn't possible when there's no VM and no cluster. The oss-pulse
  observability + alerting work has to be deliberately designed to
  surface failures that would otherwise be invisible.

### Neutral but worth noting

- **The $0 constraint shapes some choices that wouldn't survive at a
  real company.** For instance, Cloud Scheduler + Cloud Run as the
  primary orchestrator makes sense for one tiny pipeline; a real
  company would run Airflow or Dagster from day one. The reader of
  this repo should understand this is a learning-optimized stack, not
  a scale-optimized one.
- **dbt and Terraform both have steep day-one learning curves** before
  they feel natural. Expect the first few PRs in each to feel slow.
  Normal.

## Related future work (explicit non-goals here)

Captured so no one spends time wondering if these were missed:

- **Second portfolio project on AWS** — same stack shape (ELT, dbt,
  Terraform, IaC-ful) rebuilt on AWS to prove cross-cloud fluency.
- **Databricks mini-project** — a 3-4 weekend effort on Databricks
  Community Edition using Delta Lake, PySpark, and MLflow. Serves the
  Spark-and-ML-platform gap.
- **A Kafka or streaming project** — separate mental model from batch
  ELT, deserves its own dedicated effort.

## Review date

Revisit by **2027-04-05** (six months), or earlier if any of the following
trigger:

- Monthly cloud spend goes above $5 for three consecutive months (the
  $0 constraint is clearly broken).
- The author takes a role that uses a materially different stack and
  continuing to invest in this one no longer compounds.
- A chosen tool is announced end-of-life or materially re-pricing
  (e.g., BigQuery eliminates the free tier).
- The project advances past the foundation phase and the operational
  realities of running it suggest a different tradeoff.

## References

- [`DECISIONS.md`](../../DECISIONS.md) — operating decisions this ADR
  builds on, especially §1 (GCP account + $0 budget), §2 (region), §5
  (secrets policy).
- [`FOUNDATION_BACKLOG.md`](../../FOUNDATION_BACKLOG.md) — ordered
  foundation plan; this ADR is item A4.
- [`color-analytics-pipeline/CLAUDE.md`][color-analytics] — sibling
  project this stack deliberately differs from.

[color-analytics]: ../../../Codebase_ColorAnalytics
