# Quiz for Session 03 — A6 CONVENTIONS.md and the No-Local-Docker Decision

**Date:** 2026-10-06
**Topics from ELI5 walkthroughs this session:**

- Linters and formatters (ruff / mypy / sqlfluff) — what each is, where they
  overlap, where they don't
- `mypy --strict` as a fail-fast lever in a batch ELT pipeline
- Leading commas in SQL — the diff-friendliness argument
- CTEs vs nested subqueries — named steps, top-to-bottom reading order
- `SELECT *` in production models — schema propagation that bypasses PR review
- Serverless scheduling (Cloud Scheduler + Cloud Run) — what runs when nobody
  is touching the system

---

## Q1. Linters & formatters

**Question:** A linter and a formatter are both tools that read your source
code without running it, but they do fundamentally different jobs. In one or
two sentences, explain the difference — and name one specific problem a
linter catches that a formatter wouldn't.

**My answer:** A linter is about problematic patterns in the code —
identifying poor practices, enforcing typing, etc. A formatter is about
style — making sure all parts of a script follow the same formatting
conventions.

**Grade:** Partial

**Gap:**

- Didn't commit to a *concrete* example. The question asked for one specific
  problem a linter catches; answered with categories ("poor practices,"
  "enforcing typing") rather than a concrete lint catch like "unused import."
- "Enforcing typing" blurs linter vs. type checker. Type checking (mypy) is
  a *sibling* tool, not a subset of linting (ruff). Python separates them
  clearly: ruff lints, mypy type-checks.

**Reference:**

A **formatter** rewrites code into a canonical shape — spacing, line breaks,
import order, trailing commas. It never changes what the code *means*, only
how it looks. A **linter** flags suspicious or buggy *patterns* — unused
imports, variables assigned but never read, `== None` instead of `is None`,
mutable default arguments (`def f(x=[]):` — every call reuses the same list),
shadowed names.

The clean dividing line: a formatter can run on your code and always produce
an equivalent program; a linter tells you your program is *wrong or
suspicious* even though it would run.

Concrete lint catches a formatter would never notice:

- `import json` at the top, never used → unused-import warning.
- `def append(x, items=[]):` → mutable-default-argument warning.
- `if x == None:` → use `is None`.

---

## Q2. `mypy --strict`

**Question:** Python runs fine without type annotations — `def hours_since(ts): return int((datetime.now() - ts).total_seconds() / 3600)` works. So what does
`mypy --strict` actually *buy* you in a batch ELT pipeline that runs hourly
on Cloud Run? Frame your answer in terms of *when* an error gets caught.

**My answer:** It catches typing errors before you ever merge the code into
production, that way you waste no time.

**Grade:** Right

**Gap:** None on the core answer. Depth note: "waste no time" undersells
*why* catching early is specifically valuable for a batch ETL pipeline. See
reference for the shift-left economics and the batch-vs-webserver
distinction.

**Reference:**

`mypy --strict` converts runtime type bugs (expensive, unattended, 3am) into
check-time lint failures (cheap, in a PR, during business hours). Same
shift-left logic as the fail-fast error-handling philosophy in
DECISIONS.md §6, applied before the code even runs.

Why this matters more for batch ETL than for a web server:

- A web server's type bug surfaces almost immediately — the next request
  after deploy hits it. Someone's watching, someone pages, you roll back.
- A batch ETL's type bug surfaces *when the scheduled job next runs* —
  possibly 3am with nobody watching. By the time anyone notices, backfill
  queues have piled up, trust is dented, and the postmortem is already
  being drafted.

Same bug, two orders of magnitude different cost depending on when it was
caught.

---

## Q3. Leading commas in SQL

**Question:** A SQL style guide calls for *leading* commas on multi-column
`SELECT` lists instead of trailing commas. What's the specific advantage,
and in whose workflow is it felt?

**My answer:** It's more efficient because removing or adding a column
under SELECT only requires editing one line. With trailing commas, adding a
line would require adding a comma at the end of the previous line, then
adding the new line. I think it's felt in many scenarios — more efficient
for a human to write/edit, same for an LLM, maybe for a linter to evaluate.

**Grade:** Partial

**Gap:**

- Mechanism (one-line vs two-line diff) — right.
- *Whose workflow* — missed. The advantage is felt at **read time**, not
  write time. Autocomplete makes typing a comma trivial, so writer-ergonomics
  is a minor benefit. The real wins are for the PR reviewer and the
  `git blame` reader.

**Reference:**

The advantage is a one-line diff for a column add/remove instead of two.
It's felt by:

1. **Code reviewers.** A one-line diff (`+ event_type` added, nothing else
   touched) says "this PR adds one column." A two-line diff (previous
   column's trailing comma also modified) shows two edits even though one is
   semantically a no-op. Multiplied over hundreds of PRs, that's a real
   reviewer tax.

2. **`git blame` readers.** With trailing commas, when Bob adds `event_type`
   today, Alice's `created_at` line gets a comma appended → `git blame` now
   attributes `created_at` to **Bob, today**. Alice's history is overwritten
   for a cosmetic reason. With leading commas, Alice's blame line is
   untouched; `event_type` gets a new line attributed to Bob. Archaeological
   trail stays accurate.

Writers-vs-readers distinction worth internalizing: code is written once and
read many times. Convention choices that trade a tiny writer-ergonomics cost
for a meaningful reader-ergonomics win are almost always correct. Same logic
underlies the "default to no comments" rule in CONVENTIONS.md §7.

---

## Q4. CTEs vs nested subqueries

**Question:** A query written as deeply nested subqueries and the same query
written as a sequence of CTEs produce identical results and (in BigQuery)
identical performance. Given that, what's the readability-and-maintenance
argument for choosing CTEs?

**My answer:** CTEs are more visually separated/distinct than nested
subqueries — it's much easier to see how many CTEs are involved than nested
subqueries. CTEs also lead to fewer errors since devs are less likely to
accidentally veer into a neighboring query.

**Grade:** Partial

**Gap:**

- "Visual separation" is directionally right but shallow.
- Missed the two biggest wins: **naming** and **reading-order**.
- CTEs let each intermediate step have a human-picked name, which doubles as
  inline documentation. Nested subqueries hide the same logic inside
  anonymous expressions.
- CTEs flip the reading order from inside-out (nested) to top-to-bottom
  (narrative). Humans read code top-to-bottom by default; inside-out is
  cognitive overhead that compounds with query depth.

**Reference:**

CTEs give each intermediate step a human-picked name that doubles as inline
documentation, and they flip reading order from inside-out to top-to-bottom.
The naming is the key — it turns an anonymous expression tree into a
sequence of named, reviewable steps.

Bonus benefit: diff-friendliness. Inserting a new step (say "exclude bot
accounts") in the CTE version is a self-contained new CTE block between
existing ones. In the nested version it's surgery inside a parenthesized
expression.

Example:

```sql
with recent_stars as (                          -- named: filter step
    select * from events
    where event_type = 'WatchEvent'
      and created_at >= timestamp('2026-10-01')
)

, stars_per_repo as (                           -- named: aggregate step
    select r.repo_name, count(*) as star_count
    from recent_stars
    join repos r on r.repo_id = recent_stars.repo_id
    group by r.repo_name
)

select repo_name, star_count                    -- final: filter + sort
from stars_per_repo
where star_count > 100
```

The names `recent_stars` and `stars_per_repo` *are* the documentation.

---

## Q5. `SELECT *` in production models

**Question:** A production dbt mart uses `select * from {{ ref('stg_events') }}`.
In a different PR, someone adds a new column to `stg_events`. What goes
wrong downstream, and why doesn't the mart's own code review catch it?

**My answer:** Suddenly the dbt mart is aggregating more rows than it was
intended to, and the change is silent. The mart's own code review doesn't
catch it because there's nothing technically wrong with the code itself.

**Grade:** Partial — with a direct correction

**Gap:**

- **Columns ≠ rows.** Adding a column adds a field to every existing row;
  it doesn't change the row count. The failure mode here is **schema drift**,
  not row explosion. Those two have completely different debugging stories
  and should stay cleanly separated:
  - Row count changes = join / filter / group-by behaved differently.
  - Column set changes = schema propagation from upstream.
- "Nothing wrong with the code" is directionally right but undersells the
  point. The sharper version: **the mart's file isn't in the diff at all.**
  The PR that broke things touches only `stg_events.sql`. The reviewer sees
  one file and reviews it in isolation. The fact that four downstream marts
  silently gained a column is invisible in git.

**Reference:**

Downstream, the mart silently gains the new column — its output schema
changes with no code change in its own file. Consumers (dashboards, BI
tools, dbt tests that assert column lists) suddenly see a schema they didn't
expect. The mart's code review doesn't catch it because **the mart's `.sql`
file isn't in the diff at all** — the only PR involved is the upstream
`stg_events` edit, which touches one file and gets reviewed in isolation.
The propagation is invisible in git.

That's the whole argument against `SELECT *` in prod: it converts explicit,
reviewable schema changes into **implicit** ones that bypass PR review
entirely. Explicit column lists force every schema change to appear as a
visible edit in the downstream file, so the review conversation happens on
the right PR.

---

## Q6. Serverless scheduling

**Question:** An "hourly" ETL pipeline is set up on Cloud Scheduler + Cloud
Run. It's 3:30am and nobody has touched the system in weeks. Describe
what's actually running at that moment — and explain why the monthly bill
can still be $0.

**My answer:** Everything is running on the cloud. The monthly bill can be
$0 because of the plan chosen.

**Grade:** Wrong

**Gap:**

Both halves miss, and this is the misconception-correcting question in the
quiz — the one worth getting right.

- "Everything is running on the cloud" is the wrong mental model. At
  3:30am, **nothing of yours is running.** No container exists. No process
  is live. Cloud Run is *request-triggered*, not a daemon — between fires,
  your container doesn't exist in any pause state, it's genuinely gone and
  recreated fresh at the next fire.
- "$0 because of the plan chosen" misreads the mechanism. There is no plan.
  The bill is $0 because (a) serverless pricing charges only for execution
  time, so you pay for ~2 minutes/hour × 24 = ~48 min/day of compute, and
  (b) that falls inside Cloud Run's monthly free tier. The other 23h 12min
  of each day don't exist on your bill because they don't exist as compute.

**Reference:**

At 3:30am, **nothing of yours is running** — no container, no process.
Cloud Scheduler holds a cron entry that will fire at :15 past the next hour;
Cloud Run has no live container between fires. At each hour mark:

```
03:15:00 UTC  Scheduler fires → HTTPS POST to a Cloud Run URL
03:15:02 UTC  Cloud Run cold-starts your container
03:17:00 UTC  Container finishes → exits → vanishes
03:17:01 UTC  Nothing of yours exists until the next fire.
...
03:30:00 UTC  Pure quiet. No compute of yours in use.
```

The bill is $0 because serverless pricing is per-execution: 24 fires × ~2
minutes = ~48 minutes/day of compute, which fits well inside Cloud Run's
monthly free tier (2M requests, hundreds of thousands of vCPU-seconds).
Scheduler and small BigQuery scans are also within their free tiers. There's
no idle-time charge because there's no idle resource — Cloud Run only
exists while serving a request.

Why this matters architecturally: the alternative — an always-on VM running
`cron` — would cost $5-30/month regardless of whether the job ran or not,
because you're renting the machine 24/7. The $0 target in DECISIONS.md §1
is only achievable *because* the stack was chosen specifically to pay for
execution, not idle. The target drives the stack choice.

---

## Final tally

| Q | Topic                              | Grade   |
|---|------------------------------------|---------|
| 1 | Linter vs formatter                | Partial |
| 2 | `mypy --strict`                    | Right   |
| 3 | Leading commas                     | Partial |
| 4 | CTEs vs nested subqueries          | Partial |
| 5 | `SELECT *` in prod                 | Partial |
| 6 | Serverless scheduling              | Wrong   |

**Pattern noticed across the session:** The *shape* of the right answer
(what the mechanism is, which direction the benefit flows) is usually
there, but the specifics stop short — a correct direction without a
concrete example, or a shallow version of a deeper argument. Q6 was the
exception, where the mental model itself ("nothing runs between fires")
wasn't in place yet. Worth re-reading that one in particular; serverless
cost intuition is foundational for the $0 target that governs almost every
later stack decision.

**Follow-ups** (not asked in-session but worth logging):

- The column-vs-row distinction (Q5) is likely to come up again in dbt
  land. "Schema drift" and "row explosion" are both failure modes but have
  separate debugging kits — if a future dbt test fails, know which one is
  firing before you start looking.
- The writers-vs-readers framing (Q3) applies well beyond leading commas.
  CONVENTIONS.md §7's comments rule is the same principle: writing a
  comment is cheap for the author and a liability for every future reader.
  Reach for it when you notice yourself tempted to add a cosmetic artifact
  "for clarity."
