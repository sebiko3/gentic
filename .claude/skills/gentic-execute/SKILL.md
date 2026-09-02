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
4. Write the table into `progress.md`. If still on the default branch, create a work branch now — checkpoints never land on main. Get its name from the helper, because the convention belongs to the project rather than to gentic: `python3 "$HOME/.claude/hooks/lib/project_conventions.py" branch "<slug>"`. An adopted repo gets `gentic/<slug>`; any other project gets its own prefix, or a bare slug. If the helper errors, use the bare slug and continue.

## Per-task loop

1. **Invoke `gentic-tdd` and follow it.** It carries the Iron Law — no production code without a failing test first — and the rules for tasks with no executable behaviour. Every task goes through it; there is no fast path for small ones.
2. Take the task's test from the masterprompt: the DoD item it serves already names the test file, the test name and the failure to expect. If reality contradicts that contract, that is drift — see below.
3. Watch the test fail, and **paste the actual failure into the task's `RED` cell** in `progress.md`. A trimmed assertion message is enough; invented text is not.
4. Implement the smallest change that passes.
5. Verify locally (task's tests + suite affected by the change).
6. Tick the task's Status in `progress.md`. **A task with an empty `RED` cell is not done** — the cell, not your memory, is what a resumed session reads. `n/a` is legal only for a task that changes nothing observable, and must carry its reason.
7. Checkpoint commit, one task per commit. Subject from `python3 "$HOME/.claude/hooks/lib/project_conventions.py" commit "<slug>" "<summary>"` — `gentic(<slug>): <task summary>` in an adopted repo, the plain summary in any other project.

## When blocked on a missing decision

Never improvise silently. If interactive: a single AskUserQuestion call (a mini-interview — gentic-interview's question-craft rules apply, but one call, not the round system). If autonomous: adopt the most conservative option consistent with the masterprompt, append it to `decisions.md` as `default — unconfirmed`, and continue.

A blocker, a surprise, or a number that was hard to find is worth a `note` in the brain
(`gentic-brain`) — the next run in this project will `recall` it before scouting.

## Drift rule

- Reality invalidates the *plan* (wrong task breakdown, wrong estimate): update the task table and keep going. Note it in `progress.md`.
- Reality invalidates the *spec* (a Decision or DoD item is wrong): stop executing. That is rung 5 territory — invoke gentic-iterate for a direct rung-5 entry.

## Optional parallelism

Independent tasks of 3+ points may be dispatched to subagents when available. Never parallelize dependent tasks, and never fan out before the riskiest task has landed — cheap course correction is worth more than concurrency.

Dispatch `task-executor`, one instance per task, under this contract. A fan-out without it produces several incompatible readings of the same spec, which costs more to reconcile than it saved.

**Receives:** the full `masterprompt.md` (not a summary — the non-goals are what stop it over-building), exactly one task from the table, the DoD items that task serves, its verification command, and the files it owns. Anything missing is the parent's bug, not the worker's.

**Returns:** the fixed report block in the agent's own definition — `status`, files changed, the test written, the RED failure observed, the GREEN command with its real output, the broader suite result, non-goals honoured, and anything noticed but not fixed. A `done` without a `green` line containing real output is not `done`.

**Parent merges by:** re-running each worker's verification command itself before believing it, then running the full affected suite once over the combined result — a worker's green proves its own change, not the merge. Then tick the task table and make one checkpoint commit per task, in dependency order. Workers never commit; the parent owns history. A `blocked` or `assignment unclear` return means the task breakdown was wrong: fix the table before re-dispatching, never re-send the same brief.

**Isolation required when:** two concurrently dispatched tasks can touch the same file, or a task runs a build, migration, or generator that writes outside its owned paths. Give those workers a git worktree each. Tasks with provably disjoint file sets may share the tree.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Batching several tasks into one commit | One task, one commit — resume depends on it |
| Pushing through when the spec is wrong | Spec drift is iterate's job; executing a wrong spec is negative work |
| Silent judgment calls on blockers | Every unplanned decision lands in decisions.md, flagged |
| Marking a task done because code exists | Done = its test failed first, then passed; evidence, not existence |
| Ticking a task with an empty RED cell | The evidence is the deliverable; go back and watch the test fail |
| Writing the test after, "to save a step" | A test written after passes immediately and proves nothing |
