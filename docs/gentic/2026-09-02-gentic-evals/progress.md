# Run: gentic-evals
Goal: A fitness function for gentic — an eval suite in the official plugin-eval case layout, run headlessly with and without gentic, graded deterministically, scored into the brain; plus an agent fixture bank as eval cases and UI test runners counted as verification evidence.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 6 blocking / 21 serious / 12 minor on draft 1, all fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Runner skeleton: flat parser, discovery, argv, preflight, `--dry-run`; fake-`claude` test harness (E0, E1) | 5 | — | `tests/test_evals.py::test_preflight_refuses_a_missing_flag`, `::test_dry_run_lists_cases_and_argv` | `AssertionError: 2 != 1 : runner did not refuse`; `AssertionError: 2 != 0 : runner did not run: … can't open file '…/evals/run.py'` | done |
| 2 | Invocation and per-run workspaces, `GENTIC_BRAIN` redirection (E2) | 2 | 1 | `::test_invocation_flags_per_arm` | | pending |
| 3 | Graders, created-file snapshot, scaffold, timeout (E3, E4) | 5 | 2 | `::test_graders_score_a_replayed_transcript`, `::test_scaffold_runs_first_and_is_not_created` | | pending |
| 4 | Brain `eval_runs`/`eval_graders`, record functions, `brain evals`, runner integration, `--no-brain` (E5) | 3 | 2 | `::test_brain_rows_and_evals_summary` | | pending |
| 5 | Money ceiling, order, exit codes, `result.json` totals (E6) | 2 | 3 | `::test_money_ceiling_and_exit_codes` | | pending |
| 6 | The five cases, fixtures, scaffolds, manifest, gitignore (E7, E12) | 5 | 3 | `::test_five_cases_are_well_formed`, `::test_manifest_and_gitignore` | | pending |
| 7 | Verification regex gains the UI runners (E8) | 1 | — | `tests/test_tdd.py::test_ui_test_runners_are_verification_commands` | | pending |
| 8 | Harness registration and docs (E10, E11) | 2 | 1-7 | `::test_harness_registers_evals_offline`, `::test_docs_evals_are_documented` | | pending |
| 9 | Live proof: install check, real suite run, `brain evals`, lessons for failures (E9) | 2 | 8 | n/a — observation of the real system; output pasted here | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order: 1-9 as listed (runner first, cases once the runner can grade them, live proof last).

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Child run R2 of the epic `2026-09-02-self-improving-gentic`. Brain consulted first (2 lessons,
  1 note recalled); three scouting facts noted into the brain under run `gentic-evals`.
