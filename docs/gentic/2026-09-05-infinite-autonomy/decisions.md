# Decisions: infinite-autonomy

The user delegated every decision ("decide on best judgment, flag transparently, don't block";
brain decision `all-open-decisions` = delegated, source user). No question was asked. Every
row below is the brief's recommended default, adopted and flagged; the final report lists them
again for reversal.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Iteration budget | Keep the 13-point ledger; exhaustion escalates instead of halting: the next failure goes straight to rung 5, a second exhaustion to rung 8, and a taken rung 8 resets the ledger for the re-framed cycle | Delete points entirely; keep the budget as a stop | Removes every self-imposed stop while keeping "same item, same rung, twice → climb", the property that makes the loop converge; lessons still carry points for evals and the gardener | default — unconfirmed |
| Rungs 5 and 8 when autonomous | Taken autonomously: amend the spec / re-interview from brain preferences and scouted defaults, every change flagged `default — unconfirmed`, then continue | Hand off (today's rule) | The literal request; `gentic-interview` already runs without `AskUserQuestion` | default — unconfirmed |
| `STOP` file and `/gentic stop` | Kept as the user's external kill switch — the one legitimate early end | Remove with the rest | User-initiated, free, and an infinitely autonomous run needs an off switch that is not Ctrl-C | default — unconfirmed |
| Session state store | A `sessions` table in the brain; `~/.claude/state`, the lock files and `prune_state` go away; a missing brain fails open | Keep JSON files for the valve only | One store, atomic increment under SQLite's locking (fixes note #17's race and note #16's orphaned locks) | default — unconfirmed |
| Smart brain additions | Three: `PRAGMA user_version` migrations with indexes on `(project, ts)`; a `prune` command with 89-day event retention run best-effort at session start; events tagged with the project's open run slug | Only the state move | Each fixes a documented weakness: unbounded events, "delete the file" on schema change, events unattributable to runs | default — unconfirmed |
| `post_tool_use.py` ledger | Records only what has a reader: `red`/`verification` events and the valve's decrement; `touched`, `code_changed`, `test_touched`, `evidence`, `reviewed` are dropped | Keep the ledger unused | Dead state is a "hooks notice" claim with nobody listening | default — unconfirmed |
| Live `~/.claude/settings.json` | This run removes the `Stop` entry after backing the file up as `settings.json.bak-2026-09-05`, and syncs `~/.claude/hooks` with `./install.sh` | Leave machine state to the user | The request is about this machine's behaviour; the edit is reversible and documented | default — unconfirmed |
| Concurrency valve | Kept; only its storage moves | Remove as another "condition" | Caps fan-out, never ends a run, proven by the standing-authorizations run | default — unconfirmed |
| Event retention period | 89 days (Fibonacci) | 55, 144, none | Long enough to cover a quarter of runs; the house rule picks the value | default — unconfirmed |
| One run, not two | Autonomy removal and brain-as-store stay in one run; brain work and irreversible machine steps come first in the task order | Split into two runs as the masterprompt critic recommended | The valve's counter must leave `~/.claude/state` before the directory can go, and the user asked for both in one request | default — unconfirmed |
| Fail-open valve | A brain that cannot be opened means an uncapped valve, silently | Fail closed (deny every spawn) | A blocked session is worse than an uncapped fan-out; the harness proves the normal path | default — unconfirmed |
| `~/.claude/state` deletion | Deleted without backup | Tarball first | It holds only per-turn ledgers and valve counters; another live session loses at most one valve count | default — unconfirmed |
