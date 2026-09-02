# Decisions: self-improving-gentic (epic)

The user delegated every open decision on 2026-09-02 ("I fully trust your decisions here") and
added one of their own. Delegated defaults are recorded as `user — delegated`: chosen by the
agent under blanket approval, still listed in every final report.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| A persistent brain | **An SQLite brain gentic may use as it likes** — one machine-wide database, stdlib `sqlite3`, with structured tables (lessons, decisions, runs, events, stamps) *and* a free-form notes table with full-text recall, plus unrestricted SQL for the agent. | JSONL ledger + `zcontext` store (the brief's items 3 and 5); a custom MCP server (sheldon's approach) | The user's own call. It also collapses four proposed mechanisms (lesson ledger, preference memory, version stamping, orchestrator bus) into tables of one store, and `sqlite3` needs no dependency, which keeps the hooks' stdlib rule. | user |
| Which run starts first | **`sqlite-brain`** (new R1), then `gentic-evals`. | Evals first (the brief's recommendation) | The brain is the substrate the ledger, preference memory, epic DAG and mesh bus all write to, and the user named it. Eval scores per skill version also belong in it, so evals come second and store into it. | user — delegated |
| Orchestration engine | First-party `Workflow` scripts inside a run and agent teams between orchestrators, behind capability detection with the prose contract as fallback. | Prose only; a custom MCP server | Uses platform machinery, keeps the portability claim, no server to maintain. | user — delegated |
| Where standing authorizations live | A `## gentic authorizations` section in the project's `CLAUDE.md`; none granted by default. | `.gentic.toml`; machine-wide | Reviewable in git, next to the adoption marker; a machine-wide grant would authorise pushes in unrelated repos. | user — delegated |
| UI testing executable | Playwright as the DoD contract; browser tools for scouting and failure reproduction. | Browser tools only | Contracts must be reproducible in CI. | user — delegated |
| CI generation | On request, per project, under the authorizations above. | Never; always | CI is another project's public surface. | user — delegated |
| Self-improvement cadence | On-demand `/gentic evolve` first; scheduled after two clean on-demand cycles. | Scheduled from day one; continuous | An unattended loop that rewrites its own skills must first prove the eval gate catches regressions. | user — delegated |
| Lesson storage | In the brain (machine-wide) plus a committed `retro.md` per run. | Per-repo only | Workflow lessons are cross-project; product lessons travel with the code. | user — delegated |
| sheldon's fate | Absorb its concepts and archive it with an ADR, in the `gardener` run. | Keep both; revive it | Its brain, contracts and epic-planner map onto brain tables, DoD contracts and `gentic-epic`. | user — delegated |
