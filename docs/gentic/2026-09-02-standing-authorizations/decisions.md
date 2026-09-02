# Decisions: standing-authorizations

Under the user's blanket delegation ("go ahead with R5").

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Where grants live | The project's root `CLAUDE.md`, section `## gentic authorizations`. | `.gentic.toml`; `~/.claude` | Epic decision: reviewable in git, next to the adoption marker; a machine-wide grant would reach repos never meant. | user — delegated |
| Vocabulary | `push`, `open-pr`, `merge-on-green`, `deploy-preview`, `use-workflow-tool`, `spawn-teams`; only the first two have a consumer in this run. | Free-form | A fixed list makes an unknown word a `no`, never a surprise grant. | user — delegated |
| Fail direction | Closed: no root, no file, no section, unknown word ⇒ `no` / exit 1. | Fail open like naming | Naming must never stop a run; consent must never be assumed. | user — delegated |
| First consumer | `gentic-iterate`'s final report: when `authorized push` and `authorized open-pr` both say `yes`, follow `commands/ship.md` end to end and put the PR URL in the report. | Wait for the release lane | It is the smallest step that makes "one prompt → PR" true, and `/ship`'s own steps (verify, review, push, PR body with unconfirmed defaults) already exist. | user — delegated |
| `/ship` wording | "the user typing `/ship` is the authorisation" gains "— or a project whose `## gentic authorizations` grants `push` and `open-pr`". `Never merge` stays. | Leave `/ship` as is | The command is the mechanism the run reuses; its text must admit the second caller. | user — delegated |
| Concurrency valve | `pre_tool_use.py` denies a `Task`/`Agent` spawn while five are in flight (count up at spawn, down at return); a cap, not a once-only valve; foreground only. | No valve; a once-only valve | Runaway fan-out is the mesh run's risk; 5 is Fibonacci; a background agent returns at once, so the count is honest about what it sees. | user — delegated |
| STOP flag | `docs/gentic/<run>/STOP` (any content) written by `/gentic stop <slug> [reason]`; `gentic-execute` checks before each task, `gentic-iterate` before each rung; status lists it. | A hook that blocks; a brain flag | A file the user can create by hand from any shell; no hook, no new hard block. | user — delegated |
| This repo's grants | Section present, no grants. | Grant push + open-pr here | `/ship` stays the user's call in this repo; the section documents the shape. | user — delegated |
| Regression gate | One live run of `csv-export-probe`, with arm only, after install; must stay 4/4. | Full suite; none | The wording change touches `gentic-iterate`, which the probe exercises; the agent cases are untouched. | user — delegated |
| Budget currency (epic item 15) | Deferred to `gentic-epic`. | Define constants now | No consumer exists yet. | user — delegated |
