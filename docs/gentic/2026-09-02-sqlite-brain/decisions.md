# Decisions: sqlite-brain

Interview held under the user's blanket delegation ("I fully trust your decisions here"); the
brain itself was the user's own instruction.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| That gentic gets an SQLite brain | **Yes** — one database, used freely. | JSONL ledger; `zcontext`; sheldon's MCP brain | User's instruction. | user |
| Location | `~/.claude/gentic/brain.sqlite`, overridable by `GENTIC_BRAIN`. | Per-repo `.gentic/brain.sqlite`; `~/.claude/state/` | Lessons and preferences are cross-project; state/ is pruned. Env override keeps tests hermetic. | user — delegated |
| Engine | stdlib `sqlite3`, WAL mode, FTS5 for notes when available with a `LIKE` fallback. | An embedding index; a server | Hooks are stdlib-only; FTS5 is present here and the fallback keeps other machines working. | user — delegated |
| Free SQL | `brain sql "<statement>"` runs any statement and prints rows as JSON lines. | SELECT-only | "Use as it likes" means the agent may add its own tables. The database is its own; nothing else reads it. | user — delegated |
| What the hooks write | `post_tool_use`: `red` and `verification` events; `stop`: `gate_block` and `nudge` events; `session_start`: reads only. All best-effort, 89 ms busy timeout, never raise. | Nothing automatic (skills only); everything (every tool call) | The RED/green record is the one fact only hooks can see; logging every tool call would bloat the brain and the hot path. | user — delegated |
| Preference rule | Learned when at least 2 user-sourced decisions on a topic agree and the latest user-sourced decision is one of them. Defaults never teach. | Learned from 1; majority of all sources | One answer is an accident; two is a preference. Defaults teaching would let the agent confirm its own guesses. | user — delegated |
| Project key | Basename of the git root. | Absolute path; remote URL | Survives moving the repo; readable in reports. Collision between same-named repos accepted and documented. | user — delegated |
| Skill shape | New `gentic-brain` skill (eighth), plus one-line hooks in `gentic`, `gentic-scout`, `gentic-interview`, `gentic-execute`, `gentic-iterate`. | Fold into `gentic/SKILL.md` | The brain is used across phases and outside runs; it needs its own trigger description. | user — delegated |
| Bus for orchestrators | Not now: the `events` table is shaped so the mesh run can use it, but no consumer is built here. | Build `bus.jsonl` now | Non-goal; concurrency is R8. | user — delegated |
