# Run: self-improving-gentic
Goal: Turn gentic from a single-threaded spec-first workflow into a self-improving, multi-orchestrator system that takes one short prompt ("make this calendar app 100% more awesome") through scouting, spec, build, UI tests, review, PR, CI and deploy — and learns from every run.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all; added the SQLite brain)
- [x] 3 Masterprompt (epic index; child runs carry the specs)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| R1 | child run `2026-09-02-sqlite-brain` | 8 | — | its own DoD | see child (13/13 proven, 2 rung-1 fixes) | done |
| R2 | child run `gentic-evals` | 8 | R1 | its own DoD | — | pending |
| R3 | child run `adjective-compiler-and-retro` | 5 | R1 | its own DoD | — | pending |
| R4 | child run `standing-authorizations` | 5 | — | its own DoD | — | pending |
| R5 | child run `ui-contracts` | 8 | R2 | its own DoD | — | pending |
| R6 | child run `release-lane` | 8 | R4 | its own DoD | — | pending |
| R7 | child run `gentic-epic` | 8 | R3, R4, R5 | its own DoD | — | pending |
| R8 | child run `orchestrator-mesh` | 8 | R1, R7 | its own DoD | — | pending |
| R9 | child run `gardener` | 8 | R2, R3 | its own DoD | — | pending |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- 2026-09-02: Scout complete. The user asked for *ways to improve* gentic, not for a build, so
  the brief doubles as the proposal: an improvement catalogue of 18 mechanisms grouped into a
  seven-run roadmap, and eight open decisions each with a recommended default. The Interview is
  the user's choice of which run to start first; every default is autonomous-safe, so `resume`
  can proceed without them if the user delegates.
- This goal is an epic, not one run. The brief's roadmap names the runs; this directory closes
  once the first one (`gentic-evals`) is chosen and started as its own run.
- 2026-09-02: User delegated all decisions and chose an SQLite brain. The brain is now R1; the
  roadmap grew to nine runs (the retro/adjective work split out of the old R2 because it depends
  on the brain). Child run `2026-09-02-sqlite-brain` started in this session.
- 2026-09-02: R1 `sqlite-brain` complete on this branch. Next: R2 `gentic-evals` — its scout should `recall` and `lessons` first; the brain now has content.
