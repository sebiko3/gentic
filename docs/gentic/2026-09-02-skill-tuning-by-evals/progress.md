# Run: skill-tuning-by-evals
Goal: Apply the two workflow findings the fitness suite produced — a headless Interview must continue instead of stopping to flag, and the task-executor must always answer in its report block — plus the PII grader's symmetry and budget-exhaustion scoring, and prove the changes with the suite.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 5 blocking / 12 serious / 9 minor, all fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Contract tests, then the three wording changes: Interview rule, orchestrator section + red flag, executor block (G1, G2, G3) | 3 | — | `tests/test_structure.py::test_interview_continues_when_no_question_can_be_asked`, `::test_orchestrator_has_an_autonomous_runs_section`, `::test_executor_block_is_the_entire_message` | `AssertionError: '`askuserquestion` is unavailable' not found in …`; `AssertionError: '## autonomous runs' not found in …`; `AssertionError: 'entire final message' not found in '## output…'` | done |
| 2 | PII pattern symmetric + pinned + negative fixture; `error_max_*` exhaustion (G4, G5) | 2 | — | `tests/test_evals.py::test_definition_graders_are_in_place`, `::test_pii_grader_rejects_a_silent_decision`, `::test_budget_exhaustion_is_graded_like_turns` | `AssertionError: '(pas[81 chars]ault)' != '(pas[81 chars]ault)|(unconfirmed|exclud|…' ` (old pattern vs new, both tests); `AssertionError: False is not true : file grader failed on a budget-exhausted run: claude exited 1:` | done |
| 3 | README bullet; harness (G6, G7) | 1 | 1-2 | `tests/test_structure.py::test_readme_says_headless_runs_continue`; `run.sh` | `AssertionError: 'no `askuserquestion`' not found in '# gentic…'`; G7: n/a — runner of the others | done |
| 4 | Install, live proof, comparison, lessons (G8, G9) | 2 | 3 | no test contract — the live run is the check | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–4.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Child run R4 of the epic `2026-09-02-self-improving-gentic`: the first time the loop changes
  gentic itself from suite evidence (brain lessons #7, #9, #11, #12; notes #12, #13).
