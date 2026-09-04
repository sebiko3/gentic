# Brief: standing-authorizations

## Mission (as understood)
"One short prompt does everything" collides with two standing rules: `~/.claude/CLAUDE.md`
forbids commits, pushes and PRs unless asked, and ROUTING.md says a run never pushes and never
opens a PR — only a user-typed `/ship` does. Both rules are right; what is missing is a way for
the user to *ask once, durably, per project*. This run adds that: a `## gentic authorizations`
section in the project's `CLAUDE.md`, a helper that answers `authorized <action>` from a
script rather than from memory, and the first consumer — a run whose project grants `push` and
`open-pr` finishes by following `/ship`'s steps itself. Two safety pieces from the epic brief
ride along: a hook valve that refuses a sixth concurrent subagent, and a `STOP` file every
phase checks so a run can be halted from outside.

## Facts
- `~/.claude/CLAUDE.md` Version Control: "Do not commit, push, create pull requests … unless
  explicitly asked." ROUTING.md:57: "**Never push and never open a PR as part of a run.** That
  is `/ship`'s job, and `/ship` only runs when the user types it." `commands/ship.md:8`: "the
  user typing `/ship` is the authorisation"; `:115` "Never merge the PR".
- `lib/project_conventions.py` is the precedent for a deterministic per-project answer: argparse
  CLI, `--root`, `is_adopted()` reads the root `CLAUDE.md` for a literal marker, fails *open*
  to a bare slug because naming must never stop a run. Authorizations must fail **closed**.
- `tests/test_project_conventions.py` has `helper(*args, root=)` and `make_repo(claude_md=)`
  fixtures; `test_structure.py` holds wording contracts; `test_guard_and_session.py` drives
  `pre_tool_use.py` with payloads.
- `post_tool_use.py:60` `SUBAGENT_TOOLS = {"Task", "Agent"}`; the pre hook has no subagent
  branch. PreToolUse fires when a subagent is spawned, PostToolUse when the tool call returns —
  for a background agent that is immediately, so an in-flight count sees foreground fan-out only.
- `gentic/SKILL.md:46` has a Status request section and no stop command; `gentic-execute`'s
  per-task loop and `gentic-iterate`'s rung loop have no external stop check.
- This repo's `CLAUDE.md` has Routing, Conventions, Test-first spine, Fibonacci, Composition
  sections; the adoption marker `gentic/<slug>` lives in Conventions (`:21`).
- The suite (`evals/run.py`) is the regression gate for any skill wording change; the workflow
  case alone costs ≈ 2.5 USD (`--case csv-export-probe --arm with`).

## Patterns to follow
- Deterministic helper + CLI, consumed by skills through a literal command (`project_conventions.py`).
- Contract tests for every wording change; hook tests with payloads; fail closed for consent.
- Fibonacci: valve at 5 concurrent agents.
- One live regression check of the workflow case after the skill edits.

## Constraints discovered
- The grant must live where the user edits and git reviews: the project's root `CLAUDE.md`.
  Machine-wide grants would authorise pushes in repos the user never meant (epic decision).
- `merge-on-green` and `deploy-preview` need CI and deploy machinery (R6); this run reserves the
  words and consumes only `push` and `open-pr`. `use-workflow-tool` and `spawn-teams` are
  reserved for R8.
- The valve cannot see background agents; documented, not solved.

## Open decisions (all resolved by delegation — see decisions.md)
1. Section format — heading `## gentic authorizations`, one bullet per action from a fixed
   vocabulary, anything else ignored. Default: as stated.
2. Fail direction — absent file/section/root or unknown action ⇒ `no`, exit 1. Default: closed.
3. First consumer — `gentic-iterate`'s final report follows `commands/ship.md` when both `push`
   and `open-pr` are granted. Default: yes.
4. Valve — deny a spawn when five subagents are in flight; not a once-per-session valve but a
   cap, like the agentignore guard. Default: 5, cap.
5. STOP — a `STOP` file in the run directory, written by `/gentic stop <slug> [reason]`, checked
   before each task and each rung. Default: as stated.
6. This repo's own grants — the section exists with no grants (`/ship` stays hand-typed here).
   Default: as stated.
