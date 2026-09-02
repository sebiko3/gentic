# Masterprompt: standing-authorizations

## Mission
A project can grant gentic standing permissions in its own `CLAUDE.md`, a script answers
whether an action is granted, and a run whose project grants `push` and `open-pr` ends by
following `/ship`'s steps itself and reporting the PR URL. Runs elsewhere behave exactly as
today. A hook refuses a sixth concurrent subagent, and a `STOP` file halts a run between tasks
or rungs. The workflow case of the eval suite still scores 4/4 afterwards.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- **Section format** (in the project's root `CLAUDE.md`):
  ```
  ## gentic authorizations
  - push
  - open-pr — CI is required on this repo, so a PR is safe to open
  ```
  Heading match: a line equal to `## gentic authorizations` after trimming, case-insensitive.
  The section ends at the next line starting with `## ` or at end of file. A grant is a line
  matching `^\s*[-*]\s*([a-z-]+)` whose captured word is in the vocabulary; text after the word
  (a dash, a `#`, a comment) is ignored; any other line is ignored. Vocabulary, exactly:
  `push`, `open-pr`, `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`.
- **Helper:** `.claude/hooks/lib/project_conventions.py` gains a mode `authorized`:
  `authorized <action> [--root DIR]` prints `yes` and exits 0 when granted, prints `no` and
  exits 1 otherwise — including when there is no project root, no `CLAUDE.md`, no section, or
  the word is not in the vocabulary (a message on stderr says which). `authorized --list`
  prints the granted words one per line (nothing when none) and exits 0. The existing
  `except Exception` fallback at the bottom of the file must print `no` and exit 1 for this
  mode — consent fails closed; naming keeps failing open. The root is found the same way as
  for `branch`/`commit` (`project_root`). Stdlib only, no git needed for this mode.
- **Consumers, exact wording:**
  - `.claude/skills/gentic/ROUTING.md`, the bullet at line 57 becomes: "**Never push and never
    open a PR as part of a run unless the project grants it.** A project grants it in its root
    `CLAUDE.md` under `## gentic authorizations` (words: `push`, `open-pr`; `merge-on-green`,
    `deploy-preview`, `use-workflow-tool`, `spawn-teams` are reserved for later runs). Ask the
    script, never memory: `python3 "$HOME/.claude/hooks/lib/project_conventions.py" authorized push`
    prints `yes` or `no`. Without both `push` and `open-pr` granted, `/ship`, typed by the user,
    remains the only path."
  - `.claude/skills/gentic-iterate/SKILL.md`, in `## Final report (all DoD green)`, after the
    brain `run finish` line: "Then ask the project: if
    `python3 "$HOME/.claude/hooks/lib/project_conventions.py" authorized push` and
    `… authorized open-pr` both print `yes`, follow `$HOME/.claude/commands/ship.md` end to end
    — its verification, review, push and PR steps; the checkpoint commits already exist — and
    put the PR URL in the report. If either prints `no`, the report says what `/ship` would do
    and stops there."
  - `.claude/commands/ship.md` line 8 becomes: "Nothing here fires on its own; the user typing
    `/ship` is the authorisation — or a project whose root `CLAUDE.md` grants `push` and
    `open-pr` under `## gentic authorizations`, which a gentic run checks with
    `project_conventions.py authorized` before following these steps at the end of Iterate."
    `Never merge the PR` stays.
  - `.claude/skills/gentic/SKILL.md`: after `## Status request`, a section `## Stop request`:
    "`/gentic stop <slug> [reason]` writes `docs/gentic/<run>/STOP` containing the reason (or
    `stopped by user`). `gentic-execute` checks for it before every task and `gentic-iterate`
    before every rung; a stopped run writes its handoff and ends the turn. Status lists a
    stopped run as `stopped`. Delete the file to resume."
  - `.claude/skills/gentic-execute/SKILL.md`, `## Per-task loop`, a new step 0: "**Check for
    `STOP`.** If `docs/gentic/<run>/STOP` exists, write the handoff into `progress.md` and end
    the turn; do not start the task."
  - `.claude/skills/gentic-iterate/SKILL.md`, `## On failure: diagnose, then pick a rung`, first
    sentence gains: "Before any rung, if `docs/gentic/<run>/STOP` exists, write the handoff and
    stop."
  - This repo's `CLAUDE.md`, after `## Conventions`' bullets, a section:
    ```
    ## gentic authorizations

    Standing permissions a run may use without asking again. Words: `push`, `open-pr`,
    `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`. This repository
    grants none; `/ship` is typed by hand here.
    ```
    (no bullets — the parser must yield nothing for it).
  - `README.md`: a section `## Standing authorizations` before `## Install`, showing the
    section format, the helper call, the fail-closed rule, that only `push` and `open-pr` are
    consumed today, and the STOP file.
  - `.claude/hooks/README.md`: a paragraph under Components or Design rules naming the
    concurrency valve: five concurrent foreground subagents, deny with a reason, background
    agents not counted.
- **Concurrency valve:** `pre_tool_use.py` — for `tool_name` in `{"Task", "Agent"}`, load the
  session state; if `session["agents_in_flight"]` (default 0) ≥ 5, `deny(...)` with:
  "Five subagents are already in flight. Wait for one to return before spawning another —
  runaway fan-out is how a run burns its budget without converging." Otherwise increment and
  save. `post_tool_use.py` — for the same tools, decrement (floor 0) and save. Both use the
  existing `common.load_state`/`save_state` and the `session` sub-dict (survives turns). The
  agentignore checks stay first for file tools; this branch runs before the Bash branch. No
  brain event. The `subagent_type` review signal in `post_tool_use.py` is unchanged.
- **Tests:**
  - `tests/test_project_conventions.py`: `test_authorized_reads_the_section` (a repo whose
    `CLAUDE.md` grants `push` and `open-pr — comment` → `authorized push` yes/0, `authorized open-pr`
    yes/0, `authorized merge-on-green` no/1, `authorized --list` prints `push\nopen-pr`);
    `test_authorized_fails_closed` (no section → no/1; no `CLAUDE.md` → no/1; unknown word
    `deploy` → no/1; a section with the word inside prose but not as a bullet → no/1).
  - `tests/test_guard_and_session.py`: `test_concurrency_valve_denies_a_sixth_agent` (five
    PreToolUse `Task` payloads pass, the sixth is denied with `in flight` in the reason; one
    PostToolUse `Task` payload then lets a spawn pass).
  - `tests/test_structure.py`, class `StandingAuthorizations`: lowered-text needles —
    ROUTING.md: `'## gentic authorizations'` and `'authorized push'`; gentic-iterate:
    `'authorized open-pr'` and `'ship.md'` and `'stop'`; ship.md: `'gentic authorizations'`;
    gentic-execute: `'check for `stop`'`; gentic/SKILL.md: `'## stop request'`; root
    `CLAUDE.md`: `'## gentic authorizations'`; README: `'## standing authorizations'`; hooks
    README: `'in flight'`.
- **Regression gate:** after `./install.sh` and `--check` exit 0,
  `python3 evals/run.py --case csv-export-probe --arm with` must score 4/4 (n=1); pasted.
  ≈ 2.5 USD.
- Lessons carried: `-k` patterns are substrings of contract test names; no double-quoted
  `.claude` literal in a hook without `Path.home()` on the same line (the deny reason above
  contains none); commit from the repo root with absolute paths.
- Environment: Claude Code 2.1.258, macOS, Python 3.13.

## Decisions (inlined; all `user — delegated`)
Grants in the project's `CLAUDE.md`; fixed vocabulary; fail closed; first consumer is the
Iterate final report following `commands/ship.md`; `/ship` wording admits the second caller;
valve at 5 as a cap, foreground only; `STOP` file via `/gentic stop`; this repo grants nothing;
one live regression run of the workflow case; budget currency deferred.

## Constraints
- Stdlib only; hooks stay under 150 ms; no new brain tables.
- The wording sites are exactly those in Context; no other skill, agent or doc changes.
- `/ship`'s "Never merge", "Never force-push" and all preconditions are unchanged.
- Every task test-first; observed RED in `progress.md`.

## Non-goals
- No consumer for `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`.
- No budget currency (`gentic-epic`); no counting of background agents; no hook for STOP.
- No eval case for authorizations (needs a remote and `gh`); the helper is unit-tested.
- No CI; no change to `install.sh`; no full suite run (workflow case only).

## Definition of Done
- [ ] H1 Helper reads grants. As in Context.
      verify: `python3 .claude/hooks/tests/test_project_conventions.py -k authorized_reads`
      contract: tests/test_project_conventions.py · test_authorized_reads_the_section ·
      expected RED: `AssertionError: 2 != 0 : authorized push` (argparse rejects the mode)
- [ ] H2 Helper fails closed. As in Context.
      verify: `python3 .claude/hooks/tests/test_project_conventions.py -k fails_closed`
      contract: tests/test_project_conventions.py · test_authorized_fails_closed ·
      expected RED: `AssertionError: 2 != 1 : no section must be a no`
- [ ] H3 Valve. Sixth concurrent spawn denied; a return frees a slot.
      verify: `python3 .claude/hooks/tests/test_guard_and_session.py -k concurrency_valve`
      contract: tests/test_guard_and_session.py · test_concurrency_valve_denies_a_sixth_agent ·
      expected RED: `AssertionError: 0 != 2 : sixth spawn was not denied`
- [ ] H4 Wording in place. All needles in the `StandingAuthorizations` class.
      verify: `python3 .claude/hooks/tests/test_structure.py -k StandingAuthorizations`
      contract: tests/test_structure.py · StandingAuthorizations (six tests, one per file group) ·
      expected RED: `AssertionError: 'authorized push' not found in …`
- [ ] H5 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 and prints
      `ok    test_project_conventions`, `ok    test_guard_and_session`, `ok    test_structure`.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of H1–H4's tests.
- [ ] H6 Regression gate. `./install.sh --check` exit 0; `python3 evals/run.py --case csv-export-probe --arm with`
      prints `csv-export-probe  with 4/4 (1.00)`; pasted with the suite id, cost and turn count.
      verify: run it; paste
      contract: no test contract — a live observation; n=1.
- [ ] H7 This repo still grants nothing. `python3 .claude/hooks/lib/project_conventions.py authorized --list`
      from the repo root prints nothing, exit 0; `authorized push` prints `no`, exit 1.
      verify: run both; paste
      contract: covered by H1's parser tests over the same section shape; the live check is
      the observation.

## Risks & early signals
- The Iterate wording adds a path that pushes; the regression gate and the fail-closed helper
  are the guards. In the eval workspace the section is this repo's (copied `CLAUDE.md`), which
  grants nothing, so the probe never pushes.
- `argparse` positional `action` versus `--list` flag: give `authorized` an optional positional
  with `nargs="?"` and a `--list` flag.

## Task order (for Execute)
1. Helper `authorized` mode + tests — H1, H2.
2. Valve in both hooks + test — H3.
3. Wording in the seven files + structure tests; hooks README; README — H4.
4. Harness — H5; install; regression run — H6; H7.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
