# Run: universal-claude-setup
Goal: A universal Claude Code setup (skills + hooks + agents) that works across all projects and automates intent capture → prompt transformation → spec → execution → verification → GitHub management.
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

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Deliverable target is the user's global config (`~/.claude/`), outside this repo. Run artifacts stay here in `docs/gentic/`.
- Critique pass run on masterprompt.md: resolved the gentic-checkpoint-commit vs no-unprompted-git contradiction (confined to `gentic/*` branches, flagged unconfirmed); added the once-per-prompt Stop escape hatch after the deadlock scan; converted "works for ALL projects" / "automatically" / "perfect" into measured DoD items and explicit non-goals.
