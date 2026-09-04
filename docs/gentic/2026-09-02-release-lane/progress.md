# Run: release-lane
Goal: After the PR opens, the run watches CI, feeds failures back as rung-1 fixes, deploys a preview and smokes it, and merges on green — each step gated by the project's grants — with a deterministic helper over `gh` and, for this repository, its first CI workflow.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated; the request itself is the "on request" for CI in this repo)
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
- Child run R7 of the epic `2026-09-02-self-improving-gentic` (brief item 12). PR #2 is the live
  target; this repo grants nothing and is untrusted, so the gated steps are exercised as refusals.
