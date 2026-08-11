---
name: gentic-execute
description: Use when a gentic run has a critiqued masterprompt.md and tasks remain unplanned or unchecked in progress.md. Also use when resuming interrupted implementation work after a context loss or session break.
---

# Gentic Execute — Small Verified Steps, Checkpointed

## Overview

Execute turns the masterprompt into a task plan, then delivers it one verified, committed step at a time. All state lives in the `progress.md` task table, so an interrupted run resumes cleanly.

**Core principle: the run directory and git history, not your memory, carry the state.**

## Planning (first entry only)

1. Derive tasks from the masterprompt's Definition of Done — every DoD item must be covered by at least one task.
2. Size each task in fibonacci points: 1, 2, 3, 5, or 8. **A task estimated above 8 must be split** — if it can't be split, the masterprompt is under-specified (return to it). Sizes are planning estimates only; they never deduct from the iteration budget (only gentic-iterate's rungs spend that).
3. Order by dependencies first, then riskiest-first: do the task most likely to invalidate the plan early, while changing course is cheap.
4. Write the table into `progress.md`. If still on the default branch, create `gentic/<slug>` now — checkpoints never land on main.

## Per-task loop

1. **Failing test first.** If superpowers:test-driven-development is available, you MUST invoke it. Otherwise the inline rule holds: write the test, watch it fail, then implement.
2. Implement the smallest change that passes.
3. Verify locally (task's tests + suite affected by the change).
4. Tick the task's Status in `progress.md`.
5. Checkpoint commit: `gentic(<slug>): <task summary>`. One task, one commit.

## When blocked on a missing decision

Never improvise silently. If interactive: a single AskUserQuestion call (a mini-interview — gentic-interview's question-craft rules apply, but one call, not the round system). If autonomous: adopt the most conservative option consistent with the masterprompt, append it to `decisions.md` as `default — unconfirmed`, and continue.

## Drift rule

- Reality invalidates the *plan* (wrong task breakdown, wrong estimate): update the task table and keep going. Note it in `progress.md`.
- Reality invalidates the *spec* (a Decision or DoD item is wrong): stop executing. That is rung 5 territory — invoke gentic-iterate for a direct rung-5 entry.

## Optional parallelism

Independent tasks of 3+ points may be dispatched to subagents when available. Each subagent gets: the full `masterprompt.md`, its single task, and the instruction to return evidence of verification. Use worktree isolation if tasks touch overlapping files. Never parallelize dependent tasks.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Batching several tasks into one commit | One task, one commit — resume depends on it |
| Pushing through when the spec is wrong | Spec drift is iterate's job; executing a wrong spec is negative work |
| Silent judgment calls on blockers | Every unplanned decision lands in decisions.md, flagged |
| Marking a task done because code exists | Done = its test passed; evidence, not existence |
