# Run: token-efficiency-hooks
Goal: Build hooks that reduce token waste in Claude Code sessions.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Duplicate-read guard with valve; legacy state upgrades in place (D1, D2, D7) | 5 | — | `tests/test_token_efficiency.py::test_duplicate_read_is_denied_once`, `::test_valve_never_denies_twice_per_path`, `::test_legacy_state_upgrades_in_place` | | pending |
| 2 | Bare-cat guard, cwd-resolved, shared valve ledger (D3) | 3 | 1 | `tests/test_token_efficiency.py::test_bare_cat_of_large_file_is_denied_once` | | pending |
| 3 | Spend accumulation (Read + Bash) and repeat counting (D4, D6) | 3 | 1 | `tests/test_token_efficiency.py::test_spend_accumulates_across_turns`, `::test_repeat_readonly_bash_counted_not_denied` | | pending |
| 4 | Stop spend report — threshold, once, joined advisory (D5) | 2 | 3 | `tests/test_token_efficiency.py::test_spend_report_threshold_and_once` | | pending |
| 5 | Hooks README documents guards, valve, estimates (D9) | 1 | 1-4 | `tests/test_token_efficiency.py::test_docs_document_the_guards` | | pending |
| 6 | Harness registration and full green; install --check lists new files (D8, D10) | 2 | 1-5 | `bash .claude/hooks/tests/run.sh`; `./install.sh --check` | | pending |

Sizes are planning estimates only; they never spend the iteration budget.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
