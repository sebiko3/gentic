# Masterprompt: sqlite-brain

## Mission
After this run, gentic has a persistent SQLite brain. The hooks write RED/verification events,
gate blocks and nudges into it without being asked; the phase skills note, recall, decide, learn
preferences, record lessons, stamp skill versions and open/close runs through a CLI; and the
agent may run any SQL against it. A missing, locked or unwritable brain is invisible to a
session: no block, no message, no delay beyond the bounds below.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- **Invocation.** `brain …` in this document abbreviates
  `python3 "$HOME/.claude/hooks/lib/brain.py" …` (installed) or
  `python3 .claude/hooks/lib/brain.py …` (in this repo). **No PATH entry, alias, shim or
  symlink is created.** Skills and docs write the literal `python3 "$HOME/.claude/hooks/lib/brain.py"`
  form, matching how `project_conventions.py` is invoked (`README.md`, `gentic-execute/SKILL.md`).
- **Database path.** `$GENTIC_BRAIN` when set, else `Path.home() / ".claude" / "gentic" / "brain.sqlite"`.
  In `lib/brain.py` that default must be built with `Path.home()` on one physical line, and no
  docstring or comment may quote a `.claude` path inside double quotes — `run.sh` lines 87-96
  grep every hook for `"…\.claude…"` and fail unless `Path.home()` is on the same line.
- **Test isolation.** `run.sh` exports `GENTIC_BRAIN` to a fresh `mktemp` path before its first
  section, so the degradation and latency runs never touch the user's brain. Every test in
  `tests/test_brain.py` sets `GENTIC_BRAIN` (and `CLAUDE_HOOK_STATE_DIR`) in its own temp dir.
  D6's tests run serially against a private brain.
- Hooks: `.claude/hooks/*.py`, shared code in `.claude/hooks/lib/`, stdlib only, 150 ms median
  budget measured by `.claude/hooks/tests/run.sh`. `common.safe_main` turns any exception into a
  `systemMessage` starting `hook error` — which is exactly what the brain must never cause.
- `post_tool_use.py` lines ~95-103 sort verification commands into `state["evidence"]` (exit 0
  or unknown) and `state["red"]` (non-zero), storing `command[:300]`. `stop.py` has
  `verification_gate` (calls `common.block`, which exits 2) and `advisory_nudges` (three
  nudges: TDD, review, spend). `session_start.py` prints one `systemMessage` listing unfinished
  runs and returns early when there is no git root or no unfinished run.
- CLI precedent: `.claude/hooks/lib/project_conventions.py` (argparse, `--root`, never fails).
- Test precedent: `tests/test_token_efficiency.py` drives hooks via subprocess with
  `CLAUDE_HOOK_STATE_DIR`; `tests/test_structure.py` holds contract tests for skills and docs;
  `tests/run.sh` **line 14** lists the unit suites, line 147 asserts `7` gentic skills.
- `install.sh` installs whatever `git ls-files -- .claude` returns (untracked files are
  invisible to it until staged); `--check` prints `missing: hooks/lib/brain.py`-style lines.
- Environment: Python 3.13 / SQLite 3.53 here, with FTS5. **Minimum supported: Python 3.9,
  SQLite 3.35.** FTS5 is detected at runtime by attempting to create the virtual table inside a
  try/except; `GENTIC_BRAIN_NO_FTS=1` forces the `LIKE` path so tests can exercise it.

## Decisions (inlined; all `user — delegated` except the first)
- The brain exists, is SQLite, and the agent may use it as it likes — **user's instruction.**
- **Project key** = basename of the git root of the hook payload's `cwd` (hooks) or of the
  current directory (CLI), or `--project`. **No git root ⇒ hooks write nothing; the CLI exits 1
  with a one-line stderr message unless `--project` is given.** Same-named repos share memory;
  documented as a limitation.
- **Hot-path writes are best-effort:** `sqlite3.connect(path, timeout=0.034)`, WAL journal,
  `CREATE TABLE IF NOT EXISTS`, one INSERT, close; any exception → silent return. In-process,
  `brain.record_event` returns in under 89 ms even when the directory cannot be created.
- **Only `post_tool_use.py`, `stop.py` and `session_start.py` touch the brain**; the first two
  write, the third reads. `user_prompt_submit.py` and `pre_tool_use.py` are not changed.
- **Event kinds are exactly:** `red`, `verification`, `gate_block`, `nudge_tdd`,
  `nudge_review`, `nudge_spend`. Each row: `ts, project, session, kind, detail, data`. `detail`
  is the first 300 characters of the command (matching `post_tool_use.py`) or the block/nudge
  text's first 300 characters. **Secrets are scrubbed before storage:** any value following
  `Authorization:`, `--password`, `-p`(as a password flag to mysql/psql is not distinguishable;
  scrub only the four named forms), `token=`, `password=`, `secret=`, or an `AWS_…=` assignment
  is replaced by `***`.
- **Recall semantics:** `<words>` is split on whitespace; a note matches when every term is
  present in key or body. FTS5 path: `MATCH` on the AND of terms; `LIKE` fallback: one
  `LIKE '%term%'` per term, ANDed, over `key || ' ' || body`. Newest first, limit 8 unless `--limit`.
- **Preference rule:** among `user`-sourced decisions for a topic, take the most recent one's
  value; it is the preference **only if** that value has ≥2 user-sourced rows. `default`- and
  `learned`-sourced rows never count. User decides A, A, B ⇒ no preference (B has one row).
- **Stamps** are unique on `(project, slug, path)`; re-stamping the same slug replaces, a
  different slug adds.
- **`sql`** runs exactly one statement per invocation via `execute`. SELECT prints one JSON
  object per row (non-JSON values via `default=str`); other statements print nothing and exit 0;
  a SQL error prints the message to stderr and exits 1. **Before any statement whose first word
  (case-insensitive) is DROP, DELETE, UPDATE or ALTER, the database is copied to
  `<path>.bak` with the sqlite backup API** — one level of undo, overwritten each time.
- **Scoping:** `lessons`, `recall` and `stats` default to the current project; `--all` crosses.
- **Skill shape:** new `gentic-brain` skill (the eighth); one-line hooks into `gentic`,
  `gentic-scout`, `gentic-interview`, `gentic-masterprompt`, `gentic-execute`, `gentic-iterate`.
  `gentic-tdd` is excluded: it is a per-task discipline with nothing to remember.
- **The subcommand set is exactly:** `note`, `recall`, `decide`, `preference`, `lesson`,
  `lessons`, `stats`, `run start`, `run finish`, `stamp`, `sql`. No others.

## Constraints
- Stdlib only in `lib/brain.py`; no subprocess anywhere in it.
- `tests/test_gate.py` remains at 19 passing tests; the verification gate's decision logic and
  block text are unchanged. Adding one best-effort brain write immediately before
  `common.block()` and inside `advisory_nudges` is in scope.
- Latency: the two existing `run.sh` medians stay under 150 ms, and a **third median is added:
  `post_tool_use.py` with a verification payload that writes a brain event, under 150 ms.**
- `~/.claude/CLAUDE.md` rules apply: no secrets, no network, English identifiers.
- Every task test-first via `gentic-tdd`; observed RED into `progress.md`.

## Non-goals
- No consumer of the `events` table (no orchestrator bus, no dashboard).
- No evals, no gardener, no `retro.md`, no adjective catalogue — later runs.
- No migration of or dependency on `zcontext`; no MCP server; no embeddings.
- No schema versioning or migrations: a shape change in a later run may require deleting the
  file, and the README says so.
- No retention policy: `events` grows unbounded; accepted for this run.
- No guard, prompt or denylist on `sql` beyond the `.bak` copy — destructive statements are
  permitted by design.
- No import of existing run artifacts; the brain starts empty.
- No automatic notes: the agent decides what to `note`; hooks record only events.
- No change to the token guards, the agentignore guard or the classifier.
- No PATH entry, alias or wrapper for the CLI. No Windows support; no CI.

## Definition of Done
- [ ] D1 Note and recall. `brain note <key> <text…>` stores a note for the current project;
      `brain recall <words…>` prints matching notes (every term present in key or body), newest
      first, at most 8 unless `--limit N`; the `LIKE` path behaves the same under
      `GENTIC_BRAIN_NO_FTS=1`.
      verify: `python3 .claude/hooks/tests/test_brain.py -k recall`
      contract: tests/test_brain.py · test_note_then_recall_finds_it (two-term query matches
      terms in either order; an unrelated note is absent) and test_recall_falls_back_to_like
      (same assertions with FTS forced off) · expected RED: `AssertionError: 2 != 0 : brain CLI
      did not run`
- [ ] D2 Free SQL. `brain sql "<statement>"` executes one statement; SELECT rows print as one
      JSON object per line; a created table persists across invocations; a SQL error exits 1
      with the message on stderr.
      verify: `python3 .claude/hooks/tests/test_brain.py -k sql`
      contract: tests/test_brain.py · test_sql_is_unrestricted_inside_the_brain · `create table`,
      `insert`, `select` across three invocations round-trip; a syntax error exits 1 ·
      expected RED: `AssertionError: 2 != 0`
- [ ] D3 Preference learning. `brain decide <topic> <chosen…> --source user|default|learned`
      records; `brain preference <topic>` prints the learned value and exits 0 only under the
      rule in Decisions; otherwise prints nothing and exits 1.
      verify: `python3 .claude/hooks/tests/test_brain.py -k preference`
      contract: tests/test_brain.py · test_preference_needs_two_agreeing_user_decisions · one
      decision → exit 1; two agreeing user decisions → exit 0 with the value; two agreeing
      defaults → exit 1; user A, A, B → exit 1 · expected RED: `AssertionError: 2 != 0`
- [ ] D4 Lessons. `brain lesson --item I --rung R --points P --caught-by C --cause TEXT [--note
      TEXT] [--run SLUG]` stores; `brain lessons` lists the current project's rows newest first;
      `brain stats` prints lesson counts by `caught_by`, total points, note count and learned
      preference count for the current project.
      verify: `python3 .claude/hooks/tests/test_brain.py -k lesson`
      contract: tests/test_brain.py · test_lessons_recorded_and_summarised · after one lesson
      with `--caught-by suite --points 2`, `lessons` shows the item and `stats` contains
      `suite: 1` and `points: 2` · expected RED: `AssertionError: 2 != 0`
- [ ] D5 Runs and stamps. `brain run start <slug> --goal TEXT` and `brain run finish <slug>
      --outcome done|stopped` record lifecycle (unique per project+slug; finish updates);
      `brain stamp <slug> <paths…>` stores a sha256 per file, unique on (project, slug, path).
      verify: `python3 .claude/hooks/tests/test_brain.py -k run_lifecycle`
      contract: tests/test_brain.py · test_run_lifecycle_and_stamps · finish sets the outcome;
      stamping the same slug twice leaves one row per path with the newer hash; a second slug
      adds rows · expected RED: `AssertionError: 2 != 0`
- [ ] D6 Hooks write events. A `post_tool_use` payload with a failing verification command
      produces one `red` event whose `project` is the fixture repo's basename and whose `detail`
      starts with the command's first 40 characters; a passing one produces `verification`; a
      Stop gate block produces `gate_block`; a TDD nudge produces `nudge_tdd`; a command
      containing `Authorization: Bearer abc123` is stored without `abc123`.
      verify: `python3 .claude/hooks/tests/test_brain.py -k hooks_write` and
      `python3 .claude/hooks/tests/test_gate.py` (19 tests OK)
      contract: tests/test_brain.py · test_hooks_write_events_to_the_brain · counts per kind,
      project, detail prefix, secret absent · expected RED: `AssertionError: 0 != 1 : no red
      event in brain`
- [ ] D7 Brain failure is invisible. With `GENTIC_BRAIN` set to a path under a regular file (so
      the directory cannot be created), `post_tool_use.py` and `stop.py` exit 0, print no
      `hook error`, emit no `systemMessage`, and write nothing to stderr; and in-process
      `brain.record_event(...)` returns in under 89 ms under the same condition.
      verify: `python3 .claude/hooks/tests/test_brain.py -k invisible`
      contract: tests/test_brain.py · test_brain_failure_is_invisible_to_hooks · expected RED:
      observed against the first implementation of `record_event`, written without its
      try/except: `AssertionError: 'hook error' unexpectedly found in …`. The RED is watched
      before the guard is added; the guard is the GREEN.
- [ ] D8 Session start mentions the brain only when it has something. With ≥1 lesson or ≥1
      learned preference for the project, `session_start.py` emits a line
      `brain: N lesson(s), M learned preference(s) for <project> — python3 "$HOME/.claude/hooks/lib/brain.py" recall <words>`
      **even when there is no unfinished run**; when unfinished runs also exist, both go in the
      one `systemMessage`. With an empty brain the output is byte-identical to today's.
      verify: `python3 .claude/hooks/tests/test_brain.py -k session_start`
      contract: tests/test_brain.py · test_session_start_mentions_brain_when_it_has_something ·
      `brain:` in output after a lesson in a repo with no unfinished run; absent before ·
      expected RED: `AssertionError: 'brain:' not found in ''`
- [ ] D9 Project scoping. `lessons`, `recall` and `stats` default to the current project and
      `--all` crosses; without a git root and without `--project` the CLI exits 1.
      verify: `python3 .claude/hooks/tests/test_brain.py -k scoping`
      contract: tests/test_brain.py · test_lessons_default_to_current_project · a lesson from
      project B is absent without `--all`, present with it; no-git-root exit 1 · expected RED:
      `AssertionError: 2 != 0`
- [ ] D10 Skill wiring. `.claude/skills/gentic-brain/SKILL.md` exists with `name: gentic-brain`
      and a description that begins with `Use when` and names at least two of note / recall /
      decide / lesson; the six skills named in Decisions each contain `gentic-brain`;
      `GENTIC_SKILL` in `test_structure.py` matches `gentic-brain`; `run.sh` line 147 expects 8.
      verify: `python3 .claude/hooks/tests/test_structure.py`
      contract: tests/test_structure.py · test_brain_skill_is_wired_into_the_phases ·
      expected RED: `AssertionError: 'gentic-brain' not found in … gentic/SKILL.md`
- [ ] D11 Docs. `README.md` has a section headed `## The brain` containing `brain.sqlite`,
      `GENTIC_BRAIN`, the `sql` command, the `.bak` undo, the no-migration note and the
      synced-home (iCloud/Dropbox) caveat; `.claude/hooks/README.md` lists the six event kinds
      and states that brain failures are silent.
      verify: `python3 .claude/hooks/tests/test_brain.py -k docs`
      contract: tests/test_brain.py · test_docs_document_the_brain · expected RED:
      `AssertionError: 'brain.sqlite' not found in README`
- [ ] D12 Harness green with the suite registered and isolated. `bash .claude/hooks/tests/run.sh`
      exits 0, prints `test_brain (Ran N tests)` with N ≥ 10, prints a third latency line for
      `post_tool_use` under 150 ms, and exports `GENTIC_BRAIN` to a temp path before its first
      section.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: tests/test_brain.py · test_harness_registers_and_isolates_the_brain_suite ·
      asserts `run.sh` line 14's suite list contains `test_brain` and the file exports
      `GENTIC_BRAIN` before the `Unit and contract suites` section · expected RED:
      `AssertionError: 'test_brain' not found in …`
- [ ] D13 Installable. The installer's source list includes `hooks/lib/brain.py`,
      `hooks/tests/test_brain.py` and `skills/gentic-brain/SKILL.md` once they are staged.
      verify: `git ls-files -- .claude | grep -c brain` prints 3, and
      `python3 .claude/hooks/tests/test_install.py`
      contract: tests/test_install.py · test_source_list_includes_the_brain · expected RED:
      `AssertionError: 'hooks/lib/brain.py' not found in …`

## Risks & early signals
- SQLite open + insert on the hot path might exceed 150 ms on a slow disk: the third `run.sh`
  median is measured before any other task lands (task order below). If it exceeds the budget,
  buffer events in session state and flush at Stop — rung 3 territory, decided then.
- FTS5 external-content triggers are easy to get wrong: use a contentless-free simple FTS5
  table populated by triggers on insert only (notes are never updated), so no update trigger
  is needed.
- `stop.py`'s brain write must precede `common.block()` and must not delay it: one insert with a
  34 ms busy timeout.

## Task order (for Execute)
1. `lib/brain.py` core: schema, project key, `note`/`recall` (FTS + LIKE), `sql` with `.bak`,
   `record_event` with scrubbing — D1, D2, D6's storage half.
2. Hook wiring and the third latency median — D6, D7, D12's latency line. Riskiest, second.
3. `decide`/`preference`, `lesson`/`lessons`/`stats`, `run`/`stamp`, scoping — D3, D4, D5, D9.
4. `session_start` brain line — D8.
5. Skill + wiring + structure test + `run.sh` count and registration — D10, D12.
6. Docs + installer test — D11, D13.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read, this file only) returned 6 blocking, 15 serious and 8 minor
findings on the first draft. All were fixed inline above: the `brain` shorthand is now defined
as a literal command with no PATH side effect; `GENTIC_BRAIN` isolation in `run.sh` and every
test; the preference rule handles a changed mind; stamps are unique per run; event kinds and
the `detail` length are enumerated; the gate non-goal was aligned with the gate-block event;
D7's RED is an observed failure of the unguarded implementation; D12 and D13 have real
contracts; a third latency median covers the hook that actually writes; secrets are scrubbed;
destructive SQL gets a `.bak`; no-git-root behaviour, `sql` error semantics, `stats` scope,
minimum versions and the `run.sh` `.claude`-literal grep are all stated.
