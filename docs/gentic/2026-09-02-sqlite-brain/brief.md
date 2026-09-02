# Brief: sqlite-brain

## Mission (as understood)
Give gentic a persistent brain it can use as it likes: one SQLite database, machine-wide, that
the hooks write into automatically (RED and verification events, gate blocks, nudges) and that
the phase skills read and write deliberately (notes and recall, learned preferences for the
Interview, lessons from Iterate, run lifecycle, skill-version stamps). Free-form notes with
full-text search and an unrestricted `sql` command are what make it *the agent's own* memory
rather than another fixed ledger.

## Facts
- The hooks are stdlib-only, no subprocess, no network, 150 ms median on hot paths
  (`lib/common.py:1-9`, `tests/run.sh` latency sections). `sqlite3` is stdlib: Python 3.13.5,
  SQLite 3.53.4, FTS5 available, JSON1 available (verified in this session).
- Session state lives in `~/.claude/state/<session>.json` and is pruned after 7 days
  (`lib/common.py` `prune_state`). Nothing else persists across sessions.
- `post_tool_use.py:95-103` already classifies a verification command's exit code into
  `evidence` (0/unknown) or `red` (non-zero) — the brain's `red`/`verification` events hang off
  that branch. `stop.py` `verification_gate` and `advisory_nudges` are the block/nudge sites.
- `session_start.py` emits one `systemMessage` about unfinished runs and is silent otherwise —
  the brain summary follows that shape.
- `install.sh` enumerates files with `git ls-files -- .claude`, so a new `lib/brain.py`, a new
  test and a new skill are installed with no installer change; `--check` reports drift.
- `tests/test_structure.py:51` `GENTIC_SKILL` enumerates the phase skills for
  reference-existence checks; `tests/run.sh:147` asserts exactly 7 gentic skills; `run.sh:15`
  lists the unit suites by name. All three must change for an eighth skill.
- `test_structure.py:350` requires every file shipped inside a skill directory to be mentioned
  by its `SKILL.md`.
- Precedent for a CLI helper next to the hooks: `lib/project_conventions.py` (argparse, never
  fails a run, subprocess allowed because it is not on a hot path).
- `zcontext` (global skill) is a separate SQLite context store with its own CLI; the brief's
  item 5 proposed reusing it. The user chose a brain of gentic's own instead.

## Patterns to follow
- Deterministic helper with a CLI, referenced by skills instead of prose rules (`project_conventions.py`).
- Save-before-block, never-raise hooks: brain writes must be wrapped so a missing or locked
  database costs nothing (`common.safe_main`, `save_state` swallowing failures).
- Fibonacci constants: busy timeout 89 ms, recall limit 8, preference threshold 2.
- Contract tests for docs and skills (`test_structure.py`, `test_token_efficiency.py::test_docs_document_the_guards`).
- One task, one commit; RED text in the task table.

## Constraints discovered
- Hot-path writes must be bounded: open with `timeout=0.089`, one INSERT, close; on any
  exception, return silently. No schema migration on the hot path beyond `CREATE IF NOT EXISTS`.
- The brain is machine-wide, so every row carries a `project` key. Project = basename of the git
  root (a repo moved on disk keeps its memory; two repos with the same basename share it —
  accepted, documented).
- `GENTIC_BRAIN` env var overrides the path (tests, and users who want it elsewhere).
- The verification gate's behaviour is unchanged: `tests/test_gate.py` stays at 19 passing tests.

## Open decisions (all resolved by delegation — see decisions.md)
1. Location — `~/.claude/gentic/brain.sqlite`, env override. Default: as stated.
2. Free SQL — allow arbitrary statements. Default: yes; it is the agent's own store.
3. Preference rule — learned when ≥2 user-sourced decisions on a topic agree and the most recent
   user-sourced one is among them; default-sourced decisions never teach. Default: as stated.
4. Project key — basename of the git root. Default: as stated.
5. Eighth skill vs. folding the brain into `gentic/SKILL.md` — a dedicated `gentic-brain` skill,
   because "use as it likes" needs a place that explains what the brain can do, outside any phase.
