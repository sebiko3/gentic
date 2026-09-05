# Run: infinite-autonomy
Goal: Remove the Stop hook, its gates/nudges and the token-efficiency guards and ledger; make runs continue autonomously without built-in stopping conditions; make gentic use the SQLite brain smartly.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (all defaults adopted; user delegated)
- [x] 3 Masterprompt (critic: two passes, all blockers fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Live machine part 1: brain backup (backup API), settings backup, remove `hooks.Stop` | 1 | — | A11 first half: `jq '.hooks.Stop'` non-null before, `null` after | `jq '.hooks.Stop'` → `[{"hooks":[{"type":"command","command":"python3 \"$HOME/.claude/hooks/stop.py\"","timeout":5}]}]`; after: `null` | done |
| 2 | brain: `SCHEMA_VERSION`, `user_version` migrations, five indexes, `events.run`, open-run tagging | 3 | 1 | test_brain.py `Migrations.test_old_brain_is_migrated_in_place`, `HooksWriteEvents.test_events_carry_the_open_run` | `AttributeError: module 'brain' has no attribute 'SCHEMA_VERSION'`; `sqlite3.OperationalError: no such column: run` | done |
| 3 | brain `sessions` helpers; valve rewired in pre/post/user_prompt hooks (plan drift: `common` state removal and `TRUST_FILE` moved to task 4 — the guards and Stop hook still use that code until then) | 3 | 2 | test_guard_and_session.py `ConcurrencyValve.test_valve_counts_parallel_spawns`, `test_valve_fails_open_without_a_brain` | `AssertionError: 0 != 5 : parallel spawns lost updates`; `AssertionError: 'deny' is not None : a spawn was denied although no brain could count it` | done |
| 4 | Delete `stop.py`, `token_efficiency.py`, the ledger and guards, `common` state code; `TRUST_FILE` re-derived; rewrite test_tdd.py, trim test_brain.py, delete three suites; run.sh suite list, sweep and machine checks (plan drift: pulled in from task 6 so the sweep no longer names a deleted script); test_install expected file (drift, from task 6) | 8 | 3 | test_structure.py `InfiniteAutonomy.test_stop_hook_and_token_guards_are_gone`, `test_harness_has_no_stop_hook`; test_tdd.py `RedLedger.test_event_kinds_are_exactly_red_and_verification`; test_lib.py `PublicSurface`; test_project_conventions.py `test_trust_file_derives_from_the_brain_path` | `AssertionError: True is not false : .claude/hooks/stop.py still exists`; `AssertionError: 'test_gate' unexpectedly found in 'for suite in …'`; `AssertionError: Tuples differ: ('red', 'verification', 'gate_block', …) != ('red', 'verification')`; `AssertionError: Items in the first set but not the second: 'save_state'…`; `AttributeError: module 'project_conventions' has no attribute 'brain'` | done |
| 5 | brain `prune`, `prune_quietly`, session_start wiring | 2 | 2 | test_brain.py `Prune.*` | `AssertionError: 2 != 0 : brain CLI did not run: usage: brain.py …` (no `prune` command); `AssertionError: 3 != 2 : the 120-day event survived a session start` | done |
| 6 | Harness: run.sh suite list, sweep, machine checks; installer block; test_install | 2 | 4 | test_structure.py `InfiniteAutonomy.test_harness_has_no_stop_hook`; test_install.py `test_settings_block_registers_no_stop_hook` | | pending |
| 7 | Skills prose: gentic, gentic-iterate, gentic-brain | 2 | 4 | test_structure.py `InfiniteAutonomy.test_workflow_prose_never_stops_itself` | | pending |
| 8 | Docs: CLAUDE.md, ROUTING.md, README.md, hooks README | 2 | 6, 7 | test_structure.py `InfiniteAutonomy.test_docs_describe_the_hooks_that_exist` | | pending |
| 9 | Live machine part 2: install, delete stale files and `~/.claude/state`, A11 commands | 1 | 8 | run.sh machine check FAIL before, green after; seven A11 commands | observed at task 4: `FAIL  ~/.claude/state is no longer used; delete it` | blocked — see notes |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- 2026-09-05 task 4: the permission classifier denied `./install.sh` and `rm -r ~/.claude/state`
  (both write under `~/.claude`). The repo is complete and its unit suites are green; on this
  machine `run.sh`'s Configuration section reports `FAIL  ~/.claude/state is no longer used;
  delete it` until the user runs the three commands in the final report (install, delete the
  five stale files, delete the state directory). The live hooks are therefore still the
  pre-run copies (Stop hook unregistered since task 1, so they only keep writing JSON state).
- 2026-09-05 task 1: backups taken with date string `2026-09-05` — `~/.claude/gentic/brain.sqlite.bak-2026-09-05` (sqlite backup API, 303104 bytes) and `~/.claude/settings.json.bak-2026-09-05`; `hooks.Stop` removed with `jq 'del(.hooks.Stop)'`, every other key identical. A11 reads this date string.
