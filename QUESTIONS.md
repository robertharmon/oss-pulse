# Questions for the author

> Decisions the build agents can't make alone. Agents add a question here
> when they're blocked, then keep working on something else. The author
> answers inline whenever convenient. Agents check this file at the start
> of each session, act on answers, and move answered questions to the
> **Answered** section (with the date) so the reasoning stays findable.
>
> Rules for agents:
> - **Ask only what's genuinely the author's call:** scope, cost,
>   security, accounts, or an ambiguous spec. Anything the docs already
>   answer isn't a question.
> - **Give a recommendation** and the cost of each option, so the answer
>   can be one word.
> - **Say what's blocked** while the question is open.

Format:

```
### Q<N>. <one-line question>  (opened YYYY-MM-DD, blocks: <item>)
**Context:** …
**Options:** (a) … (recommended) — cost …  (b) … — cost …
**Answer:** _(author fills in)_
```

---

## Open

### Q1. How should commits be attributed once the bot account pushes?  (opened 2026-11-11, blocks: `docs/author_setup.md` 1.2 step 4)
**Context:** DECISIONS §9 says the author of a commit is Robert. With the
bot pushing branches and squash-merging PRs into `build/agentic`, GitHub
will show the bot as the PR author and merger. Squash-merge commits are
typically attributed to the PR's author, so the bot may also show up as
the commit author.

**Options:**
- **(a) Recommended.** Keep `git config user.name/email` as Robert on the
  agent's machine, so every commit the agent makes is authored by Robert
  and only *pushed* by the bot. When milestones are promoted to `main`,
  Robert does the merge, so `main`'s history shows Robert. The bot stays
  visible only as the PR opener on `build/agentic` PRs. Cost: the bot's
  name appears in PR lists.
- **(b)** Accept the bot as visible author/merger everywhere. It's honest
  about tooling, but it contradicts §9 as written.
- **(c)** The bot only pushes branches and opens PRs; Robert does every
  merge. Cost: every PR waits on Robert, which undoes the "agent merges"
  decision.

**Answer:** _(author fills in)_

## Answered

_(none yet)_
