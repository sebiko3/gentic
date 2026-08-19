# Run: project-scoped-conventions
Goal: gentic follows each project's own branch and commit conventions instead of imposing its own everywhere.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Status (pending/in progress/done) |
|---|------|------|------------|--------|
| 1 | `lib/project_conventions.py` + `tests/test_project_conventions.py`, wired into `run.sh:14` | 5 | — | pending |
| 2 | `test_structure.py` case: neither hardcoded form survives unconditionally (DoD 8) | 2 | 1 | pending |
| 3 | Rewrite the 4 branch sites and 4 commit sites in skills and `/ship` (DoD 9, 10) | 3 | 1 | pending |
| 4 | README section on marking a project adopted (DoD 13) | 1 | 1 | pending |
| 5 | Install, re-verify machine, Configuration section passing (DoD 12) | 1 | 2,3,4 | pending |

Coverage: 1→t1 · 2,3,4,5,6,7→t1 · 8→t2 · 9,10→t3 · 11→t1+t5 · 12→t5 · 13→t4

### Masterprompt critique
`masterprompt-critic` (its first real run) returned 6 blocking, 9 serious, 6 minor findings on
the first draft. The blocking ones were all symptoms of one thing: the helper's contract was
described only through examples. The rewrite pins it in a single section. Two of its catches
were load-bearing — the fail-open rule silently contradicting "this repo unchanged", and DoD 6
scanning only `gentic/<slug>` while four `gentic(<slug>)` commit sites went unlisted, which
would have shipped half the mission undone.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Branches from `gentic/agent-automation-suite` (PR #1), which carries the hooks, installer and
  agents this run builds on. A PR for this run therefore stacks on PR #1.
