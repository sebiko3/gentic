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
| R2 | child run `gentic-evals` | 8 | R1 | its own DoD | see child (13/13 proven; first score 0.70 vs 0.87) | done |
| R3 | child run `2026-09-02-eval-fidelity` (re-scoped from adjective-compiler-and-retro; that work moves to R4+) | 5 | R2 | its own DoD | see child (9/10 proven, F8 in substance; first trustworthy score 0.92 vs 0.35) | done |
| R4 | child run `2026-09-02-skill-tuning-by-evals` (inserted by R3's findings; standing-authorizations becomes R5) | 3 | R3 | its own DoD | see child (9/9 proven; with 1.00 / without 0.20) | done |
| R5 | child run `2026-09-02-standing-authorizations` | 5 | R4 | its own DoD | see child (7/7 proven; regression 4/4) | done |
| R6 | child run `2026-09-02-ui-contracts` | 8 | R2 | its own DoD | see child (7/8 proven; U8 closed unproven by the user) | done |
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
- 2026-09-02: R2 `gentic-evals` complete. First fitness number is negative (with 0.70, without 0.87); three lessons in the brain define R3's scope: headless turn cost of the phases, errored-run scoring, discriminating agent graders, transcript capture.
- 2026-09-02: R3 `eval-fidelity` complete. The fitness number is now trustworthy: with 0.92, without 0.35, delta +0.57. Four evidence-backed change requests sit in the brain (interview must continue headless; executor report block; without-arm HOME isolation; pii grader symmetry). Suggested R4: `skill-tuning-by-evals` — apply the interview and executor findings and prove them with the suite; the adjective compiler and retro follow.
- 2026-09-02: R4 `skill-tuning-by-evals` complete — the first evidence-driven change to gentic itself, proven by the suite (with 1.00, without 0.20). Remaining roadmap: standing-authorizations, ui-contracts, release-lane, gentic-epic, orchestrator-mesh, gardener, then the adjective compiler and retro.
- 2026-09-02: R5 `standing-authorizations` complete — grants in CLAUDE.md plus a machine-side trust file; runs may push and open PRs only when both hold; valve at 5 subagents; STOP file. Next: `ui-contracts`, then `release-lane` (the first real push under a grant).
- 2026-09-02: R6 `ui-contracts` — U1–U7 proven (grammar, TDD, Scout variant, Iterate, ui-tester agent, README, harness, live browser dispatch with evidence); U8's regression gate failed twice on harness limits (55-turn exhaustion, then a 900 s timeout), both fixed; a third billed run awaits the user.
- 2026-09-02: R6 closed by the user with U8 unproven. Next: `release-lane` (the first real push under a grant, CI watched, preview deploy), then `gentic-epic`, `orchestrator-mesh`, `gardener`, `adjective-compiler-and-retro`. PR #2 is open for everything so far.
