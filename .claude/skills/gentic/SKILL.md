---
name: gentic
description: Use when starting any non-trivial, multi-step, or ambiguously specified task; when the user invokes /gentic; or when the user wants to resume, continue, or check status of earlier deep work. Symptoms that call for it - requirements unclear, work spans many files, done-ness is fuzzy, or the task could outlive one context window.
---

# Gentic — Deep Workflow Orchestrator

## Overview

Gentic turns a vague request into verified, done work through five gated phases. Every phase writes a durable artifact to disk, so any future session can resume exactly where the last one stopped. You are the state machine: read state, run the current phase's skill, check its gate, advance.

**Core principle: no phase before Execute produces code, and no phase is skipped once a run starts.**

**Read `ROUTING.md` in this skill's directory first.** It carries the machine-wide rules that the
gentic repo keeps in its project `CLAUDE.md` — where artifacts go when the repo is not ours, and the
hard limits on committing during a run (a dedicated work branch only, named by the project's own
convention via `project_conventions.py`; never push, never open a PR).

## Phase map

| # | Phase | Skill | Artifact | Gate to advance |
|---|-------|-------|----------|-----------------|
| 1 | Scout | gentic-scout | `brief.md` | Facts grounded in repo; every open decision has a recommended default |
| 2 | Interview | gentic-interview | `decisions.md` | Every open decision resolved (by user) or defaulted (flagged) |
| 3 | Masterprompt | gentic-masterprompt | `masterprompt.md` | Critique pass done; every Definition of Done item names its check and its test contract |
| 4 | Execute | gentic-execute | task table in `progress.md` | All tasks checked off, each with observed RED evidence and a checkpoint commit |
| 5 | Iterate | gentic-iterate | iteration log in `progress.md` | Every Definition of Done item verified with evidence |

## Starting a run

1. Derive a short kebab-case slug from the request (e.g. `add-user-auth`).
2. Create the run directory: `docs/gentic/<YYYY-MM-DD>-<slug>/` (today's date).
3. Write `progress.md` in it from the template below.
   Open the run in the brain (`gentic-brain`): `python3 "$HOME/.claude/hooks/lib/brain.py" run start <slug> --goal "<goal>"`,
   then `stamp <slug>` the skill and agent files this run will use.
4. Invoke `gentic-scout` with the Skill tool. Follow each phase skill exactly.
5. Between phases: verify the gate from the table above, tick the phase box in `progress.md`, commit the run directory (subject from `project_conventions.py commit`: `gentic(<slug>): <phase> gate` in an adopted repo, `<phase> gate` elsewhere), then invoke the next phase's skill. During Execute, progress ticks ride inside each task's checkpoint commit instead. After Execute, `gentic-iterate` owns control flow until the run is done or stopped — it may re-enter earlier phases via its escalation ladder.

## Resuming a run

1. Find the newest `docs/gentic/*/progress.md` with unchecked items (or the one the user names).
2. Read every artifact in that run directory before doing anything else. They are your restored context — trust them over memory of the conversation.
3. Re-enter at the first unchecked phase. If Execute was interrupted mid-task, `git log` shows which checkpoints landed; uncommitted changes belong to the first unticked task — re-run that task's test, keep what it proves, reset the rest.
4. If the repo changed since the run's last artifact commit, have `gentic-scout` drift-check the brief (append corrections; never untick phases).

## Status request

Read all `docs/gentic/*/progress.md`, report each run's goal, current phase, tasks done/total, budget remaining, and any handoff note. No other action.

## progress.md template

```markdown
# Run: <slug>
Goal: <one line>
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [ ] 1 Scout
- [ ] 2 Interview
- [ ] 3 Masterprompt
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
```

## Red flags — stop and re-read this skill

- "This part seems clear enough, I'll skip Interview" — routing decides *whether* gentic runs (see CLAUDE.md); once it runs, every phase runs. Phases may be *short*, never absent.
- "I'll fix the artifact by hand" — if a gate fails, re-run the phase skill; artifacts are outputs of phases, not scratch files.
- "I remember the context, no need to re-read artifacts" — after resume or compaction, memory is the thing that failed. Artifacts are the source of truth.
- Starting a second goal inside an existing run — one run directory per goal; new goal, new run.
