# Run: agentignore-guard
Goal: A PreToolUse guard that reads `.agentignore` files and refuses reads/writes the project has declared off-limits, before the tool runs.
Iteration budget: 10 remaining (3 spent) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview
- [x] 3 Masterprompt
- [x] 4 Execute
- [x] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Status (pending/in progress/done) |
|---|------|------|------------|--------|
| 1 | `lib/agentignore.py`: parser + pattern matcher + cascade resolution | 5 | — | done |
| 2 | Wire enforcement into `pre_tool_use.py` (file tools + Bash scan) | 3 | 1 | done |
| 3 | Widen `settings.json` PreToolUse matcher | 1 | 2 | done |
| 4 | Example `.agentignore` + README limitations section | 2 | 2 | done |
| 5 | Harness: latency case + full green run | 2 | 3 | done |

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | all 17 items | — | 0 | Passed on first verification: 34 agentignore tests + full harness green; 12/12 live decision cases correct. |
| 2 | no-false-positives (adjacent defect) | 1 | 1 | Found in live use, not by the suite: the pre-existing destructive-git guard matched dangerous commands quoted *inside* another command, refusing legitimate work (`echo`, `grep`, `printf`, heredocs). Fixed by blanking quoted sections before matching (`unquoted()`); 4 regression tests added. |

| 3 | malformed/oversized input must fail open silently | 2 | 2 | Reported from live use in `~/code/docEyes`: `[Errno 63] File name too long`. Root cause at `agentignore.py:150` — `target.is_dir()` sat outside the try block; `Path.resolve()` is lenient on macOS but `is_dir()` stats, and a path over PATH_MAX (1024) raises. Trigger was a Bash command carrying a pasted JSX blob, which `shlex.split` yielded as one giant token. **Second, unlogged consequence:** the exception aborted the whole token scan, so a protected path later in the same command went unchecked — the guard silently stopped guarding. Fixed in two layers: (1) every filesystem call in `rules_for` is now inside the guard; (2) `plausible_path()` rejects tokens with newlines, over PATH_MAX, or with a component over NAME_MAX before any stat, and `check_bash` no longer aborts on one bad token. 13 regression tests added (`OversizedTokens`, `OversizedEnforcement`). |

## Notes / handoff
- Critique pass: the two-readings scan caught that "Edit" needs *both* read and write permission (an edit reads first) — specified explicitly. The contradiction scan caught that fail-open conflicts with a strict security reading; resolved by demoting the feature to "accident-preventer" in Non-goals and requiring that wording in the README.

## Final report
`.agentignore` enforcement shipped in `~/.claude/hooks/`: `lib/agentignore.py` (parser, gitignore-subset
matcher, cascade resolution) enforced from `pre_tool_use.py` across Read/Edit/Write/NotebookEdit and a
heuristic Bash path scan. 91 tests total across the layer; PreToolUse median 23.5 ms.

**Unconfirmed defaults** — see `decisions.md`: cascade discovery, `!` negation, no off-switch,
fail-open on a malformed file, accident-preventer framing, and extending the existing hook rather
than adding a second one.

**Not done (non-goals):** Grep/Glob unguarded, no result filtering, no `.gitignore`/`.cursorignore`
interop, no global `~/.agentignore`, no per-session override.
