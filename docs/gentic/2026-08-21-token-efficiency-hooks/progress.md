# Run: token-efficiency-hooks
Goal: Build hooks that reduce token waste in Claude Code sessions.
Iteration budget: 13 of 13 remaining — no escalation rung was spent.

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [x] 4 Execute
- [x] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Duplicate-read guard with valve; legacy state upgrades in place (D1, D2, D7) | 5 | — | `tests/test_token_efficiency.py::test_duplicate_read_is_denied_once`, `::test_valve_never_denies_twice_per_path`, `::test_legacy_state_upgrades_in_place` | `AssertionError: 0 != 2 : duplicate read was not denied`; `AssertionError: 0 != 2 : no deny on legacy state`; valve test failed at its precondition (same missing-feature RED) | done |
| 2 | Bare-cat guard, cwd-resolved, shared valve ledger (D3) | 3 | 1 | `tests/test_token_efficiency.py::test_bare_cat_of_large_file_is_denied_once`, `::test_bounded_and_composed_forms_pass`, `::test_relative_path_resolves_against_cwd` | `AssertionError: 0 != 2 : bare cat passed`; `AssertionError: 0 != 2 : relative bare cat was not resolved against cwd` | done |
| 3 | Spend accumulation (Read + Bash) and repeat counting (D4, D6) | 3 | 1 | `tests/test_token_efficiency.py::test_spend_accumulates_across_turns`, `::test_repeat_readonly_bash_counted_not_denied`, `::test_intervening_edit_resets_repeat_eligibility`, `::test_mutating_commands_are_not_repeat_tracked` | `AssertionError: 0 not greater than 0 : no spend recorded`; `AssertionError: 0 != 1 : repeat not counted` | done |
| 4 | Stop spend report — threshold, once, joined advisory (D5) | 2 | 3 | `tests/test_token_efficiency.py::test_spend_report_threshold_and_once`, `::test_below_threshold_stays_silent` | `AssertionError: 'tokens' not found in '' : no spend report` | done |
| 5 | Hooks README documents guards, valve, estimates (D9) | 1 | 1-4 | `tests/test_token_efficiency.py::test_docs_document_the_guards` | `AssertionError: 'duplicate' not found in … : hooks README does not document the read guard` | done |
| 6 | Harness registration and full green; install --check lists new files (D8, D10) | 2 | 1-5 | `bash .claude/hooks/tests/run.sh`; `./install.sh --check` | registration RED: `run.sh` output contained 0 `test_token_efficiency` lines before the suite-list edit | done |

Sizes are planning estimates only; they never spend the iteration budget.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | D1 duplicate read denied with full message | — | 0 | PROVEN — `test_duplicate_read_is_denied_once` → OK |
| 2 | D2 valve: retry, offset/limit, modified file all pass | — | 0 | PROVEN — `test_valve_never_denies_twice_per_path`, `test_read_with_offset_or_limit_always_passes`, `test_modified_file_passes_and_refreshes_the_ledger` → OK |
| 3 | D3 bare cat > 89 KB denied once; composed forms pass | — | 0 | PROVEN — `test_bare_cat_of_large_file_is_denied_once`, `test_bounded_and_composed_forms_pass` → OK |
| 4 | D4 spend accumulates across turns | — | 0 | PROVEN — `test_spend_accumulates_across_turns` → OK |
| 5 | D5 spend report: threshold, once, joined | — | 0 | PROVEN — `test_spend_report_threshold_and_once`, `test_below_threshold_stays_silent` → OK |
| 6 | D6 repeats counted, never denied; edit resets | — | 0 | PROVEN — `test_repeat_readonly_bash_counted_not_denied`, `test_intervening_edit_resets_repeat_eligibility` → OK |
| 7 | D7 legacy state upgrades in place | — | 0 | PROVEN — `test_legacy_state_upgrades_in_place` → OK (session facts survive) |
| 8 | D8 harness green, suite registered, latency held | — | 0 | PROVEN — `run.sh` → exit 0, `test_token_efficiency (Ran 15 tests)`, medians 22.5 / 24.5 ms |
| 9 | D9 hooks README documents guards/valve/estimates | — | 0 | PROVEN — `test_docs_document_the_guards` → OK |
| 10 | D10 install path sees both new files | — | 0 | PROVEN — `./install.sh --check` lists `lib/token_efficiency.py` and `tests/test_token_efficiency.py`, exit 1 |

Checks run directly under the dod-auditor rule (no subagent dispatch in this session);
verification-before-completion applied with fresh outputs. Budget: 13 of 13 remaining — no rung
spent. Every feature test went RED first (evidence in the task table); the negative-space tests
(composed cat forms, mutating commands) passed on arrival by design — they pin the guards'
boundaries, not their existence.

## Notes / handoff

**Mechanism note (task 1).** `pre_tool_use.py`'s existing agentignore denies use the
`permissionDecision` JSON on stdout; the new guards use `common.block()` (exit 2 + stderr) as the
masterprompt pinned. Both are honoured PreToolUse deny channels in Claude Code. State is saved
before blocking, mirroring the verification gate's record-then-block pattern.
