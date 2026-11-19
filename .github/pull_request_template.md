<!-- Title: `type(scope): subject`, the same as the squash commit (CONVENTIONS §6). -->

## What
<!-- One sentence. -->

## Why
<!-- One or two sentences, or the roadmap item / ADR / FM-, R-, M- IDs this serves. -->

## How tested
<!-- What you ran, and its result. For a gate or config: the planted-bad-input drill (ways of working §3.3). For docs: "docs-only" plus the review. -->

## What could break
<!-- An honest answer, even if it's "nothing". -->

## Rollback
<!-- How to undo it: usually "revert this PR". Say so if anything else is needed (data, state, a setting). -->

## Checklist
- [ ] One logical change (no "also")
- [ ] Code with behavior: stubs → red (tests only, failing by assertion) → green commits, none mixing test and non-test paths (ways of working §3.1)
- [ ] Every doc the change touches is updated, or a follow-up PR is linked
- [ ] Reviewer subagent's findings fixed or answered below
- [ ] No secrets, and no AI-assistant attribution (DECISIONS §5, §9)
