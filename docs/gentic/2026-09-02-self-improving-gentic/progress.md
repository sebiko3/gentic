# Run: self-improving-gentic
Goal: Turn gentic from a single-threaded spec-first workflow into a self-improving, multi-orchestrator system that takes one short prompt ("make this calendar app 100% more awesome") through scouting, spec, build, UI tests, review, PR, CI and deploy — and learns from every run.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [ ] 2 Interview
- [ ] 3 Masterprompt
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|

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
