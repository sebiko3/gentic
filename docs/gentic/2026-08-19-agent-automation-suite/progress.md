# Run: agent-automation-suite
Goal: New subagents plus an improved automation workflow for code review, orchestration, and spec-driven development, across all projects.
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
| 1 | Record baselines; import hooks/commands/ROUTING.md into repo; `.gitignore` | 3 | — | done |
| 2 | `install.sh` with `--check` and ownership safety (test-first) | 5 | 1 | done |
| 3 | `tests/test_structure.py`: agent frontmatter, resolvable refs, plugin cross-check | 5 | 1 | done (RED: 4 genuine failures awaiting t4,t6,t7) |
| 4 | The four agent files under `.claude/agents/` | 5 | 3 | done |
| 5 | Review nudge: `post_tool_use` review signal + `stop.py` advisory (test-first) | 5 | 1 | done |
| 6 | `settings.json`: drop phantom entry, widen matcher, backup + rollback doc | 2 | 5 | pending |
| 7 | `/review` command; rewrite `/ship` §4 to first-party agents | 2 | 4 | pending |
| 8 | gentic skills: dispatch contract, `masterprompt-critic`, `dod-auditor` | 3 | 4 | pending |
| 9 | README: agents section, installer usage, remove superseded install text | 2 | 2,4 | pending |
| 10 | Seeded-defect fixture for `code-reviewer` | 1 | 4 | pending |

Coverage: every DoD item is claimed by at least one task —
1,2→t3,t4 · 3→t3,t6 · 4→t1 · 5,6,7→t2 · 8→t1(all tasks re-run it) · 9,10,12→t5 ·
11,18→t1 baseline + final measure at Iterate · 13,14→t7 · 15,16→t8 · 17→t10 · 19→t6 · 20→t9

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff

### Recorded baselines (task 1, pre-change)
- `test_gate.py`: **19 tests**, OK — DoD 11 requires this count unchanged.
- `stop.py` no-op payload, median of 20: **22.2 ms** (min 20.9 / max 24.7) — DoD 18 baseline.
- `bash .claude/hooks/tests/run.sh` from the new repo location: exit 0, no FAIL lines.
- Base branch: `gentic/universal-claude-setup` (carries the hooks + global skills work that `main` lacks). New run branch `gentic/agent-automation-suite` branches from it.
