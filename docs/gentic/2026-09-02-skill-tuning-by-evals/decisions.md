# Decisions: skill-tuning-by-evals

Under the user's blanket delegation ("please continue").

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Where the autonomous "continue" rule lives | **Both** `gentic-interview` (the phase that stopped) and `gentic/SKILL.md` (a new "Autonomous runs" section binding every phase gate). | Interview only | The transcript shows the stop happening *after* the Interview finished its work — at the gate — so the orchestrator needs the rule as much as the phase. | user — delegated |
| What "autonomous" means | **`AskUserQuestion` unavailable ⇒ autonomous, whatever the session looks like.** | Keep the three-way description | The R2/R3 transcripts show the model judging a `-p` session "clearly interactive"; the tool's absence is the one signal that cannot be misread. | user — delegated |
| Executor wording | One sentence in Output: the block is the entire final message, even for `blocked` and `assignment unclear`; questions go in `blocker:`. | Rewrite the agent | Smallest change at the point of misreading. | user — delegated |
| `pii-surfaced` | Symmetric pattern (keyword before or after the PII term). | Keep as is | A grader that scores correct behaviour 0 is a defect; the asserted claim does not change. | user — delegated |
| Budget exhaustion | Any result `subtype` starting `error_max_` is exhaustion, graded on files, tools and last text. | Only `error_max_turns` | The dollar cap is now reachable in 55 turns; treating it as an error would hide files again. | user — delegated |
| Leak channel | Non-goal; recorded. | Temp `HOME` / `CLAUDE_CONFIG_DIR` | Both lose the login (probed, 0 USD). | user — delegated |
| Proof | One live suite after install sync; compared with `20260902-170309`; a `with` case still below 1.0 is a lesson. | Offline only | Wording changes are only proven by the suite that found them. | user — delegated |
