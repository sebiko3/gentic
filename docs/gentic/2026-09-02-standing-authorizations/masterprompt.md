# Masterprompt: standing-authorizations

## Mission
A project can grant gentic standing permissions in its own `CLAUDE.md`, the user confirms the
project once on the machine, a script answers whether an action is granted, and a run whose
project grants `push` and `open-pr` ends by following `/ship`'s steps itself and reporting the
PR URL. Projects that grant nothing keep today's push/PR behaviour exactly; the concurrency
valve and the STOP check apply everywhere. A hook refuses a sixth concurrent foreground
subagent, and a `STOP` file halts a run between tasks or rungs. The workflow case of the eval
suite still scores 4/4 afterwards.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
### Trust model (the credential-touching part)
`CLAUDE.md` travels with a clone, so a grant inside it must never be enough on its own: any
repository could otherwise push branches and open PRs with the user's `gh` credentials. A
grant is honoured only when **both** hold:
1. the project's root `CLAUDE.md` (the git root's only; nested files are not consulted) lists
   the action under `## gentic authorizations`, and
2. the git root's absolute path appears, one per line, in the machine-side trust file
   `~/.claude/gentic/trusted-projects` — a file the user creates by hand; nothing in this repo,
   the installer, or a run ever writes it. `GENTIC_TRUST` overrides its path (tests).
`authorized` prints `no` when either is missing and says which on stderr. This repository's
own path is not in the user's trust file at the end of this run (H7).

### Section format
```
## gentic authorizations
- push
- open-pr — CI is required on this repo, so a PR is safe to open
```
Heading: a line equal to `## gentic authorizations` after trimming, case-insensitive; the
section ends at the next line starting with `## ` or at end of file. A grant is a line matching
`^\s*[-*]\s*([A-Za-z-]+)` whose word, lowercased, is in the vocabulary; text after the word is
ignored; a bullet whose word is not in the vocabulary is reported on stderr as `ignored:
<word>` and otherwise ignored; non-bullet lines are ignored. Vocabulary, exactly: `push`,
`open-pr`, `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`. The last four
are parsed and listed only; **no code may branch on them** in this run.

### Helper
`.claude/hooks/lib/project_conventions.py` gains one mode, `authorized`, inside the existing
file (no new module): parser shape `mode` choices `branch|commit|authorized`, `slug` becomes
`nargs="?"`, plus `--list`; `branch` and `commit` without a slug must still exit 2 (argparse
error), which a test pins. `authorized <action> [--root DIR]` → `yes`/exit 0 when both trust
conditions hold, else `no`/exit 1 with a one-line stderr reason (`no CLAUDE.md`, `no section`,
`not granted`, `unknown action <w>`, `project not trusted: <root>`). `authorized --list` →
granted **and trusted** words, document order, duplicates collapsed, exit 0 (nothing when none;
`--list` for an untrusted project prints nothing and says `project not trusted` on stderr). The
`except Exception` fallback at the file's end prints `no` and exits 1 when `sys.argv[1] ==
"authorized"`: consent fails closed, naming keeps failing open. Stdlib only.

### Consumers — exact old text → new text
- **ROUTING.md**: replace the two-line bullet beginning `- **Never push and never open a PR as
  part of a run.**` (through `only runs when the user types it.`) with:
  `- **Never push and never open a PR as part of a run unless the project grants it and the
  machine trusts the project.** A project grants it in its root `CLAUDE.md` under
  `## gentic authorizations` (`push`, `open-pr`; `merge-on-green`, `deploy-preview`,
  `use-workflow-tool`, `spawn-teams` are reserved), and the user trusts the project by adding
  its git-root path to `~/.claude/gentic/trusted-projects`. Ask the script, never memory:
  `python3 "$HOME/.claude/hooks/lib/project_conventions.py" authorized push` prints `yes` or
  `no`. Without `yes` for both `push` and `open-pr`, `/ship`, typed by the user, remains the
  only path.`
- **gentic-iterate**, `## Final report (all DoD green)`: replace the sentence `If
  superpowers:finishing-a-development-branch is available, invoke it to close out the branch.`
  with `Then commit the final-report edit to `progress.md` as the last checkpoint commit. Ask
  the project: if `python3 "$HOME/.claude/hooks/lib/project_conventions.py" authorized push`
  and `… authorized open-pr` both print `yes`, follow `$HOME/.claude/commands/ship.md` steps 1–4
  and 6 (preconditions, branch guard, verify, review, push, PR); skip its commit step, skip
  `dod-auditor` in its review because it just ran, record any review finding in the PR body
  rather than as a rung, and put the PR URL in the report. If either prints `no`, the report
  says what `/ship` would do and stops there; then, if
  superpowers:finishing-a-development-branch is available, invoke it to close out the branch.`
- **gentic-iterate**, `## On failure: diagnose, then pick a rung`: insert as a new first
  paragraph, before `Direct rung-5 entry:`: `Before any rung, if `docs/gentic/<run>/STOP`
  exists, write the handoff into `progress.md` and stop — the file was put there from outside
  the run.`
- **ship.md**: replace the sentence `Nothing here fires on its own; the user typing `/ship` is
  the authorisation.` with `Nothing here fires on its own; the user typing `/ship` is the
  authorisation — or a gentic run in a project that grants `push` and `open-pr` under
  `## gentic authorizations` *and* is listed in `~/.claude/gentic/trusted-projects`, which the
  run checks with `project_conventions.py authorized` before following these steps at the end
  of Iterate.` `Never merge the PR` and every precondition stay.
- **gentic/SKILL.md**: after `## Status request`'s paragraph, a section `## Stop request`:
  `\`/gentic stop <slug> [reason]\` — handled by this skill like a status request, no command
  file — writes `docs/gentic/<run>/STOP` containing the reason (default `stopped by user`).
  `gentic-execute` checks for it before every task and `gentic-iterate` before every rung; a
  stopped run writes its handoff and ends the turn. Status lists such a run as `stopped`. The
  file is untracked and never committed; nothing deletes it but the user. Delete it to resume.`
- **gentic-execute**, `## Per-task loop`: new step `0. **Check for `STOP`.** If
  `docs/gentic/<run>/STOP` exists, write the handoff into `progress.md` and end the turn; do
  not start the task.` (renumber nothing; a `0.` before `1.`).
- **root `CLAUDE.md`**, after the `## Conventions` bullets: a section `## gentic authorizations`
  with the prose: `Standing permissions a run may use without asking again, honoured only when
  this repository's path is also in the machine's `~/.claude/gentic/trusted-projects`. Words:
  `push`, `open-pr`, `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`.
  This repository grants none; `/ship` is typed by hand here.` No bullets.
- **README.md**: a section `## Standing authorizations` before `## Install`: the section
  format, the trust file and why (a clone must not grant itself), the helper call, fail-closed,
  only `push`/`open-pr` consumed today, the STOP file.
- **hooks README**: the Components table row for `PreToolUse` gains `subagent spawns`, and a
  paragraph names the concurrency valve: five concurrent foreground subagents, deny with a
  reason, background spawns (`run_in_background: true`) not counted, counter reset at each
  user prompt, serialised with a lock.
- **install.sh**: the printed settings block's `PreToolUse` matcher gains `|Task|Agent`. The
  user's live `~/.claude/settings.json` gets the same edit (a config change, backed up first:
  `settings.json.bak-<timestamp>`), and `run.sh`'s matcher assertion gains `Task`.

### Concurrency valve
`pre_tool_use.py`: for `tool_name` in `{"Task", "Agent"}` — skipped when
`tool_input.get("run_in_background")` is true — take a lock (`fcntl.flock` on
`<state file>.lock`, via a new `common.session_lock(session_id)` context manager), load state,
and if `session["agents_in_flight"]` (default 0) ≥ 5, save nothing and `deny(...)` with:
`Five subagents are already in flight. Wait for one to return before spawning another —
runaway fan-out is how a run burns its budget without converging.` Otherwise increment, save,
release. `post_tool_use.py`: same tools, same lock, decrement with floor 0 (background spawns
were never counted, but a decrement on their return is harmless at the floor). `common.begin_turn`
resets `agents_in_flight` to 0 (a new prompt has no foreground subagents in flight; leaked
counts clear). The `subagent_type` review signal is unchanged. Hooks remain stdlib (`fcntl` is).

### Tests
- `tests/test_project_conventions.py`: `test_authorized_reads_the_section` — a repo whose
  `CLAUDE.md` grants `push` and `open-pr — comment` and whose root is in a temp trust file
  (`GENTIC_TRUST`): `authorized push` → `yes`, 0; `authorized open-pr` → `yes`, 0;
  `authorized merge-on-green` → `no`, 1; `authorized --list` → `push\nopen-pr\n`, 0; `- Push`
  capitalised counts. `test_authorized_fails_closed` — same grants but root absent from the
  trust file → `no`, 1, stderr contains `not trusted`; trusted but no section → `no`, 1;
  no `CLAUDE.md` → `no`, 1; unknown word `deploy` → `no`, 1, stderr `unknown action`; the word
  in prose but not a bullet → `no`, 1. `test_branch_and_commit_still_need_a_slug` — `branch`
  alone exits 2.
- `tests/test_guard_and_session.py`: `test_concurrency_valve_denies_a_sixth_agent` — five
  PreToolUse `Task` payloads (sequential) allowed, the sixth's stdout JSON has
  `permissionDecision: "deny"` with `in flight` in the reason; one PostToolUse `Task` then a
  spawn passes; a `run_in_background: true` spawn passes even at five.
  `test_valve_counts_parallel_spawns` — five PreToolUse processes started concurrently with
  `subprocess.Popen`, all waited; the state file then shows `agents_in_flight == 5`.
  `test_valve_resets_on_a_new_prompt` — after a `UserPromptSubmit` payload the count is 0.
- `tests/test_structure.py`, class `StandingAuthorizations`, **eight** tests over lowered
  text: ROUTING.md contains `'## gentic authorizations'` and `'authorized push'`;
  gentic-iterate contains `'authorized open-pr'`, `'ship.md'` and `'docs/gentic/<run>/stop'`;
  ship.md contains `'trusted-projects'`; gentic-execute contains `'check for `stop`'`;
  gentic/SKILL.md contains `'## stop request'`; root `CLAUDE.md` contains
  `'## gentic authorizations'`; README contains `'## standing authorizations'` and
  `'trusted-projects'`; hooks README contains `'in flight'` and `'run_in_background'`.
- `tests/test_install.py`: `test_settings_block_matcher_covers_subagents` — the printed
  settings block (run the installer against an empty temp `CLAUDE_HOME` and read its output)
  contains `Task|Agent` in the `PreToolUse` matcher.
- Environment for H6: network, a logged-in `claude`, ≈ 2.5 USD; `./install.sh` mutates
  `~/.claude` (`settings.json` is backed up first).
- Lessons carried: `-k` patterns are substrings of contract test names; no double-quoted
  `.claude` literal in a hook without `Path.home()` on the same line; commit from the repo root
  with absolute paths.

## Decisions (inlined; all `user — delegated`)
Grants in the project's `CLAUDE.md` **and** a machine-side trust file; fixed vocabulary, four
words reserved and inert; fail closed; the Iterate final report follows `ship.md` steps 1–4
and 6 when both `push` and `open-pr` say `yes`, review findings go to the PR body; `/ship`
wording admits the second caller; valve at 5 as a cap, foreground only, locked, reset per
prompt; PreToolUse matcher gains `Task|Agent` in the installer and the live settings; `STOP`
file via `/gentic stop`, untracked; this repo grants nothing and is not trusted; one live
regression run of the workflow case; budget currency deferred.

## Constraints
- Stdlib only; hooks under 150 ms (the existing PreToolUse median stands in for the valve path);
  no new brain tables.
- The wording sites are exactly those in Context. `/ship`'s "Never merge", "Never force-push"
  and all preconditions are unchanged.
- Every task test-first; observed RED in `progress.md`.

## Non-goals
- No consumer for the four reserved words; no code may branch on them.
- No `/gentic` command file; `/gentic stop` is handled by the gentic skill like `/gentic status`.
- No budget currency (`gentic-epic`); no hook for STOP; no commit of the STOP file.
- **The push path ships unexercised end to end in this run**: no agent session pushes to a
  bare remote here. The deterministic half (grant + trust → `yes`) is tested; the prose half
  is the wording tests; the first real exercise is the release-lane run (R6), which owns CI.
- No eval case for authorizations; no full suite run (workflow case only); no CI.

## Definition of Done
- [ ] H1 Helper reads grants (trusted project). `authorized push` and `authorized open-pr` print
      `yes`/exit 0; `authorized merge-on-green` prints `no`/exit 1; `--list` prints `push` then
      `open-pr`; a capitalised bullet counts.
      verify: `python3 .claude/hooks/tests/test_project_conventions.py -k authorized_reads`
      contract: tests/test_project_conventions.py · test_authorized_reads_the_section ·
      expected RED: `AssertionError: 2 != 0 : authorized push` (argparse rejects the mode)
- [ ] H2 Helper fails closed. Untrusted root → `no`/1 with `not trusted` on stderr; no section,
      no file, unknown word, word in prose → `no`/1; `branch` without a slug still exits 2.
      verify: `python3 .claude/hooks/tests/test_project_conventions.py -k fails_closed -k need_a_slug`
      contract: tests/test_project_conventions.py · test_authorized_fails_closed,
      test_branch_and_commit_still_need_a_slug · expected RED: `AssertionError: 2 != 1 : untrusted must be a no`
- [ ] H3 Valve. Sixth sequential spawn denied (`permissionDecision` `deny`, reason contains
      `in flight`); a return frees a slot; background spawns are never counted; five parallel
      spawns count to 5; a new prompt resets the count.
      verify: `python3 .claude/hooks/tests/test_guard_and_session.py -k valve`
      contract: tests/test_guard_and_session.py · test_concurrency_valve_denies_a_sixth_agent,
      test_valve_counts_parallel_spawns, test_valve_resets_on_a_new_prompt · expected RED:
      `AssertionError: None != 'deny' : sixth spawn was not denied`
- [ ] H4 Wording in place: the eight `StandingAuthorizations` tests.
      verify: `python3 .claude/hooks/tests/test_structure.py -k StandingAuthorizations`
      contract: tests/test_structure.py · StandingAuthorizations (eight tests) · expected RED:
      `AssertionError: 'authorized push' not found in …`
- [ ] H5 Matcher covers subagents. The installer's printed settings block and the live
      `~/.claude/settings.json` `PreToolUse` matcher contain `Task|Agent`; `run.sh`'s matcher
      assertion includes `Task`.
      verify: `python3 .claude/hooks/tests/test_install.py -k matcher_covers_subagents` and
      `jq -r '.hooks.PreToolUse[0].matcher' ~/.claude/settings.json`
      contract: tests/test_install.py · test_settings_block_matcher_covers_subagents · expected
      RED: `AssertionError: 'Task|Agent' not found in …`
- [ ] H6 Harness green. `bash .claude/hooks/tests/run.sh` exits 0, prints the substrings
      `ok    test_project_conventions`, `ok    test_guard_and_session`, `ok    test_structure`,
      `ok    test_install`, and its Configuration section is not skipped.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of H1–H5's tests.
- [ ] H7 Regression gate and this repo's state. After `./install.sh` (mutates `~/.claude`) and
      `./install.sh --check` exit 0: `python3 evals/run.py --case csv-export-probe --arm with`
      prints a with-arm line containing `4/4 (1.00)` (format `csv-export-probe  … with 4/4 (1.00)  $…`);
      a lower score is a rung-1 entry, not a re-run. And from the repo root
      `python3 .claude/hooks/lib/project_conventions.py authorized --list` prints nothing with
      `project not trusted` on stderr, `authorized push` prints `no`, exit 1.
      verify: run them; paste suite id, cost, turns, and the two helper outputs
      contract: no test contract — live observations; n=1 for the probe.

## Risks & early signals
- Five parallel PreToolUse processes contend on the lock; `flock` serialises them. If the
  parallel test is flaky on this machine, that is a rung-1 finding about the lock, not the test.
- The Iterate wording adds a path that pushes; the trust file and fail-closed helper are the
  guards, and the eval workspace's `CLAUDE.md` is this repo's (grants nothing).
- Editing the live `settings.json` is reversible from its backup.

## Task order (for Execute)
1. Helper `authorized` mode + trust file + tests — H1, H2.
2. Lock, valve in both hooks, reset in `begin_turn` + tests — H3.
3. Installer block, live settings, `run.sh` assertion + test — H5.
4. Wording in the eight sites + structure tests — H4.
5. Harness — H6; install; regression run; repo state — H7.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read): 4 blocking, 14 serious, 8 minor. All fixed inline: a
machine-side trust file so a clone cannot grant itself; `Task|Agent` added to the PreToolUse
matcher (installer, live settings, harness assertion, H5); a lock and a per-prompt reset for
the counter with parallel and reset tests; background spawns keyed off `run_in_background`;
exact old→new text per site; the STOP paragraph placed before `Direct rung-5 entry`; the
final-report sequence (commit first, ship steps 1–4 and 6, findings to the PR body,
`finishing-a-development-branch` gated); `--list` order and case rules; parser shape and the
slug test; eight structure tests; H3's RED as a decision string; H6's substrings and
Configuration clause; H7's real format and rung rule; H1/H2 inlined; non-goals for the command
file, reserved words, STOP lifecycle, one mode; the unexercised push path stated as such.
