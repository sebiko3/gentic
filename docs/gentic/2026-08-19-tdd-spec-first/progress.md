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
| 1 | Ledger: record failing verification as RED, classify test files (D5, D6) | 3 | — | `tests/test_tdd.py::test_failing_verification_is_recorded_as_red`, `::test_test_files_are_classified_separately` | | pending |
| 2 | `stop.py`: advisory TDD nudge, suppressed and once per session (D7, D8) | 3 | 1 | `tests/test_tdd.py::test_tdd_nudge_is_advisory`, `::test_tdd_nudge_suppressed_and_bounded` | | pending |
| 3 | New `gentic-tdd` skill; `GENTIC_SKILL` regex and `run.sh` skill count updated (D1) | 3 | — | `tests/test_structure.py::test_gentic_tdd_skill_is_self_contained` | | pending |
| 4 | `gentic-execute` routes tasks through `gentic-tdd`; empty RED cell blocks ticking (D2) | 2 | 3 | `tests/test_structure.py::test_execute_routes_tasks_through_tdd` | | pending |
| 5 | `gentic-masterprompt`: test contract per DoD item + critique scan (D3) | 2 | — | `tests/test_structure.py::test_masterprompt_requires_test_contracts` | | pending |
| 6 | `gentic/SKILL.md`: task-table template gains Test and RED columns (D4) | 1 | — | `tests/test_structure.py::test_task_table_template_has_tdd_columns` | | pending |
| 7 | README.md and CLAUDE.md document the test-first spine (D9) | 2 | 3 | `tests/test_structure.py::test_docs_document_the_tdd_spine` | | pending |
| 8 | Whole harness green; superpowers refs still conditional; install path handles skill 7 (D10, D11, D12) | 2 | 1-7 | `bash .claude/hooks/tests/run.sh` | | pending |

Sizes are planning estimates only; they never spend the iteration budget.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
