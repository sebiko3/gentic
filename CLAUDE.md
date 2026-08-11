# gentic

Spec-first, resumable deep workflow for Claude Code. Five gated phases — Scout → Interview → Masterprompt → Execute → Iterate — each writing a durable artifact under `docs/gentic/<date>-<slug>/`, so any session can resume any run.

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
- Any decision the user didn't personally make — silent defaults included — is flagged `default — unconfirmed` and surfaced in the final report.

## Fibonacci discipline

Fibonacci numbers are the workflow's balancing mechanism, not decoration:

- **Task sizing:** 1 / 2 / 3 / 5 / 8 points; anything larger must be split.
- **Escalation ladder:** rung costs 1 / 2 / 3 / 5 / 8 — deeper backtracking costs more because it discards more work.
- **Iteration budget:** 13 points per run — affords many small fixes or one spec re-opening, never endless fiddling. Only iterate's rungs spend it; task sizes never do.

## Composition

If the superpowers plugin is installed, gentic phases invoke its skills at the marked points (test-driven-development, systematic-debugging, verification-before-completion, finishing-a-development-branch). Without it, the inline fallback rules in each phase skill apply. Either way the workflow is complete.
