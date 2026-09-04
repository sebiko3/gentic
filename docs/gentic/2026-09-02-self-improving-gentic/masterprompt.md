# Masterprompt: self-improving-gentic (epic index)

## Mission
gentic becomes a self-improving, multi-orchestrator delivery system. This run is the epic's
index: it owns the roadmap and closes when every child run below is complete. The work itself
happens in the child runs, each an ordinary gentic run with its own artifacts and budget.

## Context
`brief.md` in this directory: eighteen mechanisms, cited gaps, the roadmap, the calendar trace.

## Decisions
`decisions.md` in this directory. The user chose the SQLite brain; everything else is delegated.

## Constraints
- Every child run obeys ROUTING.md, `~/.claude/CLAUDE.md`, and the project `CLAUDE.md` in full.
- Child runs are sequenced by the roadmap; a later run may start only when the one it depends on
  has all five phases ticked.

## Non-goals
- This index does not build anything itself; no code lands under this run's commits.
- No child run is skipped or merged into another to save ceremony.

## Definition of Done
Each item: the named child run's `progress.md` has all five phases ticked and its final report
written. verify: `grep -c '^- \[x\]' docs/gentic/<date>-<slug>/progress.md` prints 5.
contract: n/a for the index — the observable behaviour is specified and tested inside each
child run's own masterprompt; the index has nothing executable of its own.

- [x] R1 `sqlite-brain` (brief items 3, 4, 5 substrate; user's decision) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-sqlite-brain/progress.md` → 5
- [x] R2 `gentic-evals` (items 1, 2, verification regex fix from 11) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-gentic-evals/progress.md` → 5
- [x] R3 `eval-fidelity` (re-scoped from adjective-compiler-and-retro by R2's lessons; items 7 and `retro.md` move to a later run) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-eval-fidelity/progress.md` → 5
- [x] R4 `skill-tuning-by-evals` (inserted; the suite's own findings applied and proven) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-skill-tuning-by-evals/progress.md` → 5
- [x] R5 `standing-authorizations` (items 14 and 16; 15 deferred to `gentic-epic`) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-standing-authorizations/progress.md` → 5
- [x] R6 `ui-contracts` (items 11, 13, `ui-tester` agent) — `grep -c '^- \[x\]' docs/gentic/2026-09-02-ui-contracts/progress.md` → 5; U8 closed unproven by the user
- [ ] R6 `release-lane` (item 12)
- [ ] R7 `gentic-epic` (item 8)
- [ ] R8 `orchestrator-mesh` (items 9, 10, 17)
- [ ] R9 `gardener` (items 6, 18)

## Risks & early signals
- A child run exhausting its budget stops the epic at that node; the handoff names the rung.
- Platform features (Workflow, teams, cron) may change between runs; each child re-scouts them.

## Iteration budget
13 (this index; child runs carry their own)

## Critique
Self-critique only (five scans, read cold): the index has one reading; DoD items are
independently checkable by the grep; the non-goal stops the index from absorbing work. The
`masterprompt-critic` agent was not dispatched for this ten-line index — it is spent on the
child runs' specs, where misreading costs work.
