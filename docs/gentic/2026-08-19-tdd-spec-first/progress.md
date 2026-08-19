# Run: tdd-spec-first
Goal: Make TDD and spec-driven development the enforced backbone of the gentic workflow, superpowers-style.
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
| 1 | Ledger: record failing verification as RED, classify test files (D5, D6) | 3 | — | `tests/test_tdd.py::test_failing_verification_is_recorded_as_red`, `::test_test_files_are_classified_separately` | `AssertionError: None is not true : no RED recorded for a failing verification command`; `AssertionError: None is not true : test file edit was not recorded` | done |
| 2 | `stop.py`: advisory TDD nudge, suppressed and once per session (D7, D8) | 3 | 1 | `tests/test_tdd.py::test_tdd_nudge_is_advisory`, `::test_tdd_nudge_suppressed_and_bounded`, `::test_both_nudges_arrive_as_one_message` | `AssertionError: 'failing test' not found in '…not reviewed yet this session…'`; `AssertionError: 0 != 1 : nudge fired twice in one session`. Mid-task RED: routing TDD first silenced the review nudge — `test_review_nudge` failed 2/2 until both were combined into one message | done |
| 3 | New `gentic-tdd` skill; `GENTIC_SKILL` regex and `run.sh` skill count updated (D1) | 3 | — | `tests/test_structure.py::test_gentic_tdd_skill_is_self_contained`, `::test_gentic_tdd_is_validated_like_the_other_phase_skills` | `AssertionError: False is not true : .claude/skills/gentic-tdd/SKILL.md does not exist`; `AssertionError: Regex didn't match … GENTIC_SKILL does not cover gentic-tdd` | done |
| 4 | `gentic-execute` routes tasks through `gentic-tdd`; empty RED cell blocks ticking (D2) | 2 | 3 | `tests/test_structure.py::test_execute_routes_tasks_through_tdd` | `AssertionError: 'gentic-tdd' not found in … : gentic-execute does not invoke gentic-tdd` | done |
| 5 | `gentic-masterprompt`: test contract per DoD item + critique scan (D3) | 2 | — | `tests/test_structure.py::test_masterprompt_requires_test_contracts` | | pending |
| 6 | `gentic/SKILL.md`: task-table template gains Test and RED columns (D4) | 1 | — | `tests/test_structure.py::test_task_table_template_has_tdd_columns` | | pending |
| 7 | README.md and CLAUDE.md document the test-first spine (D9) | 2 | 3 | `tests/test_structure.py::test_docs_document_the_tdd_spine` | | pending |
| 8 | Whole harness green; superpowers refs still conditional; install path handles skill 7 (D10, D11, D12) | 2 | 1-7 | `bash .claude/hooks/tests/run.sh` | | pending |

Sizes are planning estimates only; they never spend the iteration budget.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff

**Task 2 note (plan drift, not spec drift).** Implementing the TDD nudge as "one advisory message
per stop, TDD wins" broke `test_review_nudge` — the review nudge was silently suppressed. Fixed by
combining both nudges into a single `systemMessage` instead of letting them compete. No DoD item
changed; the existing suite caught it, which is the intended behaviour of the harness.
