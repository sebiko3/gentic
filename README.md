# gentic

A spec-first, resumable deep workflow for [Claude Code](https://claude.com/claude-code). One command turns a vague request into verified work: informed clarifying questions → a masterprompt that could brief a stranger → execution in small verified steps → iteration on an escalation ladder with a hard budget.

## Why

We probed a capable agent with a deliberately ambiguous request — *"Add CSV export to the admin dashboard. Should work for the users table and be fast."* — and asked it to narrate its honest default behavior. It reported that it would:

- ask **zero** questions before writing code, silently deciding on its own authority which PII columns to export;
- write **no plan to disk** — "the plan exists in my head" — so a context loss loses everything;
- accept "fast" **by construction, not measurement** — shipping unverified performance claims.

None of that is a capability problem. It is a workflow problem: missing context, missing persistence, missing verification. gentic supplies the workflow.

## The workflow

```mermaid
flowchart LR
    A[Scout\nbrief.md] --> B[Interview\ndecisions.md]
    B --> C[Masterprompt\nmasterprompt.md]
    C --> D[Execute\ntask table]
    D --> E[Iterate\nverify + ladder]
    E -->|rung 5| C
    E -->|rung 8| B
    E -->|all DoD green| F([Done, with evidence])
```

| Phase | Question it answers | Artifact |
|-------|--------------------|----------|
| **Scout** | What does reality already decide? | `brief.md` — facts, patterns, open decisions each with a recommended default |
| **Interview** | What must the user decide? | `decisions.md` — only high-leverage × high-uncertainty questions get asked (≤4 per round); data/security calls auto-rank first |
| **Masterprompt** | Could a stranger deliver this? | `masterprompt.md` — mission, decisions, non-goals, and a Definition of Done where every item names its exact check. Then a five-scan critique pass. |
| **Execute** | What's the smallest verified step? | task table in `progress.md` — fibonacci-sized tasks, dependency-ordered riskiest-first, test-first, one commit per task |
| **Iterate** | Patch, rework, or re-open the spec? | iteration log in `progress.md` — evidence for every DoD item; failures climb a ladder instead of looping |

Every artifact lives in `docs/gentic/<date>-<slug>/` and is committed, so **any session — including one that lost its context — resumes any run** by reading the run directory.

## The fibonacci mechanics

- **Task sizes** are 1/2/3/5/8 points; a task above 8 must be split (if it can't be, the spec is under-specified).
- **Escalation rungs** cost 1 (micro-fix), 2 (rework component), 3 (redesign within spec), 5 (re-open masterprompt), 8 (re-open interview). Same item fails twice at a rung → the next rung is mandatory. No third tries.
- **The budget is 13 points per run.** When it's gone, the run stops with an honest handoff instead of thrashing.

The costs grow super-linearly because each rung discards more prior work — and the budget forces a real decision between many small fixes and one deep rethink.

## Install

Copy two things into any repository:

```bash
cp -R .claude/skills/gentic* /path/to/your/repo/.claude/skills/
```

Then add the **Routing** section from this repo's [CLAUDE.md](CLAUDE.md) to your repo's `CLAUDE.md`. That's the whole install — gentic is markdown, no dependencies.

Works standalone; if the [superpowers](https://github.com/obra/superpowers) plugin is installed, gentic composes with it (TDD, systematic debugging, verification gates) at marked points.

## Use

```
/gentic add rate limiting to the public API
```

- New non-trivial task → gentic starts a run and interviews you (up to 4 multiple-choice questions per round, recommendation listed first).
- You're away? Runs don't block: gentic adopts the scouted default for each question, flags it `unconfirmed`, and lists every assumption in the final report.
- `resume` / `continue` → gentic finds the newest unfinished run and re-enters at the first unchecked phase.
- `/gentic status` → every run, its phase, tasks done, budget remaining.

## Example run

This repository built itself with its own workflow — see [docs/gentic/2026-08-11-bootstrap-gentic/](docs/gentic/2026-08-11-bootstrap-gentic/) for a complete run: the brief, the decisions (with alternatives considered), the masterprompt with its Definition of Done, the brief including the baseline probe quoted above, and an iteration log of real fixes from the run's own review gates.

## Design notes

- **Why five phases instead of "questions → masterprompt → iterate"?** The original three-phase shape lacks grounding (questions asked from ignorance are generic) and an anchor for iteration (without a checkable Definition of Done, iteration spins). Scout makes questions sharp; the DoD makes iteration converge.
- **Why not multi-agent-first?** Subagent fan-out is an execution optimization, not a workflow. gentic stays single-threaded by default (cheap, debuggable, no opt-in friction); subagents are optional optimizations — independent 3+ point tasks during Execute, a fresh-eyes critic on the masterprompt — when available.
- **Why files instead of memory?** Context windows end; `docs/gentic/` doesn't. The masterprompt's quality bar — "a stranger could deliver from this file alone" — is also exactly what a post-compaction session needs.

## License

[MIT](LICENSE)
