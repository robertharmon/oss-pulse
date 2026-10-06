# oss-pulse — Code & Documentation Conventions

> How we name things, format code, and shape commits in this repo.
>
> Many conventions live in [`DECISIONS.md`](DECISIONS.md) already (naming
> specifics in §4, branch/commit/PR rules in §9, error handling in §6,
> resource management in §7, testing in §8). This file **does not restate
> them** — it points at them, fills the gaps, and adds the one genuinely
> project-specific rule they don't cover (**when to write comments**, §7
> below).
>
> Treat conventions as **rules you apply**, not judgments to re-litigate
> per file. When adding or renaming something, resolve it against this doc
> and DECISIONS.md.

---

## 1. Naming — meaning out of context

The guiding principle: a filename or identifier mentioned in a diff, PR
discussion, or chat should tell the reader what it is without opening the
file. Four rules, all enforced:

1. **Vocabulary consistency.** When the project has an established term
   for a concept (e.g. "event", "repo", "actor", "mart", "staging"), use
   *that* term everywhere — code, dbt models, docs, commit messages.
   No adjacent synonyms (`event` vs `activity`, `repo` vs `project`).
2. **Match altitude to specificity.** A module that produces one specific
   thing is named after that thing, not its category. `gharchive_fetcher.py`
   over `fetcher.py`. `fct_events.sql` over `events.sql`.
3. **Pipeline stages carry input → output in the filename.** For
   multi-stage ingest / ELT scripts, use
   `s<N>_<subject>_<input>_to_<output>.py` — e.g.
   `s1_gharchive_hour_to_gcs_json.py`,
   `s2_gharchive_gcs_json_to_bq_raw.py`.
   Single-stage modules stay simpler.
4. **Length is OK when it earns its place.** Autocomplete makes typing
   trivial; long descriptive filenames pay dividends in diffs and chat.
   Rough ceiling: ~55 chars before considering the docstring instead.

Specifics (GCP projects, buckets, datasets, tables, service accounts,
Secret Manager entries, Python modules, dbt models, Terraform resources):
**see [`DECISIONS.md`](DECISIONS.md#4-naming-conventions) §4.**

### Deprecated / forbidden terms

(Populate as the vocabulary stabilizes. Keep the deprecated term + what
replaced it, so a future reader knows why a name is absent.)

- *(none yet)*

---

## 2. Python style

- **Formatter / linter:** `ruff` (both format and lint). `ruff` config
  lives in `pyproject.toml`; no project-local style debates — if ruff
  accepts it, it's fine.
- **Type checker:** `mypy --strict`. New code is fully typed. If a
  third-party library lacks stubs, add a narrow `# type: ignore[...]`
  with the specific error code, not a bare `# type: ignore`.
- **Line length:** whatever ruff defaults to (88). Don't fight it.
- **Imports:** ruff's import sorter (`I` rules) handles order. Group
  stdlib → third-party → first-party; ruff enforces.
- **Identifier conventions:**
  - Functions / variables: `lower_snake_case`
  - Constants: `SCREAMING_SNAKE_CASE` at module top
  - Classes: `PascalCase`
  - Private module members: single leading underscore (`_helper`)
- **Resource management:** `with` blocks for every external resource
  (BigQuery clients, GCS clients, file handles, HTTP sessions). See
  [`DECISIONS.md`](DECISIONS.md#7-resource-management-convention) §7.
- **Errors:** fail fast; don't swallow. See
  [`DECISIONS.md`](DECISIONS.md#6-error-handling-philosophy) §6.
- **Tests:** every test must fail if one line of production code is
  deleted. See [`DECISIONS.md`](DECISIONS.md#8-testing-philosophy) §8.

---

## 3. SQL style

Applies to both ad-hoc BigQuery and dbt models.

- **Linter:** `sqlfluff` with the `bigquery` dialect; config in
  `.sqlfluff`. Lint runs in pre-commit and CI.
- **Keywords:** lowercase (`select`, `from`, `where`, `join`). Lowercase
  reads better next to lowercase identifiers and is cheaper on the eyes
  in a long model.
- **Identifiers:** `snake_case`, all lowercase. BigQuery is
  case-insensitive for identifiers but mixed casing causes diff noise.
- **Trailing commas:** leading commas, not trailing — makes column
  additions a one-line diff. (sqlfluff enforces.)
- **CTEs over subqueries.** A query with more than one logical step
  reads as `with step_1 as (...), step_2 as (...) select ... from step_2`.
  Nested subqueries only when the step is a single scalar.
- **One statement per file** for dbt models (dbt enforces).
- **References:** inside dbt, always `{{ ref('model_name') }}` and
  `{{ source('schema', 'table') }}`. Never a hard-coded
  `project.dataset.table`.
- **Column order (marts):** keys first, then dimensions, then measures,
  then timestamps. Consumers scan left-to-right and expect this.
- **No `SELECT *` in production models.** Explicit column lists. (A
  staging model mirroring a raw table is still explicit — list the
  columns we actually use downstream.)

---

## 4. Branch names

**See [`DECISIONS.md`](DECISIONS.md#9-commit-branch-and-pr-conventions) §9.**

Shape: `<type>/<short-slug>`. Common types: `feat`, `fix`, `docs`,
`chore`, `refactor`, `test`, `ci`.

---

## 5. Commit messages

**See [`DECISIONS.md`](DECISIONS.md#9-commit-branch-and-pr-conventions) §9.**

Shape: `type(scope): subject`. Body explains *why*, not *what*. No AI
co-author trailers — the author of a commit is Robert.

---

## 6. PR titles & descriptions

- **Title matches the squash-merge commit** that will land on `main`.
  Use the same `type(scope): subject` shape as commit messages.
- **Description** uses the PR template (lands in B8). Until then, cover:
  - **What** changed (one sentence)
  - **Why** (one or two sentences, or a link to the issue / ADR / backlog
    item)
  - **How tested** (what you ran, or "docs-only")
  - **What could break** (one sentence — honest answer, even if "nothing")
- **No AI-assistant footers.** No "Generated with Claude Code" line, no
  co-author trailer. See
  [`DECISIONS.md`](DECISIONS.md#9-commit-branch-and-pr-conventions) §9.
- **One logical change per PR.** If the description needs the word "also"
  or "additionally", it's probably two PRs.

---

## 7. When to write comments

**Default: don't.** Well-named identifiers already say *what* the code
does. A comment that restates the code is noise — it rots when the code
changes, and a future reader learns to skip comments entirely.

**Write a comment only when the *why* is non-obvious.** The test: if you
delete the comment, would a future reader (including you in six months)
plausibly misunderstand the code or re-introduce a bug? If yes, keep it.
If no, delete it.

Legitimate reasons for a comment:

- **Hidden constraints** that the code can't express — "GH Archive drops
  the UTC hour N at ~N+45; schedule accounts for this."
- **Subtle invariants** — "`events` is sorted by `created_at` so the
  windowed join below is valid; preserve order."
- **Workarounds for a specific external bug** — "BigQuery's `JSON_VALUE`
  returns NULL for empty strings as of Oct 2026; coerce explicitly."
- **Surprising business rules** — "A pull_request event with action
  `closed` and `merged=false` means closed-without-merging; the dashboard
  counts these separately from merges."

Illegitimate reasons (don't write these):

- Restating what the code does (`# increment counter`)
- Referencing the current task / PR / issue (`# fix for issue #42`) —
  that belongs in the commit message, which doesn't rot
- "Added for the X flow" (`# used by the hourly ingest job`) — identifier
  names and `git grep` already tell this story
- Section headers inside a long function — the function is too long;
  extract instead

**Docstrings follow the same test.** A one-line docstring that just
restates the function name is noise; a docstring that documents the
*contract* (inputs, invariants, side effects, failure modes) is
valuable. For pipeline-stage files especially, lead the module docstring
with what the stage reads and writes:

```python
"""Stage 1 — Fetch one UTC hour of GH Archive events to GCS.

Reads:  https://data.gharchive.org/<YYYY-MM-DD-HH>.json.gz
Writes: gs://osp-raw-events-<env>/gharchive/<YYYY/MM/DD/HH>.json.gz

Fails fast on HTTP non-2xx, zero bytes, or a schema that doesn't
contain a `type` field in the first record.
"""
```

### SQL comments

Same rule, same test. dbt models get a `description:` in `schema.yml`
rather than an inline `-- comment` — the description surfaces in dbt
docs and in BigQuery table metadata. Inline SQL comments stay for
non-obvious joins, filter rationale, or workarounds.

---

## Change log

| Date | Change |
|---|---|
| 2026-10-06 | Initial version. Consolidates naming/branch/commit/PR rules from DECISIONS.md and adds Python style, SQL style, PR title shape, and the comments rule. |
