# Run: ui-contracts
Goal: UI becomes a first-class Definition-of-Done contract — an executable e2e spec as the contract, a `ui-tester` agent that drives the real browser and files screenshots as evidence, and a Scout that walks a running product before it asks anything.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated; one user decision: Claude in Chrome is the browser of choice)
- [x] 3 Masterprompt (critic: 3 blocking / 15 serious / 10 minor, all fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Structure tests (`UiContracts`, `EXPECTED_AGENTS`), then `ui-tester.md` (U4) | 3 | — | `tests/test_structure.py::test_ui_agent_is_defined`, `::test_exactly_the_expected_agents_exist`, `::test_each_agent_states_what_it_returns` | | pending |
| 2 | Skill wording: masterprompt grammar, tdd, scout variant, iterate (U1, U2, U3) | 3 | — | `::test_ui_grammar_in_masterprompt`, `::test_ui_tdd_names_ui_tasks`, `::test_ui_scout_walks_the_product`, `::test_ui_iterate_dispatches_the_tester` | | pending |
| 3 | README; harness (U5, U6) | 2 | 1-2 | `::test_ui_readme_documents_contracts`; `run.sh` | | pending |
| 4 | Install; live dispatch against the fixture; regression (U7, U8) | 3 | 3 | n/a — live observations | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–4.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Child run R6 of the epic `2026-09-02-self-improving-gentic` (brief items 11 and 13, the
  `ui-tester` agent). The user stated Claude in Chrome is connected and wants it used.
