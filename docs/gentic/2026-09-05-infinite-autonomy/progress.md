# Run: infinite-autonomy
Goal: Remove the Stop hook, its gates/nudges and the token-efficiency guards and ledger; make runs continue autonomously without built-in stopping conditions; make gentic use the SQLite brain smartly.
Iteration budget: 12 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (all defaults adopted; user delegated)
- [x] 3 Masterprompt (critic: two passes, all blockers fixed inline)
- [x] 4 Execute (tasks 1–8 done; task 9 blocked: the permission classifier denies writes under `~/.claude`)
- [x] 5 Iterate (12/12 proven; 1 rung-1)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Live machine part 1: brain backup (backup API), settings backup, remove `hooks.Stop` | 1 | — | A11 first half: `jq '.hooks.Stop'` non-null before, `null` after | `jq '.hooks.Stop'` → `[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/stop.py\"","timeout":5}]}]`; after: `null` | done |
| 2 | brain: `SCHEMA_VERSION`, `user_version` migrations, five indexes, `events.run`, open-run tagging | 3 | 1 | test_brain.py `Migrations.test_old_brain_is_migrated_in_place`, `HooksWriteEvents.test_events_carry_the_open_run` | `AttributeError: module 'brain' has no attribute 'SCHEMA_VERSION'`; `sqlite3.OperationalError: no such column: run` | done |
| 3 | brain `sessions` helpers; valve rewired in pre/post/user_prompt hooks (plan drift: `common` state removal and `TRUST_FILE` moved to task 4 — the guards and Stop hook still use that code until then) | 3 | 2 | test_guard_and_session.py `ConcurrencyValve.test_valve_counts_parallel_spawns`, `test_valve_fails_open_without_a_brain` | `AssertionError: 0 != 5 : parallel spawns lost updates`; `AssertionError: 'deny' is not None : a spawn was denied although no brain could count it` | done |
| 4 | Delete `stop.py`, `token_efficiency.py`, the ledger and guards, `common` state code; `TRUST_FILE` re-derived; rewrite test_tdd.py, trim test_brain.py, delete three suites; run.sh suite list, sweep and machine checks (plan drift: pulled in from task 6 so the sweep no longer names a deleted script); test_install expected file (drift, from task 6) | 8 | 3 | test_structure.py `InfiniteAutonomy.test_stop_hook_and_token_guards_are_gone`, `test_harness_has_no_stop_hook`; test_tdd.py `RedLedger.test_event_kinds_are_exactly_red_and_verification`; test_lib.py `PublicSurface`; test_project_conventions.py `test_trust_file_derives_from_the_brain_path` | `AssertionError: True is not false : .claude/hooks/stop.py still exists`; `AssertionError: 'test_gate' unexpectedly found in 'for suite in …'`; `AssertionError: Tuples differ: ('red', 'verification', 'gate_block', …) != ('red', 'verification')`; `AssertionError: Items in the first set but not the second: 'save_state'…`; `AttributeError: module 'project_conventions' has no attribute 'brain'` | done |
| 5 | brain `prune`, `prune_quietly`, session_start wiring | 2 | 2 | test_brain.py `Prune.*` | `AssertionError: 2 != 0 : brain CLI did not run: usage: brain.py …` (no `prune` command); `AssertionError: 3 != 2 : the 120-day event survived a session start` | done |
| 6 | Installer block and comment; test_install (run.sh work moved to task 4) | 1 | 4 | test_install.py `test_settings_block_registers_no_stop_hook` | `AssertionError: '"Stop"' unexpectedly found in '"hooks": {…'` | done |
| 7 | Skills prose: gentic, gentic-iterate, gentic-brain | 2 | 4 | test_structure.py `InfiniteAutonomy.test_workflow_prose_never_stops_itself` | `AssertionError: 'never a stop' not found in '## autonomous runs…'` | done |
| 8 | Docs: CLAUDE.md, ROUTING.md, README.md, hooks README | 2 | 6, 7 | test_structure.py `InfiniteAutonomy.test_docs_describe_the_hooks_that_exist` | `AssertionError: 'the hooks record, they never block' not found in '# gentic…'` | done |
| 9 | Live machine part 2: install, delete stale files and `~/.claude/state`, A11 commands | 1 | 8 | run.sh machine check FAIL before, green after; seven A11 commands | observed at task 4: `FAIL  ~/.claude/state is no longer used; delete it` | done (user ran the sync command 2026-09-05; harness `all checks passed`) |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | A1 no Stop hook, no token guards | — | 0 | PROVEN — `test_structure.py -k stop_hook_and_token_guards` OK |
| 2 | A2 hooks record red/verification only | — | 0 | PROVEN — `test_tdd.py -k RedLedger` 5 tests OK |
| 3 | A3 valve counts in the brain | — | 0 | PROVEN — `test_guard_and_session.py -k ConcurrencyValve` 5 tests OK |
| 4 | A4 schema versioning | — | 0 | PROVEN — `test_brain.py -k migrat` OK |
| 5 | A5 events name the open run | 1 | 1 | FAILED as written (`-k "open_run or invisible"` → NO TESTS RAN, exit 5: unittest has no `or`); rung 1 amends the verify line to `-k open_run -k invisible` → 2 tests OK. Same class as brain lesson #2 (sqlite-brain D9) |
| 6 | A6 prune | — | 0 | PROVEN — `test_brain.py -k prune` 2 tests OK |
| 7 | A7 harness green, four hooks, machine checks | — | 0 | PROVEN after task 9: `run.sh` → `all checks passed`, 12 suites, `4 hooks x 5 hostile payloads`, medians 23/23/23 ms, `no Stop hook registered`, `no JSON session state directory` (first audit, before task 9, saw `FAIL ~/.claude/state is no longer used; delete it`) |
| 8 | A8 installer | — | 0 | PROVEN — `test_install.py` 18 tests OK |
| 9 | A9 workflow never stops itself | — | 0 | PROVEN — `test_structure.py -k workflow_prose_never_stops` OK |
| 10 | A10 docs | — | 0 | PROVEN — `test_structure.py -k docs_describe_the_hooks` OK |
| 11 | A11 live machine | — | 0 | PROVEN after task 9: `jq` → `null`; both `.bak-2026-09-05` files exist; `./install.sh --check` → `in sync with /Users/sebiko83/.claude`; stale files and `~/.claude/state` absent → `ok`; `pragma user_version` → 2; events 328 ≥ 321 (first audit, before task 9: install out of sync, stale files present) |
| 12 | A12 no dead state code | — | 0 | PROVEN — `test_lib.py` 12 OK; `test_project_conventions.py -k authorized` OK |

## Notes / handoff
- 2026-09-05 Iterate: 9/12 proven, 1 rung-1 (A5 verify syntax), A7 and A11 blocked on the
  live-machine sync the permission classifier denies (`./install.sh`, `rm -r ~/.claude/state`).
  **Resume:** the user runs, from `~/code/gentic`: `./install.sh`; `rm ~/.claude/hooks/stop.py
  ~/.claude/hooks/lib/token_efficiency.py ~/.claude/hooks/tests/test_gate.py
  ~/.claude/hooks/tests/test_token_efficiency.py ~/.claude/hooks/tests/test_review_nudge.py`;
  `rm -r ~/.claude/state`; then `bash .claude/hooks/tests/run.sh` must print `all checks passed`
  and `./install.sh --check` must print `in sync`. That closes task 9, A7 and A11; then tick
  phase 5 and write the final report. Until then the installed hooks are the pre-run copies
  (Stop unregistered since task 1) and keep recreating `~/.claude/state`.
- 2026-09-05 task 4: the permission classifier denied `./install.sh` and `rm -r ~/.claude/state`
  (both write under `~/.claude`). The repo is complete and its unit suites are green; on this
  machine `run.sh`'s Configuration section reports `FAIL  ~/.claude/state is no longer used;
  delete it` until the user runs the three commands in the final report (install, delete the
  five stale files, delete the state directory). The live hooks are therefore still the
  pre-run copies (Stop hook unregistered since task 1, so they only keep writing JSON state).
- 2026-09-05 task 1: backups taken with date string `2026-09-05` — `~/.claude/gentic/brain.sqlite.bak-2026-09-05` (sqlite backup API, 303104 bytes) and `~/.claude/settings.json.bak-2026-09-05`; `hooks.Stop` removed with `jq 'del(.hooks.Stop)'`, every other key identical. A11 reads this date string.

## Final report (2026-09-05)

**Mission.** No hook ends a turn and no rule ends a run on its own; the SQLite brain is the one
store the hooks use. Delivered on `gentic/infinite-autonomy`, 15 checkpoint commits.

**Definition of Done — 12/12 proven, fresh at close:** A1 `test_structure -k stop_hook_and_token_guards` OK ·
A2 `test_tdd -k RedLedger` 5 OK · A3 `test_guard_and_session -k ConcurrencyValve` 5 OK · A4 `test_brain -k migrat` OK ·
A5 `test_brain -k open_run -k invisible` 2 OK · A6 `test_brain -k prune` 2 OK · A7 `run.sh` all checks passed
(medians 23/23/23 ms) · A8 `test_install` 18 OK · A9 `test_structure -k workflow_prose_never_stops` OK ·
A10 `test_structure -k docs_describe_the_hooks` OK · A11 seven machine commands as listed in the log ·
A12 `test_lib` 12 OK, `test_project_conventions -k authorized` OK.

**Points spent:** 1 of 13 (rung 1, A5's verify line). Lesson recorded in the brain.

**Unconfirmed defaults (all delegated; reverse any in `decisions.md`):** budget escalates instead
of being removed; rungs 5/8 taken autonomously; `STOP` file and the five-subagent valve kept; a
brain that cannot be opened fails open; session state in the brain's `sessions` table;
migrations + indexes + `prune` + run-tagged events as the "smart" additions; retention 89 days
events / 8 days sessions; live settings edited with a dated backup; `~/.claude/state` deleted
without backup; one run rather than the critic's two.

**Deliberately not done (non-goals):** no replacement gate or nudge in any channel; no token or
cost accounting; no backfill of `events.run` for the 321 pre-run rows; no cap on rung-8 resets;
no new brain subcommands beyond `prune`; installer still copy-only; evals, agents, `/ship`,
release lane untouched.

**Blocked, then unblocked:** the permission classifier denied `./install.sh` and
`rm -r ~/.claude/state` from the run; the user ran the handoff command by hand and the harness
went green. Brain note `permission-classifier-home-writes` records it.

**What `/ship` would do:** this repository grants neither `push` nor `open-pr`, so nothing was
pushed. `/ship` would verify (green), review the diff, push `gentic/infinite-autonomy` and open
a PR against `main` (PR #2 already carries the earlier child runs on
`gentic/self-improving-gentic`; this branch continues from its head).
