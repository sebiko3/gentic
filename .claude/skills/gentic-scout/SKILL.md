---
name: gentic-scout
description: Use when a gentic run is starting and no brief.md exists yet, or when re-entering a run after context loss and the codebase may have drifted from the brief. Also use before asking any clarifying question, to ensure the repo cannot already answer it.
---

# Gentic Scout — Ground Before Asking

## Overview

Scout makes the Interview phase worth having: questions asked from ignorance are generic; questions asked from evidence are sharp. Explore the environment just enough to know what is already decided by reality, then write `brief.md` in the run directory.

**Core principle: never leave a decision open that the repo can settle.**

## Method

0. **Ask the brain first** (`gentic-brain`): `recall <words from the request>` and `lessons`.
   A hit is a Fact, cited as `brain #<id>` — earlier runs in this project already paid for it.
1. **Shallow first.** Project layout, README, manifest/config files, recent commits. What kind of project is this, what conventions does it already have?
2. **Deepen only where the request points.** Read the files the task will touch and their tests. Note patterns to imitate, with `file:line` references.
3. **Time-box.** If ~13 tool calls pass without a new load-bearing fact, stop and write the brief with what you have.
4. **Greenfield variant.** If the repo is empty or the task is new-territory, scout the *ecosystem* instead: what the platform provides, what conventions the user's global config implies, what constraints tools impose.
5. **Runnable product variant** — only when the request touches a user-facing surface (a
   screen, a page, a flow someone clicks); a run that touches no UI skips this step. If the
   project says how to run itself (a `dev`/`start` script, `python3 app.py`, a README
   instruction), start it — the in-app Browser's `preview_start` when the project already has
   a `.claude/launch.json` entry, otherwise the project's command in the background — open it
   in Claude in Chrome (fallback: the in-app Browser), walk at most 8 routes starting from the
   ones the request names, save at most 5 half-scale screenshots under
   `docs/gentic/<run>/evidence/scout-<n>.png`, and write a **Feature inventory** section in
   the brief: one line per screen with what it shows and what the request needs that is
   missing. Never screenshot a production or authenticated surface or real personal data; use
   the project's own fixture or seed data, or skip the screenshot and say so. Time-box: 13
   tool calls for the whole variant.

## brief.md template

```markdown
# Brief: <slug>

## Mission (as understood)
<one paragraph restating the request in your own words>

## Facts
- <fact> (<file:line> or source)

## Patterns to follow
- <existing convention worth imitating> (<file:line>)

## Constraints discovered
- <hard limits: versions, APIs, style rules, user preferences>

## Open decisions (ranked by leverage)
1. <decision> — options: <A/B>; recommended default: <X> because <reason>
```

## Rules

- Every open decision **must** ship with a recommended default and a reason. The Interview and any non-interactive run depend on these defaults existing.
- Rank open decisions by leverage: how much the answer changes what gets built.
- Facts without references are hearsay — cite `file:line`, a command you ran, or the config that says so.
- Drift check (on resume): verify each Fact and Constraint still holds; append dated corrections rather than rewriting history.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Dumping file listings into the brief | Record *conclusions* (facts, patterns), not raw output |
| Open decision with no default | Add your recommendation and reasoning — that is the phase's main product |
| Scouting indefinitely to feel thorough | Time-box; the Interview and Iterate phases catch what scouting missed |
| Asking the user something a file answers | Check the repo first; the Interview only gets questions reality cannot settle |
