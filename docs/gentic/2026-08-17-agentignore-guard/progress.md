# Run: agentignore-guard
Goal: A PreToolUse guard that reads `.agentignore` files and refuses reads/writes the project has declared off-limits, before the tool runs.
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
| 1 | `lib/agentignore.py`: parser + pattern matcher + cascade resolution | 5 | — | pending |
| 2 | Wire enforcement into `pre_tool_use.py` (file tools + Bash scan) | 3 | 1 | pending |
| 3 | Widen `settings.json` PreToolUse matcher | 1 | 2 | pending |
| 4 | Example `.agentignore` + README limitations section | 2 | 2 | pending |
| 5 | Harness: latency case + full green run | 2 | 3 | pending |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|

## Notes / handoff
- Critique pass: the two-readings scan caught that "Edit" needs *both* read and write permission (an edit reads first) — specified explicitly. The contradiction scan caught that fail-open conflicts with a strict security reading; resolved by demoting the feature to "accident-preventer" in Non-goals and requiring that wording in the README.
