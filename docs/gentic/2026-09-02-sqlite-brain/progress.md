# Run: sqlite-brain
Goal: Give gentic a persistent SQLite brain — structured memory (lessons, decisions, runs, events, stamps) plus free-form notes with full-text recall and unrestricted SQL — written to by the hooks and read by the phase skills.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 6 blocking / 15 serious / 8 minor, all fixed inline; second cold read clean)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | `lib/brain.py` core: schema, project key, note/recall (FTS + LIKE), sql with .bak, record_event with scrubbing (D1, D2, D6 storage) | 5 | — | `tests/test_brain.py::test_note_then_recall_finds_it`, `::test_recall_falls_back_to_like`, `::test_sql_is_unrestricted_inside_the_brain`, `::test_sql_destructive_statement_leaves_a_backup` | `AssertionError: 2 != 0 : brain CLI did not run: … can't open file '…/lib/brain.py'` (all four) | done |
| 2 | Hook wiring (post_tool_use, stop) + invisibility guard + third latency median (D6, D7, D12 latency) | 3 | 1 | `::test_hooks_write_events_to_the_brain`, `::test_brain_failure_is_invisible_to_hooks` | `AssertionError: 0 != 1 : no red event in brain`; after wiring, unguarded: `AssertionError: 'hook error' unexpectedly found in '{"systemMessage": "hook error (__main__): [Errno 20] Not a directory: …"}'` | done |
| 3 | decide/preference, lesson/lessons/stats, run/stamp, scoping (D3, D4, D5, D9) | 5 | 1 | `::test_preference_needs_two_agreeing_user_decisions`, `::test_lessons_recorded_and_summarised`, `::test_run_lifecycle_and_stamps`, `::test_lessons_default_to_current_project` | | pending |
| 4 | session_start brain line (D8) | 2 | 3 | `::test_session_start_mentions_brain_when_it_has_something` | | pending |
| 5 | `gentic-brain` skill, wiring into six skills, structure test, run.sh count + registration + isolation (D10, D12) | 3 | 1 | `tests/test_structure.py::test_brain_skill_is_wired_into_the_phases`, `tests/test_brain.py::test_harness_registers_and_isolates_the_brain_suite` | | pending |
| 6 | README + hooks README + installer test (D11, D13) | 2 | 1-5 | `::test_docs_document_the_brain`, `tests/test_install.py::test_source_list_includes_the_brain` | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order: 1, 2 (riskiest: hot-path latency), 3, 4, 5, 6.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Child run R1 of the epic `2026-09-02-self-improving-gentic`; its brief and decisions apply.
