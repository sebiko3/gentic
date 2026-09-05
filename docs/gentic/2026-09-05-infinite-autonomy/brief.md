# Brief: infinite-autonomy

## Mission (as understood)

Strip the machinery that makes a session or a run stop on its own: the `Stop` hook (its
verification gate, TDD nudge, review nudge and spend report), the token-efficiency guards and
ledger (duplicate-read deny, bare-`cat` deny, spend estimate), and the workflow rules that halt
a run from inside (rung 5 / rung 8 "user check-ins", budget exhaustion → hand off). What is
left runs every phase and every rung without pausing, and the only way a run ends early is the
user's own `STOP` file. At the same time make the SQLite brain the one store gentic relies on
and make that reliance sensible: no parallel JSON state directory, no unbounded tables, no
"delete the file on schema change", and hook events tied to the run they happened in.

## Facts

- The Stop hook is `.claude/hooks/stop.py`; it is the only routine hard block in the setup
  (`stop.py:1-30`). It does four things: verification gate (block), TDD nudge, review nudge and
  spend report (all advisory), and writes `gate_block`/`nudge_*` events to the brain.
- The token-efficiency layer is `.claude/hooks/lib/token_efficiency.py` plus two call sites in
  `pre_tool_use.py` (`duplicate_read_guard`, `bare_cat_guard`, `pre_tool_use.py:169-201`) and
  two in `post_tool_use.py` (`record_bash`, `note_edit`, `post_tool_use.py:109-140`). It was
  built by run `2026-08-21-token-efficiency-hooks` (DoD D1–D10).
- The per-turn ledger in `common.py` (`_fresh_turn`: `evidence`, `red`, `touched`,
  `code_changed`, `test_touched`; `begin_turn`, `load_turn_state`) exists to feed `stop.py`.
  Its only other consumer is the concurrency valve's `agents_in_flight` counter and the
  `reviewed` flag (`post_tool_use.py:90-105`), the latter read only by the review nudge.
- Session state lives as JSON files in `~/.claude/state/<session>.json` with `fcntl` lock files
  next to them (`common.py:33-56`). Live machine: 81 `.json` + 11 `.lock` files, 780 KB; lock
  files are never pruned (brain note #16) and `post_tool_use`'s final save races the valve's
  locked increment (brain note #17).
- Brain: `.claude/hooks/lib/brain.py`, one SQLite file, WAL, 34 ms hot-path busy timeout, 9
  tables, FTS5 on notes, no indexes, no migrations ("delete the file", `README.md:141-143`,
  `gentic-brain/SKILL.md` Rules). Live brain: 14 lessons, 20 notes, 30 decisions, 321 events
  (308 `verification`, 5 `nudge_spend`, 3 `nudge_tdd`, 3 `nudge_review`, 2 `gate_block`), 91
  eval runs, 332 grader rows, 191 stamps, 20 runs. `events` grows unbounded — an accepted
  non-goal of run `2026-09-02-sqlite-brain`. Events carry `session` but no run slug.
- Only `post_tool_use.py`, `stop.py` and `session_start.py` touch the brain today
  (sqlite-brain masterprompt, Decisions). `evals/run.py` imports the module directly and points
  hooks at a throwaway brain via `GENTIC_BRAIN` (`evals/run.py:325,509`).
- Hooks are registered in the machine's `~/.claude/settings.json` (a `Stop` entry with
  `stop.py`, timeout 5); `install.sh` never writes settings but prints a block that includes the
  `Stop` entry (`install.sh:92-107`). `~/.claude/hooks` is a copy of `.claude/hooks`, identical
  today (`diff -rq` clean); `./install.sh` syncs.
- Workflow stop conditions in prose: `gentic/SKILL.md:85-89` (autonomous runs: "the only
  legitimate stops are rung 5, rung 8, budget exhaustion, or a blocker no default can
  resolve"); `gentic-iterate/SKILL.md:44,48-49` ("mandated rung costing more than the remaining
  budget = budget exhausted: stop and hand off"; "Rungs 5 and 8 are user check-ins … stop and
  hand off"); `gentic-execute/SKILL.md:23-24` and `gentic-iterate/SKILL.md:23-24` (the `STOP`
  file — user-initiated); `gentic/SKILL.md:50-56` (`/gentic stop`).
- Contract tests that pin the pieces being removed: `tests/test_gate.py` (19), 
  `tests/test_token_efficiency.py` (15), `tests/test_review_nudge.py` (14), the `TddNudge` class
  in `tests/test_tdd.py` (4 of 13), `test_brain.py::HooksWriteEvents` (asserts `gate_block` and
  `nudge_tdd` events), `test_install.py` (installs `hooks/stop.py`; printed matcher check),
  `test_structure.py::StandingAuthorizations` (`check for stop`, `## stop request`,
  `docs/gentic/<run>/stop`, hooks README "in flight"), `run.sh` (suite list, "5 hooks x 5
  hostile payloads", `for script in … stop …`). Harness baseline: all green, 15 suites, medians
  38 / 40 / 47 ms.
- Prose that describes the removed pieces: `CLAUDE.md:41` ("The hooks notice, they do not
  police … flags a turn …"), `CLAUDE.md:49` and `ROUTING.md:84` (budget 13), `README.md:70-72,
  78-80, 94, 104-105` (Stop-hook nudge, budget stops the run), `.claude/hooks/README.md`
  (Components table `Stop` row, "Token-efficiency guards", "The Stop gate cannot trap you",
  brain kinds table), `gentic-brain/SKILL.md:58-61`, `install.sh:87`.
- The evals do not reference the Stop hook, the spend ledger or the budget wording
  (`grep` over `evals/` excluding results: no hits); `csv-export-probe`'s graders check
  artifacts and continuation, so removing stops can only help the with-arm.
- The concurrency valve (`pre_tool_use.py:MAX_IN_FLIGHT = 5`) is a cap with a reason, not a
  once-only valve and not a stop; it is pinned by `test_guard_and_session.py::ConcurrencyValve`
  and the standing-authorizations run (H3, H5).
- brain lesson #14: the duplicate-read guard denied the main thread's first Read of a file a
  subagent had read (shared session ledger) — a live false positive of exactly the guard being
  removed.
- brain note #13 / #10: headless runs are bounded by the eval harness's own `--max-turns` and
  wall-clock, not by anything in the hooks; removing the Stop hook does not change that ceiling.
- `~/.claude/CLAUDE.md` (the user's global contract) still forbids unrequested commits/pushes;
  `ROUTING.md` says Execute authorises checkpoint commits on the work branch only. Nothing in
  this run touches that boundary.

## Patterns to follow

- Hooks: stdlib only, no subprocess, exit 0 on every error via `common.safe_main`, silence as
  the default branch (`common.py:1-12`, hooks README design rules).
- Brain hot path: `record_event` — best-effort, 34 ms busy timeout, never raises
  (`brain.py:157-182`). Any new hot-path brain write must copy this shape.
- Additive, idempotent migration already exists once: `ensure_schema` adds
  `eval_runs.exhausted` when missing (`brain.py:117-121`) — the pattern to generalise with
  `PRAGMA user_version`.
- Contract tests for prose live in `tests/test_structure.py` classes named after the run
  (`AutonomousRuns`, `StandingAuthorizations`, `ReleaseLane`); docs count as behaviour.
- Harness registration: `run.sh` suite list plus a `Documentation`/`harness` test in the
  suite that owns the feature (`test_brain.py::test_harness_registers_and_isolates_the_brain_suite`).
- Fibonacci constants with a one-line justification (`brain.py:26-30`, `token_efficiency.py:19-23`).
- Installer proves shipping by `git ls-files`; a removed file simply leaves the list, but the
  installer never deletes from `~/.claude` — a stale `stop.py` there is inert once unregistered.

## Constraints discovered

- `~/.claude/settings.json` is machine state; the installer must not write it. Removing the
  `Stop` entry there is a manual, backed-up edit (`README.md` Rollback section names the
  backup convention `settings.json.bak-<date>`).
- Latency budget: every hook median < 150 ms (`run.sh`), measured for UserPromptSubmit,
  PreToolUse and PostToolUse. Moving session state into SQLite must stay under it.
- `run.sh` isolation: no double-quoted `.claude` path literal in a hook line without
  `Path.home()` (brain lesson #1).
- `test_structure.py::NoOrphanedSkillFiles` and `ResolvableReferences` — every `hooks/<x>.py`
  named in a markdown file must exist; deleting `stop.py` means every prose mention goes too.
- `run.sh` expects exactly 8 gentic skills; `test_install.py` expects the printed PreToolUse
  matcher to contain `Task|Agent`.
- One task, one checkpoint commit on `gentic/infinite-autonomy` (created from
  `gentic/self-improving-gentic`, 66 commits ahead of `main`, PR #2 open). No push, no PR: this
  repo grants none of the authorizations.
- The user delegates decisions (memory: blanket trust granted 2026-08-11) — defaults are
  adopted and flagged, never blocked on.

## Open decisions (ranked by leverage)

1. **What replaces the iteration budget as the anti-thrash mechanism** — options: (A) keep the
   13-point ledger but make exhaustion an *escalation*, not a halt: the next failure goes
   straight to rung 5, a second exhaustion to rung 8, and rung 8 resets the ledger for the
   re-framed cycle; (B) delete the budget and points entirely; (C) keep the budget as a stop
   (unchanged). Recommended default: **A**, because it removes every self-imposed stop while
   keeping "same item, same rung, twice → climb" — the property that makes the loop converge
   rather than fiddle — and because lessons still record points, which the evals and the
   gardener read.
2. **Rungs 5 and 8 in an autonomous run** — options: (A) taken autonomously: amend the spec /
   re-interview with brain preferences and scouted defaults, every change flagged
   `default — unconfirmed`, and continue; (B) hand off (today). Recommended default: **A** —
   it is the literal request, and `gentic-interview` already knows how to run without
   `AskUserQuestion`.
3. **The `STOP` file and `/gentic stop`** — options: (A) keep as the user's external kill
   switch, the one legitimate early end; (B) remove with the rest. Recommended default: **A**,
   because it is user-initiated, costs nothing, and "infinitely autonomous" needs an off
   switch that is not Ctrl-C.
4. **Where session state lives once the Stop ledger is gone** — options: (A) a `sessions`
   table in the brain (atomic `UPDATE … SET agents_in_flight = agents_in_flight + 1` under
   SQLite's own locking; `~/.claude/state`, the lock files and `prune_state` disappear; a
   missing brain fails open); (B) keep the JSON files for the valve only. Recommended default:
   **A** — that is the concrete meaning of "sqlite used smartly": one store, no race (note
   #17), no orphaned lock files (note #16), and `begin_turn` becomes one `UPDATE`.
5. **What "smart" adds to the brain beyond the state move** — options: (A) three additions:
   `PRAGMA user_version` migrations with indexes on `(project, ts)` for events/notes/lessons
   (retire "delete the file"), a `prune` command with a 89-day event retention run best-effort
   at session start, and events tagged with the project's open run slug so a run's RED/GREEN
   history is one query; (B) only the state move. Recommended default: **A**, all three are
   small, test-first, and each fixes a documented weakness (unbounded events, no migrations,
   events unattributable to runs).
6. **What `post_tool_use.py` still records** — options: (A) only what has a reader left:
   `red`/`verification` events (brain), the valve's decrement; drop `touched`,
   `code_changed`, `test_touched`, `evidence`, `reviewed`; (B) keep the ledger unused.
   Recommended default: **A** — dead state is the "hooks notice" claim with nobody listening.
7. **The live `~/.claude/settings.json`** — options: (A) this run removes the `Stop` entry
   after backing the file up as `settings.json.bak-2026-09-05`, and syncs `~/.claude/hooks`
   with `./install.sh`; (B) leave machine state to the user. Recommended default: **A** —
   the request is about this machine's behaviour, the edit is reversible and documented.
8. **Concurrency valve** — options: (A) keep, storage moved per decision 4; (B) remove as
   another "condition". Recommended default: **A** — it caps fan-out, it never ends a run, and
   the standing-authorizations run proved it.
