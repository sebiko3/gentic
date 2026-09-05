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

- Checkpoint commits land **only** on a dedicated work branch, never on `main`, `master`, or
  whatever branch the user was already on. **Ask the helper what to call it** — the name belongs
  to the project, not to gentic:

  ```bash
  python3 "$HOME/.claude/hooks/lib/project_conventions.py" branch "<slug>"
  ```

  In a repo that has adopted gentic this prints `gentic/<slug>`; in one that has not, it prints
  the project's own dominant branch prefix, or a bare slug when it has none. If the helper is
  missing or errors, use the bare slug and carry on — it must never stop a run.
- One task, one commit. The subject comes from the same helper:

  ```bash
  python3 "$HOME/.claude/hooks/lib/project_conventions.py" commit "<slug>" "<summary>"
  ```

  Adopted repos get `gentic(<slug>): <task summary>`; everywhere else the summary is used
  plain, with no gentic wrapper in another project's history.
- **Never push and never open a PR as part of a run unless the project grants it and the
  machine trusts the project.** A project grants it in its root `CLAUDE.md` under
  `## gentic authorizations` (`push`, `open-pr`; `merge-on-green`, `deploy-preview`,
  `use-workflow-tool`, `spawn-teams` are reserved), and the user trusts the project by adding
  its git-root path to `~/.claude/gentic/trusted-projects`. Ask the script, never memory:
  `python3 "$HOME/.claude/hooks/lib/project_conventions.py" authorized push` prints `yes` or
  `no`. Without `yes` for both `push` and `open-pr`, `/ship`, typed by the user, remains the
  only path.

## The brain

gentic's memory is one SQLite file, `~/.claude/gentic/brain.sqlite` (`GENTIC_BRAIN` overrides
it). Hooks append events to it on their own; phases read and write it through
`python3 "$HOME/.claude/hooks/lib/brain.py"` as the `gentic-brain` skill describes. Nothing in
a run depends on it existing.

## Composition

Where a phase skill marks a composition point, invoke the superpowers skill named there
(`test-driven-development`, `systematic-debugging`, `verification-before-completion`,
`finishing-a-development-branch`). If superpowers is unavailable, the inline fallback rules in
each phase skill apply.

## Fibonacci discipline

- **Task sizing:** 1 / 2 / 3 / 5 / 8 points; anything larger must be split.
- **Escalation ladder:** rung costs 1 / 2 / 3 / 5 / 8.
- **Iteration budget:** 13 points per run. When it is spent the ladder escalates (rung 5, then
  rung 8, which resets it) instead of halting. Only iterate's rungs spend it; task sizes never do.

## Unconfirmed defaults

Any decision the user did not personally make — silent defaults included — is recorded as
`default — unconfirmed` in `decisions.md` and surfaced in the final report. Never quietly
adopt a judgement call.
