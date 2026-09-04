# gentic

Spec-first, test-first, resumable deep workflow for Claude Code. Five gated phases — Scout → Interview → Masterprompt → Execute → Iterate — each writing a durable artifact under `docs/gentic/<date>-<slug>/`, so any session can resume any run.

## Routing — decide this before touching anything

Invoke the `gentic` skill (Skill tool) BEFORE any implementation when the task has **any** of:

- multiple files, steps, or sessions of work
- ambiguous requirements, or vague adjectives doing load-bearing work ("fast", "simple", "robust")
- consequences beyond the diff: other people's data, security, money, public interfaces
- an explicit `/gentic` invocation, or talk of resuming/continuing earlier deep work

Skip gentic only for genuinely trivial work: a single obvious change or a pure question. **Diff size does not decide — a one-route change that exports user data is non-trivial.** When unsure, run gentic; phases may be short, never absent.

At session start, if the user references past work, check `docs/gentic/*/progress.md` for unfinished runs before starting fresh.

## Conventions

- Run artifacts (`brief.md`, `decisions.md`, `masterprompt.md`, `progress.md`) are committed — they are documentation, not scratch.
- Runs execute on a `gentic/<slug>` branch, never on main.
- Checkpoint commits: `gentic(<slug>): <task summary>`, one task per commit.
- Never edit a Definition of Done item to make it pass; spec changes go through the rung-5 escalation in `gentic-iterate`.
- Every task goes through `gentic-tdd`: the test comes first, its observed failure goes in the task's `RED` cell, and a task with an empty `RED` cell is not done.
- Any decision the user didn't personally make — silent defaults included — is flagged `default — unconfirmed` and surfaced in the final report.

## gentic authorizations

Standing permissions a run may use without asking again, honoured only when this repository's
path is also in the machine's `~/.claude/gentic/trusted-projects`. Words: `push`, `open-pr`,
`merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`. This repository grants
none; `/ship` is typed by hand here.

## Test-first spine

The spec designs the tests and the tests gate the work — the two halves are one mechanism:

- **Masterprompt** — every Definition of Done item names a *test contract*: the test file, the test name, the behaviour asserted, and the expected RED. An item with a verify command but no contract is checking work it never designed.
- **Execute** — `gentic-tdd` owns the per-task loop. No production code without a failing test first; the real failure text is pasted into `progress.md`, because a resumed session can read the artifact and not your memory.
- **Docs and prompts count as behaviour.** Their test is a contract test in the project's suite (`.claude/hooks/tests/test_structure.py` is the pattern here). `n/a` is only for a task that changes nothing observable, and must state why.
- **The hooks notice, they do not police.** The ledger records failing verification runs as RED evidence and flags a turn that changed production code with no test touched and no failure seen. It is advisory and fires once per session; the verification gate remains the only hard block.

## Fibonacci discipline

Fibonacci numbers are the workflow's balancing mechanism, not decoration:

- **Task sizing:** 1 / 2 / 3 / 5 / 8 points; anything larger must be split.
- **Escalation ladder:** rung costs 1 / 2 / 3 / 5 / 8 — deeper backtracking costs more because it discards more work.
- **Iteration budget:** 13 points per run — affords many small fixes or one spec re-opening, never endless fiddling. Only iterate's rungs spend it; task sizes never do.

## Composition

If the superpowers plugin is installed, gentic phases invoke its skills at the marked points (test-driven-development, systematic-debugging, verification-before-completion, finishing-a-development-branch). Without it, the inline fallback rules in each phase skill apply. Either way the workflow is complete.
