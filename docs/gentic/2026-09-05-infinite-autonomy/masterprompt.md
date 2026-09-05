# Masterprompt: infinite-autonomy

## Mission

After this run, no hook ends a turn and no rule ends a run on its own. (PreToolUse denials of
individual tool calls — the concurrency valve, the destructive-command rules, `.agentignore` —
are unaffected.) The `Stop` hook and its four behaviours (verification gate, TDD nudge, review
nudge, spend report) are gone; the token-efficiency guards and estimated-spend ledger are gone;
the per-turn evidence ledger that fed them is gone; and the workflow prose no longer tells a run
to "stop and hand off" at rung 5, rung 8 or budget exhaustion — those escalate instead. The only
early end is the user's own `docs/gentic/<run>/STOP` file. In the same run the SQLite brain
becomes the one store the hooks use: session state (the concurrency valve's counter) lives in a
`sessions` table instead of JSON files under `~/.claude/state`; the schema is versioned with
additive, idempotent migrations instead of "delete the file"; the `events` table is bounded by a
`prune` command with 89-day retention; and every hook event carries the slug of the project's
open run so a run's RED/GREEN history is one query. The harness stays green at every checkpoint,
the three measured hook medians (UserPromptSubmit, PreToolUse, PostToolUse) stay under 150 ms,
and this machine's `settings.json` no longer registers a `Stop` hook.

The critic recommended splitting this into two runs (autonomy; brain-as-store). They stay
together because the valve's counter must leave `~/.claude/state` before that directory can go,
and because the user asked for both in one request; the task order below puts the brain work
and every irreversible machine step first. Flagged `default — unconfirmed` in `decisions.md`.

## Context

Repository: `~/code/gentic`, branch `gentic/infinite-autonomy` (created from
`gentic/self-improving-gentic`; this repo grants no `push`/`open-pr`, so nothing is pushed).
Everything under `.claude/` is installed into `~/.claude/` by `./install.sh` (copies tracked
files, never deletes, never writes `settings.json`). CI (`.github/workflows/gentic.yml`) runs
`run.sh` on ubuntu with no `~/.claude/settings.json`; its Configuration section must keep
skipping there.

Hooks (`.claude/hooks/`), all stdlib, all exit 0 via `common.safe_main`:

- `stop.py` — the whole file is removed. Today it: blocks a done-claim with no verification
  evidence (`verification_gate`), prints the TDD / review / spend nudges (`advisory_nudges`),
  and writes `gate_block` / `nudge_tdd` / `nudge_review` / `nudge_spend` brain events.
- `lib/token_efficiency.py` — the whole file is removed. Its call sites:
  `pre_tool_use.py` `duplicate_read_guard` and `bare_cat_guard` (lines 143-170, plus the
  `if tool == "Read": return duplicate_read_guard(...)` at 270 and `bare_cat_guard(...)` at
  305); `post_tool_use.py` `token_efficiency.record_bash` (110) and `note_edit` (138).
- `post_tool_use.py` — keeps: the `VERIFICATION` regex (`post_tool_use.py:27-40`), `exit_code_of`,
  the `red`/`verification` brain event write (`brain.record_event`, line 121), and the valve
  decrement on a foreground subagent's return (`post_tool_use.py:90-104`). Loses: the
  `touched` / `code_changed` / `test_touched` / `evidence` / `red` state lists, `PROSE_SUFFIXES`,
  `TEST_PATH`, `REVIEW_AGENTS` and the `reviewed` flag (only the review nudge read them). The
  file is trimmed, not restructured: the surviving functions keep their names and shape.
- `pre_tool_use.py` — keeps the destructive-command rules, `.agentignore`, and the
  concurrency valve (`concurrency_valve`, `MAX_IN_FLIGHT = 5`, `pre_tool_use.py:173-201`);
  the valve's counter moves from `common.load_state/save_state` under `common.session_lock`
  to the brain (below). `common.block` has no caller left once the two guards go.
- `user_prompt_submit.py` — keeps intent routing; `common.begin_turn(payload)` (line 120)
  becomes `brain.session_reset(session_id)`.
- `session_start.py` — `common.prune_state(days=7)` (line 46) becomes `brain.prune_quietly()`
  (below); the unfinished-run notice and the existing `brain: N lesson(s) …` summary line stay.
- `lib/common.py` — keeps `read_payload`, `emit`, `emit_context`, `emit_message`, `safe_main`,
  `git_root`. Loses `STATE_DIR`, `_state_file`, `load_state`, `save_state`, `prune_state`,
  `session_lock`, `_fresh_turn`, `begin_turn`, `load_turn_state`, `block`, and the imports
  only they used (`os`, `re`, `time`, `contextlib`, `fcntl`). `safe_main` keeps its
  `SystemExit` re-raise (harmless).
- `lib/project_conventions.py:43` derives `TRUST_FILE = common.STATE_DIR.parent / "gentic" /
  "trusted-projects"`; it must derive from `brain.DEFAULT_PATH.parent / "trusted-projects"`
  instead (same path; `GENTIC_TRUST` still overrides, `project_conventions.py:139`). No line
  may carry a double-quoted `.claude` literal without `Path.home()` on it (`run.sh` isolation).
- `lib/brain.py` — schema in `SCHEMA` (9 tables; A4's fixture inlines the pre-run DDL it
  needs for events/notes/lessons/eval_runs rather than importing `brain.SCHEMA`) + `FTS_SCHEMA`; `ensure_schema` already holds
  one ad-hoc additive migration (`eval_runs.exhausted`, guarded by `PRAGMA table_info`, lines
  117-121); `record_event` is the best-effort hot-path shape (`timeout=0.034` seconds, never
  raises, returns False without a git root); `connect(timeout)` creates the directory and the
  file; `sqlite3.connect(timeout=…)` is in **seconds**; CLI via `argparse` subparsers with a
  `scoped` parent parser (adds `--project`). `EVENT_KINDS` lists six kinds; after this run only
  `red` and `verification` are written. `cmd_sql` shows the backup-API pattern
  (`conn.backup(other)`, lines 351-353).
- Tests: every suite is a `unittest` module run as a script (`-k` works); `run.sh` runs 15
  suites by name (line 19) with `cd "$HOOKS"`, so **new tests anchor every path on
  `Path(__file__)`** and must pass from the repo root and from `$HOOKS`. Then a hostile-input
  sweep over `user_prompt_submit post_tool_use stop session_start pre_tool_use` ("5 hooks x 5
  hostile payloads"), three latency medians, an isolation grep, and a Configuration section
  inside `if [ -f "$SETTINGS" ] …` that reads `~/.claude/settings.json` with `jq` (skips when
  absent). Suites to delete outright: `test_gate.py`, `test_token_efficiency.py`,
  `test_review_nudge.py`. Suites to rework: `test_tdd.py` (keep `UiTestRunners`; `RedLedger`
  re-asserts through brain events; `TestFileClassification` and `TddNudge` go),
  `test_brain.py` (`HooksWriteEvents` lines 145-150 drop the `stop` half; line 164 inside
  `test_brain_failure_is_invisible_to_hooks` calls `self.stop(...)` and goes too; the
  `BrainCase.stop` helper and the now-unused `edit_post` helper go; `CLAUDE_HOOK_STATE_DIR`
  leaves `BrainCase.env`), `test_guard_and_session.py::ConcurrencyValve` (`count()` reads the
  brain, not a JSON file; `test_valve_counts_parallel_spawns` sets `GENTIC_BRAIN`; the
  module's `run()` helper sets `GENTIC_BRAIN` instead of `CLAUDE_HOOK_STATE_DIR`),
  `test_lib.py::State` (gone), `test_lib.py::SafeMain::test_lets_deliberate_block_through`
  (gone with `block`), `test_install.py` (`hooks/stop.py` in the installed list at line 44 →
  `hooks/post_tool_use.py`; new assertion over the heredoc text **read from `install.sh`
  itself**, since the block is only printed when `$DEST/settings.json` lacks a `hooks` key),
  `test_evals.py:119` (`CLAUDE_HOOK_STATE_DIR` env entry and its docstring mention, line 7,
  removed). `test_structure.py` gains an `InfiniteAutonomy` class (contracts below); its
  `StandingAuthorizations` class stays as is (the `STOP` file and the valve survive).
- Docs that describe the removed pieces and must change: `CLAUDE.md:41` (the whole "The hooks
  notice, they do not police …" bullet), `CLAUDE.md:49` and `.claude/skills/gentic/ROUTING.md:84`
  (budget wording), `README.md` lines 70-72, 78-80, 94, 104-105, 141-143 ("no schema
  migrations"), 266-268; `.claude/hooks/README.md` (Components table `Stop` row,
  "Token-efficiency guards", "The Stop gate cannot trap you", session-state sentence, "The
  brain" kinds table, rollback section); `.claude/skills/gentic-brain/SKILL.md` (hook kinds,
  "No schema migrations exist" rule, command table); `install.sh:85-107` (comment and printed
  block).
- Workflow prose to change: `.claude/skills/gentic/SKILL.md` "Autonomous runs" (lines 83-89;
  "Stop request" stays); `.claude/skills/gentic-iterate/SKILL.md` ladder paragraph (38), hard
  rules (44, 48-49), final report; `.claude/skills/gentic-execute/SKILL.md` unchanged.
- Live machine: `~/.claude/settings.json` has a `Stop` entry (`python3 "$HOME/.claude/hooks/stop.py"`);
  `~/.claude/hooks` is a byte-identical copy of the repo's; `~/.claude/state` holds 81 `.json`
  and 11 `.lock` files (780 KB) — per-turn ledgers and valve counters only. Rollback
  convention: `~/.claude/settings.json.bak-<date>`. `jq` is installed (the harness already
  uses it).
- Live brain (`~/.claude/gentic/brain.sqlite`, 291 KB, WAL): `PRAGMA user_version` is 0;
  tables are the nine in `SCHEMA` plus `notes_fts`; `eval_runs` already has `exhausted`;
  `events` has 321 rows and no `run` column; `runs` has an open row `infinite-autonomy` for
  project `gentic`. **Any `brain.py` invocation without `GENTIC_BRAIN` — including this run's
  own `note`/`decide`/`lesson` calls — opens and migrates the live file once the migration code
  exists; that is the intended upgrade, and task 1's backup is its undo.** A plain `cp` of a
  WAL database can miss `-wal` contents; back up with the sqlite backup API.
- brain facts worth honouring: note #16 (lock files never pruned), note #17 (`post_tool_use`'s
  unlocked save races the valve), lesson #14 (duplicate-read guard false positive across
  subagents), lesson #1 (harness isolation grep rejects `"…\.claude…"` literals).

## Decisions

All `default — unconfirmed` (the user delegated every decision). The substance is inlined here;
`decisions.md` only repeats it.

- **Budget → escalation.** The 13-point ledger stays in `progress.md` and rungs still cost
  1/2/3/5/8. When a mandated rung costs more than the remaining balance, the run does not stop:
  it takes rung 5 (re-open the masterprompt) at once and records the overspend as a negative
  balance; if a mandated rung again exceeds the balance after a rung 5, it takes rung 8
  (re-open the Interview); a taken rung 8 resets the balance to 13 for the re-framed cycle and
  the iteration log records the reset. Worked example the prose must carry: balance 2, item
  fails twice at rung 3 → rung 5 mandated (cost 5) → taken, balance −3 → item fails twice at
  rung 5 → rung 8 mandated → taken, balance resets to 13. "Same item fails twice at a rung →
  next rung" is unchanged.
- **Rungs 5 and 8 are taken autonomously.** No "user check-in": `gentic-masterprompt` amends
  the spec, `gentic-interview` re-runs under its non-interactive rule, every changed decision is
  `default — unconfirmed`, and the run continues. The final report lists every rung-5/8 change.
- **`STOP` stays.** `docs/gentic/<run>/STOP` and `/gentic stop <slug>` remain the one
  legitimate early end; `gentic-execute` and `gentic-iterate` keep their checks unchanged.
- **Session state lives in the brain.** New table `sessions (id TEXT PRIMARY KEY,
  agents_in_flight INTEGER NOT NULL DEFAULT 0, updated REAL)`. Three helpers in `lib/brain.py`,
  each opening its own connection with `timeout=0.144` (seconds; contended by up to five
  parallel spawns), each setting `updated = time.time()`:
  `session_reset(session_id)` (upsert, counter 0; returns True on success; needs no git root
  and may create the brain file, exactly as the JSON state file was created before),
  `session_acquire(session_id, cap)` → True when a slot was taken (`INSERT OR IGNORE` the row,
  then one `UPDATE sessions SET agents_in_flight = agents_in_flight + 1, updated = ? WHERE id
  = ? AND agents_in_flight < ?`; `rowcount == 1` decides), `session_release(session_id)`
  (`agents_in_flight = MAX(agents_in_flight - 1, 0)`; returns True on success). Sessions need
  no project key. **Best-effort means:** returns False (or, for `session_acquire`, True),
  prints nothing, raises nothing, and never waits longer than its busy timeout. **A brain that
  cannot be opened fails open — an uncapped valve is preferred to a blocked session**; this is
  an accepted trade, not a defect. `~/.claude/state` and `CLAUDE_HOOK_STATE_DIR` cease to exist.
- **Schema versioning.** `SCHEMA_VERSION = 2`. `ensure_schema` runs the `CREATE TABLE IF NOT
  EXISTS` baseline as today, then reads `PRAGMA user_version` and applies, in order, each
  migration whose number is above it, then stamps `user_version = SCHEMA_VERSION`. **Every
  migration statement is individually guarded and idempotent**: a column is added only if
  `PRAGMA table_info` lacks it; tables and indexes use `IF NOT EXISTS`. Migration 1 is exactly
  today's guarded `eval_runs.exhausted` column (a no-op on any brain that already has it).
  Migration 2 adds `sessions`, `events.run TEXT`, and exactly these five indexes — no others:
  `idx_events_project_ts ON events(project, ts)`, `idx_events_run ON events(run)`,
  `idx_notes_project_ts ON notes(project, ts)`, `idx_lessons_project_ts ON lessons(project, ts)`,
  `idx_runs_project_finished ON runs(project, finished)`. `SCHEMA` stays at today's nine
  tables: `sessions` and `events.run` exist only through migration 2, so a brand-new file also
  passes through it. A version-0 brain with the old shape is upgraded in place on first open
  and its rows survive. The "delete the file on a shape
  change" rule is retired from the docs.
- **Events carry the open run.** `record_event` fills `events.run` with the slug of the most
  recently started, unfinished `runs` row for the same project (`WHERE project = ? AND finished
  IS NULL ORDER BY started DESC LIMIT 1`), or NULL when there is none. `EVENT_KINDS` shrinks
  to `("red", "verification")`.
- **Prune is global.** New CLI command `prune [--events-days 89] [--sessions-days 8]`,
  registered **without** the `scoped` parent (it takes no `--project` and never filters by
  project): deletes `events` older than the retention and `sessions` whose `updated` is older
  than theirs, printing `pruned N event(s), M session(s)`; no `.bak` is taken (designed
  retention, not an ad-hoc delete); no `VACUUM`. `brain.prune_quietly()` is the in-process
  form `session_start.py` calls: it returns immediately when `db_path()` does not exist (a
  session start still never creates the brain), otherwise opens `sqlite3.connect` directly
  (never `connect()`, which would create the file), prunes with the defaults, prints nothing,
  raises nothing.
- **`post_tool_use.py` records only what has a reader**: `red`/`verification` events and the
  valve release. It writes no session state of its own.
- **Live machine, in this order** (task 1 and the last task): (1) before any edit to
  `brain.py`, back up the live brain with the sqlite backup API to
  `~/.claude/gentic/brain.sqlite.bak-<YYYY-MM-DD>`; (2) copy `~/.claude/settings.json` to
  `~/.claude/settings.json.bak-<same date>`, remove the `hooks.Stop` key with `jq` (every
  other key keeps its value; jq's whitespace reformatting is accepted, the `.bak` is the undo);
  both backups use one date string, recorded verbatim in `progress.md` at task 1, and A11 reads
  that recorded string, never today's date. The running Claude Code session may hold the old
  `Stop` registration in memory: once task 9 deletes the script, that session may print a
  `hook error` line at the end of each turn until it is restarted — expected, not a regression. Last: `./install.sh`, then delete exactly `~/.claude/hooks/stop.py`,
  `~/.claude/hooks/lib/token_efficiency.py`, `~/.claude/hooks/tests/test_gate.py`,
  `~/.claude/hooks/tests/test_token_efficiency.py`, `~/.claude/hooks/tests/test_review_nudge.py`
  and the directory `~/.claude/state` (no backup: it holds only per-turn ledgers and valve
  counters; another live session on this machine loses at most one valve count — accepted).
- **Concurrency valve stays** with its 5 cap, its `in flight` reason and its reset at every
  user prompt.

## Constraints

- Hooks: stdlib only, no subprocess, no network; every hook exits 0 on every payload in the
  hostile-input sweep; medians under 150 ms for UserPromptSubmit, PreToolUse (with
  `.agentignore`) and PostToolUse (with a brain write) as `run.sh` measures them, on this
  machine and in CI alike (CI has passed at today's medians; a CI-only latency failure is
  investigated, never loosened). SessionStart is not measured.
- Hooks never print anything about a brain *failure*; the existing session-start `brain:`
  summary line is the one thing a hook says about the brain, and it stays.
- No double-quoted `.claude` literal on a hook line without `Path.home()` (`run.sh` isolation).
- `run.sh`'s Configuration checks live inside the existing settings-present branch, so CI and
  a fresh machine keep skipping them.
- Every task test-first via `gentic-tdd`; observed RED pasted into `progress.md`; one task, one
  checkpoint commit with the subject from `project_conventions.py commit infinite-autonomy …`;
  `bash .claude/hooks/tests/run.sh` exits 0 at every checkpoint on this machine.
- `run.sh` keeps expecting exactly 8 gentic skills; `test_install.py` keeps expecting
  `Task|Agent` in the printed PreToolUse matcher; `test_structure.py` reference checks keep
  passing (every `hooks/<x>.py` named in markdown must exist → no prose may still name
  `stop.py`).
- Nothing under `docs/gentic/` is edited to satisfy a check: `test_structure.py::markdown_files`
  scans only `.claude/**/*.md`, `README.md` and `CLAUDE.md`, so prior runs' artifacts that
  name `stop.py` are never scanned and are left alone.
- English identifiers and comments; no secrets; the live brain is never used as a test fixture
  (every test sets `GENTIC_BRAIN`).

## Non-goals

- No change to the destructive-command rules, `.agentignore`, the intent classifier, the
  agents, `/ship`, `/review`, `release.py`, the evals (`evals/run.py` and its cases), or
  `.github/workflows/gentic.yml`.
- No removal of the `STOP` file, `/gentic stop`, or the concurrency valve; no `MAX_IN_FLIGHT`
  override; no retry logic in the valve beyond the single fallback in Risks.
- No new brain CLI subcommands other than `prune` (no `migrate`, `schema`, `sessions`,
  `--dry-run`); no indexes beyond the five named; no `VACUUM`; no journal-mode change; no
  change to the existing commands' semantics (`note`, `recall`, `sql`, `decide`, `preference`,
  `lesson`, `lessons`, `stats`, `run`, `stamp`, `evals`); the `.bak` rule for `sql` stays; FTS
  behaviour stays.
- No retention for `notes`, `decisions`, `lessons`, `runs`, `stamps`, `eval_*` — only `events`
  and `sessions` are pruned.
- No new consumer of `events` beyond the `run` column (no dashboard, no per-run report).
  Migration 2 is additive only: existing `events` rows keep `run = NULL`; **no backfill**.
- No cap on rung-8 resets, no loop guard, no "after N cycles, stop" clause in any prose.
- `install.sh` keeps its copy-only behaviour; stale installed files are removed by hand in
  task 9. No new hook events (no `SessionEnd`), no stale-session sweeper: a leaked counter is
  cured by the next UserPromptSubmit reset and by `prune --sessions-days 8`. No import of
  `~/.claude/state` contents into `sessions`.
- No replacement for the verification gate, and no re-invented TDD/review advice in any other
  channel (not in `progress.md`, not as a `systemMessage`): after this run no hook blocks or
  nudges; the Iterate phase and `dod-auditor` are the only proof of done-ness. The README says so.
- No token or cost accounting of any kind; no spend estimate anywhere.
- No restructuring of `pre_tool_use.py` / `post_tool_use.py` beyond the named deletions and
  the valve's storage swap.
- No backup of `~/.claude/state`; no edits to `~/.claude/CLAUDE.md`, to plugins, or to any
  settings key other than `hooks.Stop`.
- No push, no PR (this repo grants neither).

## Definition of Done

- [ ] **A1 — No Stop hook, no token guards.** `.claude/hooks/stop.py` and
      `.claude/hooks/lib/token_efficiency.py` do not exist; no file under `.claude/hooks/*.py`
      or `.claude/hooks/lib/*.py` contains any of the ten names `token_efficiency`,
      `load_state`, `save_state`, `session_lock`, `begin_turn`, `load_turn_state`,
      `STATE_DIR`, `CLAUDE_HOOK_STATE_DIR`, `prune_state`, and a call `block(` (hooks import
      `from lib import common`, never `from common import`); the second of two identical
      PreToolUse `Read` payloads for the same `file_path` in one `session_id`, and a Bash
      payload `cat <path>` on a file the test writes at 100 KB (size is now irrelevant), each
      produce no `permissionDecision` and exit 0.
      verify: `python3 .claude/hooks/tests/test_structure.py -k stop_hook_and_token_guards`
      contract: tests/test_structure.py · InfiniteAutonomy.test_stop_hook_and_token_guards_are_gone
      · asserts the two files are absent, greps the hook sources for the ten names, and runs
      the three PreToolUse payloads · expected RED: `AssertionError: .claude/hooks/stop.py
      still exists`
- [ ] **A2 — Hooks record RED and GREEN to the brain and nothing else.** A `PostToolUse` Bash
      payload with a recognised verification command and exit 1 writes exactly one `red` event;
      exit 0 (or no exit code) writes exactly one `verification` event; a failing
      non-verification command writes none; an `Edit` payload writes no event and no `sessions`
      row; `brain.EVENT_KINDS == ("red", "verification")`.
      verify: `python3 .claude/hooks/tests/test_tdd.py -k RedLedger`
      contract: tests/test_tdd.py · RedLedger.test_event_kinds_are_exactly_red_and_verification
      (the RED-bearing one) with siblings test_failing_verification_is_recorded_as_red,
      test_successful_verification_is_green, test_unknown_exit_code_is_green,
      test_non_verification_and_edits_write_nothing — all read `events` and `sessions` from
      the `GENTIC_BRAIN` file, never a JSON state file · expected RED: `AssertionError: Tuples
      differ: ('red', 'verification', 'gate_block', …) != ('red', 'verification')`
- [ ] **A3 — The valve counts in the brain.** Five foreground spawns then a sixth →
      `permissionDecision: deny` with `in flight` in the reason; a foreground return frees one
      slot; a background spawn is never denied and its return frees nothing; five spawns
      launched as parallel processes leave `sessions.agents_in_flight = 5`; a
      `UserPromptSubmit` resets it to 0; with `GENTIC_BRAIN=<regular file>/deeper/brain.sqlite`
      (the parent is a file, so the directory cannot be created) six spawns are all allowed and
      stderr is empty.
      verify: `python3 .claude/hooks/tests/test_guard_and_session.py -k ConcurrencyValve`
      contract: tests/test_guard_and_session.py · ConcurrencyValve.test_valve_counts_parallel_spawns
      (reads `select agents_in_flight from sessions where id = ?` from `GENTIC_BRAIN`) and
      ConcurrencyValve.test_valve_fails_open_without_a_brain · expected RED: `AssertionError:
      0 != 5 : parallel spawns lost updates` (the counter is still in the JSON file)
- [ ] **A4 — Schema versioning upgrades an old brain in place, idempotently.** A brain file
      created with the pre-run `SCHEMA` (no `sessions`, no `events.run`, `user_version` 0,
      `eval_runs.exhausted` already present) containing one note, one lesson and one event is
      opened by `brain.connect()`: afterwards `PRAGMA user_version` is 2, `sessions` exists,
      `events` has a `run` column, the five named indexes exist in `sqlite_master`, and the
      three rows are unchanged; a second `connect()` changes nothing and raises nothing; a
      brand-new file also ends at version 2; `brain.SCHEMA_VERSION == 2`.
      verify: `python3 .claude/hooks/tests/test_brain.py -k migrat`
      contract: tests/test_brain.py · Migrations.test_old_brain_is_migrated_in_place · expected
      RED: `AttributeError: module 'brain' has no attribute 'SCHEMA_VERSION'`
- [ ] **A5 — Events name the open run.** After `run start alpha --goal x` in project P, a
      `red` event from a hook in P has `run = 'alpha'`; after `run finish alpha --outcome done`
      the next event has `run IS NULL`; a project with no runs gets NULL; the existing
      test_brain_failure_is_invisible_to_hooks keeps asserting `record_event` returns within
      89 ms when the brain directory cannot be created (single sample; one failure is a
      failure — never re-run to obtain a pass).
      verify: `python3 .claude/hooks/tests/test_brain.py -k "open_run or invisible"`
      contract: tests/test_brain.py · HooksWriteEvents.test_events_carry_the_open_run ·
      expected RED: `KeyError: 'run'` (the row has no such column)
- [ ] **A6 — Prune bounds events and sessions, globally.** On a fixture with three events at
      ages 1, 60 and 120 days across two projects and two sessions updated 1 and 30 days ago,
      `brain.py prune` prints `pruned 1 event(s), 1 session(s)` and leaves the young rows,
      regardless of the cwd's project; on a freshly built identical fixture, `prune
      --events-days 30` prints `pruned 2 event(s), 1 session(s)` (the 30-day session exceeds
      the 8-day default too); a `session_start.py` payload
      in a repo with an existing brain performs the default prune with stdout identical to a
      run against a brain with no old rows; with no brain file `session_start.py` creates none.
      verify: `python3 .claude/hooks/tests/test_brain.py -k prune`
      contract: tests/test_brain.py · Prune.test_prune_removes_old_events_and_sessions and
      Prune.test_session_start_prunes_silently_and_never_creates · expected RED:
      `AssertionError: 2 != 0 : brain CLI did not run: … invalid choice: 'prune'`
- [ ] **A7 — Harness green, four hooks, machine checks.** `bash .claude/hooks/tests/run.sh`
      exits 0; its suite list has no `test_gate`, `test_token_efficiency` or
      `test_review_nudge`; its hostile-input sweep names four scripts and prints `4 hooks x 5
      hostile payloads`; the three latency medians are under 150 ms; inside its
      settings-present branch it fails with `a Stop hook is registered; this setup no longer
      ships one` when `jq -e '.hooks.Stop' "$SETTINGS"` succeeds, and with `~/.claude/state is
      no longer used; delete it` when `$HOME/.claude/state` exists.
      verify: `bash .claude/hooks/tests/run.sh`
      contract (file assertions): tests/test_structure.py ·
      InfiniteAutonomy.test_harness_has_no_stop_hook (verify: `python3
      .claude/hooks/tests/test_structure.py -k harness_has_no_stop_hook`) ·
      asserts `run.sh`'s suite list and sweep list, the `4 hooks x 5` string, and both
      machine-check messages, all read from the file · expected RED: `AssertionError:
      'test_gate' unexpectedly found in run.sh suite list`
- [ ] **A8 — Installer ships no Stop hook and says so.** The heredoc settings block inside
      `install.sh` (read from the file) has no `"Stop"` key and still has the `Task|Agent`
      PreToolUse matcher; the comment above it no longer names the verification gate or the
      review nudge; `test_install.py`'s installed-file list no longer contains `hooks/stop.py`.
      verify: `python3 .claude/hooks/tests/test_install.py`
      contract: tests/test_install.py · test_settings_block_registers_no_stop_hook · expected
      RED: `AssertionError: '"Stop"' unexpectedly found in …`
- [ ] **A9 — The workflow never stops itself.** `.claude/skills/gentic/SKILL.md` "Autonomous
      runs" contains `never a stop`, `rung 5`, `rung 8`, `escalat` and `only the \`STOP\` file`; `.claude/skills/gentic-iterate/SKILL.md` contains `escalates instead
      of halting`, `resets the balance`, `taken autonomously`, the worked example row
      `balance -3` (ASCII hyphen) and `resets to 13`, and no longer contains `stop and hand off` or `user
      check-ins`; `.claude/skills/gentic-execute/SKILL.md` still contains `check for `STOP``;
      `.claude/skills/gentic-brain/SKILL.md` lists `prune` and `sessions`, names only `red`
      and `verification` as hook kinds, and no longer says `No schema migrations exist`.
      verify: `python3 .claude/hooks/tests/test_structure.py -k workflow_prose_never_stops`
      contract: tests/test_structure.py · InfiniteAutonomy.test_workflow_prose_never_stops_itself
      · expected RED: `AssertionError: 'never a stop' not found in … gentic/SKILL.md`
- [ ] **A10 — Docs describe the hooks that exist.** `CLAUDE.md`'s hooks bullet is rewritten
      whole: it says `The hooks record, they never block`, describes only `red` and
      `verification` recording, and no longer says `they do not police`, `flags a turn` or
      `advisory`; its budget bullet and `ROUTING.md`'s say `escalates`; `README.md` has no
      `Stop hook`, `Stop-hook`, `verification gate` or `no schema migrations` phrase, says the
      budget `escalates instead of halting`, says `only the \`STOP\` file` ends a run early,
      and documents `prune`, `sessions` and `user_version`; `.claude/hooks/README.md` has no
      `Stop` row, no `Token-efficiency` section, documents the `sessions` table and `prune`,
      and lists exactly `red` and `verification` as event kinds; no markdown file under
      `.claude/`, `README.md` or `CLAUDE.md` mentions `stop.py` or `token_efficiency`.
      verify: `python3 .claude/hooks/tests/test_structure.py -k docs_describe_the_hooks`
      contract: tests/test_structure.py · InfiniteAutonomy.test_docs_describe_the_hooks_that_exist
      · expected RED: `AssertionError: 'they do not police' unexpectedly found in CLAUDE.md`
- [ ] **A11 — This machine runs no Stop hook and its brain is upgraded.** Each command with
      its exact PASS output:
      `jq '.hooks.Stop' ~/.claude/settings.json` → `null`;
      `test -f ~/.claude/settings.json.bak-<date recorded in progress.md> && echo ok` → `ok`;
      `test -f ~/.claude/gentic/brain.sqlite.bak-<same date> && echo ok` → `ok`;
      `./install.sh --check` (an existing mode that reports drift, changes nothing, and
      prints `in sync with <dest>` when clean) → last line `in sync with /Users/sebiko83/.claude`;
      `test ! -e ~/.claude/hooks/stop.py && test ! -e ~/.claude/hooks/lib/token_efficiency.py
      && test ! -e ~/.claude/state && echo ok` → `ok`;
      `python3 .claude/hooks/lib/brain.py sql "pragma user_version"` → `{"user_version": 2}`;
      `python3 .claude/hooks/lib/brain.py sql "select count(*) n from events"` → `n` ≥ 321
      (the live brain's oldest event is from 2026-09-02, 3 days old, so no prune can remove one
      during this run; a session-start prune on the live brain is expected and harmless).
      verify: the seven commands above, then `bash .claude/hooks/tests/run.sh` (its
      Configuration section passes)
      contract: tests/run.sh · the two machine checks from A7 · expected RED: before task 1,
      `jq '.hooks.Stop' ~/.claude/settings.json` prints the registered `stop.py` entry (not
      `null`) — pasted into `progress.md` as task 1's RED; before task 9 (after task 6 added
      the check), `run.sh` prints `FAIL  ~/.claude/state is no longer used; delete it` — pasted
      as task 9's RED
- [ ] **A12 — No dead state code.** The public surface of `lib/common.py` — module-level
      functions whose `__module__` is `common` and whose name has no leading underscore — is
      exactly `read_payload`, `emit`, `emit_context`, `emit_message`, `safe_main`, `git_root`;
      `common.py` imports only what it uses (`json`, `sys`, `Path`); `test_lib.py` has no
      `State` class and no `block` test; `test_evals.py` sets no `CLAUDE_HOOK_STATE_DIR`;
      `project_conventions.TRUST_FILE` resolves to `~/.claude/gentic/trusted-projects` by
      default and `GENTIC_TRUST` still overrides it.
      verify: `python3 .claude/hooks/tests/test_lib.py && python3
      .claude/hooks/tests/test_project_conventions.py -k authorized`
      contract: tests/test_lib.py · PublicSurface.test_common_exports_only_the_live_helpers ·
      expected RED: `AssertionError: Items in the first set but not the second: 'save_state',
      'load_state', …`; and tests/test_project_conventions.py ·
      Authorized.test_trust_file_derives_from_the_brain_path (default `TRUST_FILE` equals
      `brain.DEFAULT_PATH.parent / "trusted-projects"`) · expected RED: `AttributeError:
      module 'project_conventions' has no attribute 'brain'` or the path assertion

## Risks & early signals

- **Parallel-spawn contention on SQLite.** Five hook processes writing `sessions` at once may
  hit `SQLITE_BUSY` inside 144 ms → a lost count and A3's parallel test fails. Signal: A3 is
  built in task 3, before anything depends on it. Fallback (the only retry allowed): wrap the
  acquire in `BEGIN IMMEDIATE` with `timeout=0.233`; if still flaky, a rung-2 rework.
- **Latency.** Each valve call now opens SQLite; PreToolUse's median (40 ms today) must stay
  under 150 ms. Signal: `run.sh` after task 3.
- **Migration on the live brain.** The one non-reversible step; task 1's backup-API copy is
  the undo, and A4 proves the migration on a fixture before the live file is ever opened by
  migrating code.
- **Prose contracts are brittle.** `test_structure.py` string checks pin wording; when a
  sentence is rewritten, the test names the substring so the reason survives.
- **`safe_main` without `block`.** A surviving `block(` call would raise `AttributeError` →
  a visible `hook error` line. Signal: A1's grep for `block(` in the hook sources.

## Task order (for Execute)

1. Live machine, part 1: back up the live brain (backup API) and `settings.json`; remove
   `hooks.Stop`; observe A11's first RED from `run.sh` beforehand — A11 (half).
2. brain: `SCHEMA_VERSION`, `user_version` migrations, indexes, `events.run`, open-run tagging
   — A4, A5.
3. brain: `sessions` helpers; valve rewired in `pre_tool_use` / `post_tool_use` /
   `user_prompt_submit`; `common` state code removed; `TRUST_FILE` re-derived — A3, A12.
4. hooks: delete `stop.py`, `token_efficiency.py`, the ledger and guards; rewrite
   `test_tdd.py`, trim `test_brain.py`, delete the three suites — A1, A2.
5. brain: `prune`, `prune_quietly`, `session_start` — A6.
6. harness: `run.sh` lists, sweep, machine checks; installer; `test_install` — A7, A8.
7. skills prose — A9.
8. docs — A10.
9. Live machine, part 2: `./install.sh`, delete the named stale files and `~/.claude/state`,
   run the seven A11 commands — A11 (rest).

## Iteration budget

13 (initial allocation — the live balance is progress.md's; amendments never reset it. The
single exception is a taken rung 8, which resets the balance to 13 and is logged as such.)
