# Run: agent-automation-suite
Goal: New subagents plus an improved automation workflow for code review, orchestration, and spec-driven development, across all projects.
Iteration budget: 11 remaining (2 spent) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [x] 4 Execute
- [x] 5 Iterate

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


## Final report

**Mission.** The repo is now the tracked source of truth for the whole Claude Code setup, and
four subagents close the three gaps scouting found: code review had no first-party capability
and its `/ship` path was broken, subagent fan-out had no dispatch contract, and the spec and
done-ness phases had no adversarial scrutiny.

**Definition of Done — 19 of 20 proven, 1 partially unverifiable.** All evidence re-run fresh
at the final gate.

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | four agents, valid frontmatter | PROVEN | `test_structure.py` 19 tests OK |
| 2 | first-party references resolve | PROVEN | validator OK; `grep -rn pr-review-toolkit` → 0 unqualified lines (after rung 1) |
| 3 | no enabled-but-unloadable plugin | PROVEN | `LiveMachineConfig` OK; entry removed |
| 4 | automation layer tracked, no artefacts | PROVEN | hooks 21 / commands 2 / agents 4 / skills 7 tracked; 0 `__pycache__` or `.pyc`; tree clean |
| 5 | `install.sh` idempotent | PROVEN | second run → `0 files changed` |
| 6 | `--check` detects drift, passes when synced | PROVEN | synced → exit 0; seeded drift → exit 1, `differs: agents/dod-auditor.md` |
| 7 | installer destroys nothing it does not own | PROVEN | `zcontext`, `cua-driver`, `use-railway`, `learned`, sessions, plugins, state all survive; 0 destructive commands in source |
| 8 | harness green | PROVEN | `run.sh` exit 0, 0 FAIL lines, 156 tests across 8 suites |
| 9 | nudge fires exactly when it should | PROVEN | `test_review_nudge.py` 14 tests OK |
| 10 | nudge never blocks | PROVEN | same suite: exit 0, no block decision on every nudge path |
| 11 | verification gate behaviourally unchanged | PROVEN | `test_gate.py` 19 tests OK — identical to the task-1 baseline |
| 12 | a review invocation is really recorded | PROVEN | same suite: `Task` and `Agent` spellings both set `reviewed` |
| 13 | `/review` exists, resolvable | PROVEN | frontmatter `description` present; covered by item 2's check |
| 14 | `/ship` §4 first-party | PROVEN | `code-reviewer`/`dod-auditor` in §4; external names only on an "if installed" line |
| 15 | real dispatch contract | PROVEN | `task-executor` named; all four required headings present exactly once |
| 16 | phases name their scrutinising agent | PROVEN | `masterprompt-critic` in gentic-masterprompt; `dod-auditor` in gentic-iterate |
| 17 | `code-reviewer` finds planted defects, resists decoy | **PARTIAL** | see below |
| 18 | nudge costs almost nothing | PROVEN | median 23.6 ms vs 22.2 ms baseline — delta +1.4 ms (limits: <150 ms, delta <50 ms) |
| 19 | rollback documented, backup exists | PROVEN | `settings.json.bak-2026-08-19` present; restore command in `hooks/README.md:91` |
| 20 | README documents agents and installer | PROVEN | 5 agent mentions, `install.sh --check` documented, superseded `cp -R` instruction gone |

**Item 17, stated precisely.** Invoking the registered `code-reviewer` agent type failed:
`Agent type 'code-reviewer' not found`. Agent definitions are resolved when a session starts,
so an agent created during a session is not invocable in that same session. That is
environmental, not a defect in the work — but the check as written did not run, so the item is
**UNVERIFIABLE**, not proven, and was not rounded up.

The substance was tested separately and clearly labelled as an approximation: the agent's
instructions were given verbatim to a general-purpose subagent and run on the fixture. It
reported both planted defects — SQL f-string interpolation at confidence 96, `except
Exception: pass` at 93 — and did not report the decoy, discarding 3 candidates below the
threshold. It also treated the fixture's own docstrings as data rather than instructions. That
matches `seeded_defect.expected.md` exactly, but it exercised the prompt, not the registration.

To finish item 17, in a **new** session: invoke `code-reviewer` on
`.claude/hooks/tests/fixtures/seeded_defect.py` and compare against
`seeded_defect.expected.md`.

**Iteration budget: 11 of 13 remaining, 2 spent.**

- Rung 1 (1 pt) — DoD 2's grep swept `test_structure.py`, which must contain the literal it
  searches for. Root cause was self-reference in the check's file set. Fixed by hoisting the
  literal to an `OPTIONAL_PLUGIN` constant; the DoD item itself was not touched.
- Rung 1 (1 pt) — a regression this run caused: task 1 imported `ROUTING.md` but not the
  diverged global `gentic/SKILL.md` that pointed to it, and `install.sh` then propagated the
  stale repo copy outward, orphaning the file. Blast radius was proven to be exactly one
  paragraph by accounting for all 20 files the first install touched. Restored, live setup
  re-synced, and a `NoOrphanedSkillFiles` guard added so a shipped-but-unreferenced file fails
  the harness.

**Correction to the Scout brief** (appended there, dated): the `pr-review-toolkit` finding was
right in its conclusion and wrong in its mechanism. The plugin *is* in
`installed_plugins.json`; its recorded `installPath` does not exist on disk. The validator was
strengthened accordingly — checking the registry key alone would have called this machine
healthy.

**Unconfirmed defaults awaiting your confirmation.** Four decisions were yours; these four were
not:

1. Orchestration delivered as a written dispatch contract rather than a `Workflow` script.
2. Verification delivered as a structural validator plus the seeded-defect fixture.
3. `install.sh` also syncs skills and `ROUTING.md`, with drift checked by `--check`.
4. `lib/common.py` joined the sanctioned edit list (added during Execute) — the once-per-session
   nudge is unimplementable without session-scoped state, since `begin_turn` clears the ledger
   every prompt.

**Deliberately not done** (non-goals held): no plugin installed; no `Workflow` orchestrator,
swarm, or parallel-execution engine; no fifth agent; no change to gentic's five phases,
Fibonacci sizing, or budget; no second hard block; no CI; no symlink mode or `uninstall.sh`; no
Windows support; no push, PR, or merge to `main`; the other global skills (`zcontext`,
`cua-driver`, `use-railway`, `learned`) were left where they are.
