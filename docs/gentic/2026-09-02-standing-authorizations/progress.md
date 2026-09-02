# Run: standing-authorizations
Goal: A per-project consent layer — a `## gentic authorizations` section in the project's CLAUDE.md, read by a deterministic helper, that lets a run push and open a PR only when granted; plus a concurrency valve on subagent spawns and a STOP flag every phase honours.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 8 minor, all fixed inline; trust file added)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Helper `authorized` mode with the trust file; parser shape (H1, H2) | 3 | — | `tests/test_project_conventions.py::test_authorized_reads_the_section`, `::test_authorized_fails_closed`, `::test_branch_and_commit_still_need_a_slug` | | pending |
| 2 | Session lock, valve in both hooks, reset per prompt (H3) | 3 | — | `tests/test_guard_and_session.py::test_concurrency_valve_denies_a_sixth_agent`, `::test_valve_counts_parallel_spawns`, `::test_valve_resets_on_a_new_prompt` | | pending |
| 3 | Installer block, live settings, harness matcher assertion (H5) | 2 | 2 | `tests/test_install.py::test_settings_block_matcher_covers_subagents` | | pending |
| 4 | Wording in eight sites + structure tests (H4) | 3 | 1 | `tests/test_structure.py::StandingAuthorizations` (8) | | pending |
| 5 | Harness, install, regression run, repo state (H6, H7) | 2 | 1-4 | n/a — live observations | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–5.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Child run R5 of the epic `2026-09-02-self-improving-gentic` (brief items 14 and 16; item 15,
  budget as a currency, moves to `gentic-epic` where its consumer lives). Brain consulted: no
  prior notes on authorizations, pushes or concurrency.
