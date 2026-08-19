# gentic routing — machine-wide

The gentic repo carries these rules in its project `CLAUDE.md`. That file does not exist in
other projects, so the rules live here instead and apply everywhere.

## When to run gentic

Invoke the `gentic` skill BEFORE any implementation when the task has **any** of:

- multiple files, steps, or sessions of work
- ambiguous requirements, or vague adjectives doing load-bearing work ("fast", "simple", "robust")
- consequences beyond the diff: other people's data, security, money, public interfaces
- an explicit `/gentic` invocation, or talk of resuming earlier deep work

Skip gentic only for genuinely trivial work: a single obvious change or a pure question.
**Diff size does not decide — a one-route change that exports user data is non-trivial.**
When unsure, run gentic; phases may be short, never absent.

The `UserPromptSubmit` hook (`~/.claude/hooks/user_prompt_submit.py`) flags likely candidates
automatically, but it is advisory and deliberately conservative. Its silence is not a ruling
that a task is trivial.

## Where run artifacts go

1. **Default** — `docs/gentic/<YYYY-MM-DD>-<slug>/` inside the repo, committed. Artifacts are
   documentation, not scratch.
2. **Fallback** — when the repo is not ours to add files to (a fork, a vendored tree, a
   read-only checkout, or the user says so), use
   `~/.claude/gentic-runs/<repo-name>/<YYYY-MM-DD>-<slug>/` instead, and say so in the final
   report so the artifacts can be found later.
3. **No git repo** — always the `~/.claude/gentic-runs/` fallback.

## Commits during a run

Entering Execute is the explicit request that authorises checkpoint commits — but only under
these limits, which exist because `~/.claude/CLAUDE.md` otherwise forbids unrequested commits:

- Checkpoint commits land **only** on a `gentic/<slug>` branch. Create it before the first
  commit. **Never commit to `main`, `master`, or whatever branch the user was already on.**
- One task, one commit: `gentic(<slug>): <task summary>`.
- **Never push and never open a PR as part of a run.** That is `/ship`'s job, and `/ship` only
  runs when the user types it.

## Composition

Where a phase skill marks a composition point, invoke the superpowers skill named there
(`test-driven-development`, `systematic-debugging`, `verification-before-completion`,
`finishing-a-development-branch`). If superpowers is unavailable, the inline fallback rules in
each phase skill apply.

## Fibonacci discipline

- **Task sizing:** 1 / 2 / 3 / 5 / 8 points; anything larger must be split.
- **Escalation ladder:** rung costs 1 / 2 / 3 / 5 / 8.
- **Iteration budget:** 13 points per run. Only iterate's rungs spend it; task sizes never do.

## Unconfirmed defaults

Any decision the user did not personally make — silent defaults included — is recorded as
`default — unconfirmed` in `decisions.md` and surfaced in the final report. Never quietly
adopt a judgement call.
