# Open Loops

> Small ad-hoc tasks that don't belong in `FOUNDATION_BACKLOG.md` (which
> tracks phased foundation work) and don't individually warrant their own
> dedicated session or PR. Pick things off opportunistically — at the start
> or end of a session, when context is thin, or when a cheap chore pairs
> naturally with other work.
>
> Delete items when done rather than marking them complete; this file is a
> working queue, not a historical record. The commit history is the record.

Status markers:
- `[ ]` open
- `[~]` in progress (someone is actively working on it)
- `[-]` deliberately dropped (keep with a reason so it doesn't come back)

---

## Housekeeping

- [ ] **Add GitHub repo topics** — go to
  https://github.com/robertharmon/oss-pulse → ⚙ next to **About** → paste:
  `data-engineering elt dbt bigquery terraform portfolio-project`
- [ ] **Enable auto-prune of stale remote-tracking refs** — run
  `git config --global fetch.prune true` so merged-and-deleted remote
  branches get cleaned up on every `git fetch`, no `--prune` flag needed.
  (Global config change; not a repo-local setting.)

## Decisions to revisit

- (empty — add items here when something is tentatively decided but
  deserves a second look after more context lands)

## Things to double-check once CI exists (gated on B6)

- [ ] **Add CI status checks to the `protect-main` ruleset** — the
  "Require status checks to pass" rule is currently in the ruleset but
  its list of required checks is empty. Once CI jobs exist (B6), add
  each job's name (`lint-python`, `typecheck`, `lint-sql`,
  `test-python`, `terraform-fmt`, `terraform-validate`, `secret-scan`)
  to that list so merges are blocked when any check fails.

## Things to double-check once the first ADR lands (gated on A4)

- (will be populated based on what A4 reveals needs follow-up)

---

## How to add items

Keep entries short and self-contained. If an item needs more than a few
lines to describe, it probably belongs in `FOUNDATION_BACKLOG.md` or
deserves its own session rather than a line in this file.

Each entry should answer: **what** needs doing, **why**, and **where/how**
to do it. The "where/how" is especially important — this file exists so
that items can be picked up with zero context-switching cost.
