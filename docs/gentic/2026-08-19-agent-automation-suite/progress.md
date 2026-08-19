# Run: agent-automation-suite
Goal: New subagents plus an improved automation workflow for code review, orchestration, and spec-driven development, across all projects.
Iteration budget: 11 remaining (2 spent) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [x] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Status (pending/in progress/done) |
|---|------|------|------------|--------|
| 1 | Record baselines; import hooks/commands/ROUTING.md into repo; `.gitignore` | 3 | — | done |
| 2 | `install.sh` with `--check` and ownership safety (test-first) | 5 | 1 | done |
| 3 | `tests/test_structure.py`: agent frontmatter, resolvable refs, plugin cross-check | 5 | 1 | done |
| 4 | The four agent files under `.claude/agents/` | 5 | 3 | done |
| 5 | Review nudge: `post_tool_use` review signal + `stop.py` advisory (test-first) | 5 | 1 | done |
| 6 | `settings.json`: drop phantom entry, widen matcher, backup + rollback doc | 2 | 5 | done |
| 7 | `/review` command; rewrite `/ship` §4 to first-party agents | 2 | 4 | done |
| 8 | gentic skills: dispatch contract, `masterprompt-critic`, `dod-auditor` | 3 | 4 | done |
| 9 | README: agents section, installer usage, remove superseded install text | 2 | 2,4 | done |
| 10 | Seeded-defect fixture for `code-reviewer` | 1 | 4 | done |

Coverage: every DoD item is claimed by at least one task —
1,2→t3,t4 · 3→t3,t6 · 4→t1 · 5,6,7→t2 · 8→t1(all tasks re-run it) · 9,10,12→t5 ·
11,18→t1 baseline + final measure at Iterate · 13,14→t7 · 15,16→t8 · 17→t10 · 19→t6 · 20→t9

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | DoD 2 — `grep -rn pr-review-toolkit` returned 5 unqualified lines, all inside `test_structure.py` itself. Root cause: the check is defined over a file set that includes the checker, which must contain the literal it searches for. Fixed by hoisting it to an `OPTIONAL_PLUGIN` constant and qualifying the remaining prose. DoD item untouched. | 1 | 1 | fixed — grep now returns 4 lines, all qualified |
| 2 | (no DoD item covered this) Regression caused by this run: task 1 imported `ROUTING.md` into the repo but not the global `gentic/SKILL.md`, which had diverged and carried the "Read ROUTING.md first" instruction. `install.sh` then propagated the stale repo copy outward, orphaning the file. Blast radius confirmed as exactly one paragraph by accounting for all 20 files the first install touched. Restored, plus a `NoOrphanedSkillFiles` guard. | 1 | 1 | fixed — pointer restored, live setup re-synced |

## Notes / handoff

### Recorded baselines (task 1, pre-change)
- `test_gate.py`: **19 tests**, OK — DoD 11 requires this count unchanged.
- `stop.py` no-op payload, median of 20: **22.2 ms** (min 20.9 / max 24.7) — DoD 18 baseline.
- `bash .claude/hooks/tests/run.sh` from the new repo location: exit 0, no FAIL lines.
- Base branch: `gentic/universal-claude-setup` (carries the hooks + global skills work that `main` lacks). New run branch `gentic/agent-automation-suite` branches from it.
