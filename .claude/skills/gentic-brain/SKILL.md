---
name: gentic-brain
description: Use when something is worth remembering or recalling across sessions and projects — note a fact, recall earlier notes, decide and learn the user's preferences, record a lesson from a failed Definition-of-Done item, stamp the skill versions a run used, or query the brain with SQL. Also use at the start of any gentic phase to check what the brain already knows.
---

# Gentic Brain — Memory You May Use As You Like

## Overview

One SQLite file holds everything gentic remembers: `~/.claude/gentic/brain.sqlite`
(`GENTIC_BRAIN` overrides the path). The hooks write into it on their own; you write everything
else, through one command:

```bash
python3 "$HOME/.claude/hooks/lib/brain.py" <command> …
```

(In the gentic repository itself: `python3 .claude/hooks/lib/brain.py`.) There is no `brain`
alias on PATH. Every row carries a project key — the basename of the git root — so the same
file serves every repository on the machine. Outside a git repository, pass `--project <name>`.

**Core principle: the brain is yours. Anything the tables cannot hold goes in a note or in a
table you create with `sql`. Empty output means "nothing known", never an error.**

## Commands — the whole set

| Command | Does |
|---------|------|
| `note <key> <text…> [--tags a,b] [--run slug]` | Store a free-form note for this project |
| `recall <words…> [--limit 8] [--all]` | Notes containing every word (key or body), newest first |
| `decide <topic> <chosen…> --source user\|default\|learned` | Record a decision and its provenance |
| `preference <topic>` | Print the user's learned answer, exit 1 if none (see rule below) |
| `lesson --item … --rung N --points P --caught-by … --cause … [--note …]` | What a failed DoD item taught |
| `lessons [--all] [--limit 21]` | Lessons for this project, newest first |
| `stats [--all]` | Counts: lessons by what caught them, points, notes, preferences, events |
| `run start <slug> --goal …` / `run finish <slug> --outcome done\|stopped` | A run's lifecycle |
| `stamp <slug> <paths…>` | sha256 of each file, so a lesson can be tied to a skill version |
| `prune [--events-days 89] [--sessions-days 8]` | Delete hook events and idle sessions past their retention — every project |
| `sql "<one statement>"` | Anything. SELECT prints one JSON object per row |

`--caught-by` names who found the defect: `suite`, `live`, `review`, `critic`, `auditor`, `user`.

## Where each phase uses it

- **gentic (starting a run)** — `run start <slug> --goal "…"`, then
  `stamp <slug> "$HOME"/.claude/skills/gentic*/SKILL.md "$HOME"/.claude/agents/*.md`.
- **gentic-scout** — before exploring: `recall <words about the task>` and `lessons`. A hit is
  a Fact for the brief; cite it as `brain #<id>`.
- **gentic-interview** — for each open decision, `preference <topic>` first. A learned answer
  is adopted with Source `learned` and is not asked. Every answer the user gives is recorded:
  `decide <topic> <chosen> --source user`.
- **gentic-masterprompt** — record unconfirmed defaults with `decide … --source default`.
  Defaults never teach a preference, but they stay visible.
- **gentic-execute** — a blocker, a surprise, a number that was hard to find: `note` it.
- **gentic-iterate** — every rung spent is a `lesson`; the final report ends with
  `run finish <slug> --outcome done`, a handoff with `--outcome stopped`.

## What the hooks record without asking

`post_tool_use` appends a `red` or `verification` event for every recognised test, lint or
build command, tagged with the project's open run (`events.run`), so a run's RED/GREEN history
is one query: `sql "select kind, detail from events where run = '<slug>'"`. Those two kinds
are the only ones a hook writes. The concurrency valve keeps its per-session counter in the
`sessions` table (`user_prompt_submit` resets it, `pre_tool_use` takes a slot, `post_tool_use`
frees one). `session_start` prunes events older than 89 days and sessions idle for 8, silently.
Credentials in commands are scrubbed before storage. A brain that cannot be opened is
silently skipped — the hooks never slow down or fail because of it.

## The preference rule

`preference <topic>` prints a value only when the user's **most recent** `user`-sourced
decision on that topic has been chosen at least twice. One answer is an accident; two is a
preference; a changed mind resets the count. Preferences describe the user, so they are
learned across projects. `default` and `learned` rows never count — the brain must not
confirm its own guesses.

## Rules

- `sql` is unrestricted. Before a `DROP`, `DELETE`, `UPDATE` or `ALTER`, the file is copied to
  `brain.sqlite.bak` — one level of undo, overwritten each time.
- Never `note` a secret. Scrubbing covers hook events only.
- The schema is versioned (`PRAGMA user_version`, `brain.SCHEMA_VERSION`). An older brain is
  upgraded in place on first open by additive, guarded migrations; existing rows are never
  rewritten. Never delete the file to "fix" a shape.
- The brain is not a run artifact. `progress.md` and friends remain the source of truth for a
  run; the brain is what carries across runs.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Asking the user a question the brain already answers | `preference <topic>` first; Source `learned` |
| Recording a default with `--source user` | Provenance is the point; defaults are `--source default` |
| Treating empty `recall` output as an error | Empty means nothing known; scout normally |
| Writing lessons into `progress.md` only | The artifact serves this run; the `lesson` row serves the next one |
| Inventing a `brain` alias | There is none; use the `python3 "$HOME/.claude/hooks/lib/brain.py"` form |
