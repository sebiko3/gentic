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
| 1 | Back up settings.json; write hooks/README.md with the rollback command | 1 | — | done |
| 2 | `lib/common.py` + harness skeleton (`tests/run.sh`) with degradation cases | 3 | 1 | done |
| 3 | `user_prompt_submit.py` classifier + 12-prompt labelled fixture set | 5 | 2 | done |
| 4 | `post_tool_use.py` evidence ledger + touched-files tracking | 3 | 2 | done |
| 5 | `stop.py` verification gate + once-per-prompt escape hatch | 3 | 4 | done |
| 6 | `session_start.py` resume notice + state pruning | 2 | 2 | done |
| 7 | `pre_tool_use.py` destructive-git guard | 2 | 2 | done |
| 8 | Copy six gentic skills global + write `ROUTING.md` | 2 | — | pending |
| 9 | `commands/ship.md` one-command GitHub flow | 3 | 8 | pending |
| 10 | Wire `settings.json` hooks; enable `pr-review-toolkit` | 2 | 2–7 | pending |
| 11 | Full harness run incl. latency + no-git degradation | 3 | 10 | pending |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Deliverable target is the user's global config (`~/.claude/`), outside this repo. Run artifacts stay here in `docs/gentic/`.
- Critique pass run on masterprompt.md: resolved the gentic-checkpoint-commit vs no-unprompted-git contradiction (confined to `gentic/*` branches, flagged unconfirmed); added the once-per-prompt Stop escape hatch after the deadlock scan; converted "works for ALL projects" / "automatically" / "perfect" into measured DoD items and explicit non-goals.
- Plan drift: tasks 4 and 5 are one contract (ledger + gate are meaningless apart) and landed in a single commit. Their tests live together in `tests/test_gate.py`.
- Gate tests caught a real defect: the initial done-claim regex missed "Done — everything is passing"; broadened, and a NOT_A_CLAIM guard added so hedged statements ("not done yet", "want me to...") never block.
