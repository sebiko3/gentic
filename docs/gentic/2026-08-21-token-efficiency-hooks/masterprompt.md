# Masterprompt: token-efficiency-hooks

## Mission
Cut context-token waste in every Claude Code session on this machine. After this run, a repeat
read of an unchanged file is denied once with a message that steers the model back to what it
already has, a bare `cat` of a large file is denied once with a ranged-read suggestion, the
session's estimated tool-traffic spend is accumulated and reported to the user once when it
crosses a threshold, and identical re-runs of read-only commands are counted in that report —
all inside the setup's existing discipline: stdlib, sub-150 ms, one bounded deny per subject,
never a loop, never a broken session.

## Context
Paths relative to `/Users/sebiko83/code/gentic`. The hooks install machine-wide via `install.sh`.

- `pre_tool_use.py` is the only hook that sees `Read` (machine `settings.json`: PreToolUse
  matches `Bash|Read|Edit|Write|MultiEdit|NotebookEdit|NotebookRead`; PostToolUse has **no
  Read**). All Read accounting and the new guards therefore live on the PreToolUse path.
- On PreToolUse only a deny (exit 2, stderr) reaches the model; `systemMessage` reaches only the
  user (lib/common.py:113-116). `common.block(reason)` is the deny primitive (lib/common.py:119-123).
- Guard style to follow: `pre_tool_use.py` docstring — guards are "deliberately narrow.
  Everything not covered passes through with no decision at all."
- Session-scoped facts live in `state["session"]`, which `begin_turn` carries across turns
  (lib/common.py:29-40); everything else in the state dict is a per-turn ledger.
- The at-most-once template: `stop.py` sets `stop_block_fired` before blocking so a false
  positive "costs one extra turn and can never trap the user in a loop" (stop.py:14-16).
- Stop's advisory channel: `advisory_nudges` in `stop.py` collects due nudges into ONE
  `systemMessage`, each once per session. New advisory lines join `parts` there.
- Compaction keeps the session id and empties the model context, and SessionStart is registered
  only for `startup|resume` — so the read-ledger can be stale. The valve (below) is the answer;
  no settings.json change is available (`install.sh:36-38` never installs settings).
- The Read tool self-caps parameterless reads at 2000 lines; the unbounded funnel into context
  is Bash `cat`.
- Bash result sizes are measurable at PostToolUse via the serialised `tool_output` length
  (shape varies; see `exit_code_of` in post_tool_use.py). Token estimate everywhere: bytes / 4.
- Test conventions: unittest suites in `.claude/hooks/tests/`, registered in `run.sh:14`,
  helpers run hooks as subprocesses with `CLAUDE_HOOK_STATE_DIR` (test_tdd.py is the model).
  `run.sh` also enforces hostile-input survival and the 150 ms PreToolUse/UserPromptSubmit
  medians — the PreToolUse bench payload is a `Read`, so it exercises the new ledger path.
- Shared lib modules live in `.claude/hooks/lib/` (agentignore.py, project_conventions.py are
  the precedents). Put the new logic in `lib/token_efficiency.py`; keep `pre_tool_use.py` thin.

## Decisions
From `decisions.md`; Source marked. The enforcement-strength decision is **user-confirmed**.

1. **Duplicate-read guard (user).** Deny a parameterless `Read` of a path whose previous
   parameterless read this session recorded the same `st_mtime_ns` and `st_size`. At most one
   deny per path per session (valve ledger). Any `Read` carrying `offset` or `limit` always
   passes. A changed file always passes and refreshes the ledger. **Only parameterless reads
   are recorded in `reads` and only parameterless reads are checked against it** — partial reads
   contribute to spend but never to duplicate detection, in either direction. The deny text
   states: content already in context; if genuinely absent (post-compaction), re-read with
   `offset`/`limit`; this fires at most once per file.
2. **Bare-cat guard (default — unconfirmed).** Deny a Bash command that is exactly `cat` of one
   file larger than 89 KB — no pipes, no redirects, no `;`/`&&`, single file argument, flags
   allowed. `head`/`tail` are not covered (they self-limit). The file argument resolves against
   the payload's `cwd`; a path that cannot be resolved or statted passes (never guess). Same
   once-per-path valve ledger as the read guard (keyed by resolved path). Deny text suggests a
   ranged read (`sed -n 'A,Bp'` or Read with offset/limit).
3. **Spend report (default — unconfirmed).** Accumulate `session.spend_est` (estimated tokens):
   Read estimates at PreToolUse (stat size, prorated `limit × 55` bytes when a limit is given),
   Bash result sizes at PostToolUse. At Stop, when `spend_est` ≥ 55 000 and not yet reported
   this session, add one line to the combined advisory message: estimated spend, read/command
   counts, identical re-run count, and estimated tokens saved by denies. Once per session.
4. **Repeated identical Bash (user).** Count — never deny — exact repeats of *read-only* Bash
   commands (grep/rg/find/ls/cat/head/tail/wc/git log/git diff/git status) when no
   Edit/Write/MultiEdit/NotebookEdit landed between the two runs. Surface the count in the
   spend report only.
5. **Fibonacci constants (default — unconfirmed).** 89 KB cat threshold, 55 000-token report
   threshold, 55 bytes/line proration, bytes/4 token estimate. Module constants, no env plumbing.
6. **State placement (default — unconfirmed).** All new keys under `state["session"]`:
   `reads` {path: [mtime_ns, size]}, `guard_fired` [paths], `spend_est`, `spend_saved`,
   `bash_seen` {command: edit_seq}, `edit_seq`, `bash_repeats`, `reads_n`, `bash_n`,
   `spend_reported`. Absent keys default cleanly — old state files must keep loading.
   **Ownership:** `pre_tool_use` writes `reads`, `guard_fired`, `reads_n` and Read spend;
   `post_tool_use` writes `edit_seq`, `bash_seen`, `bash_repeats`, `bash_n` and Bash-result
   spend; `stop` writes `spend_reported`. No key has two writers.

## Constraints
- Python stdlib only, no subprocesses, no network; every hook exits 0 on hostile input; the
  `run.sh` latency medians stay under 150 ms. `os.stat` is allowed on the hot path; reading
  file *contents* in a hook is not.
- The only new exit-2 paths are the two guards above, each bounded to one deny per path per
  session. Stop gains no block. Existing guard and gate semantics are untouched.
- No `settings.json` or matcher changes; the design works with the events each hook already
  receives. `install.sh` is not run by this run.
- New session keys must be optional on load: a state file written before this change must not
  raise anywhere (`_fresh_turn` round-trips, `.get` access only).
- English identifiers/comments; new logic in `lib/token_efficiency.py`; `pre_tool_use.py` and
  `post_tool_use.py` stay orchestration-thin; skills are not touched.

## Non-goals
- **No settings.json edits, no new hook registrations, no new hook event coverage** (Read stays
  invisible to PostToolUse; Grep/Glob stay invisible everywhere).
- **No real token counting** — bytes/4 estimates only; no tokenizer, no API calls.
- **No denying repeated Bash commands** (user chose measure-only) and no covering `head`,
  `tail`, `sed`, or multi-file `cat` in the cat guard.
- **No per-project configuration surface** — constants are module-level; nothing reads
  `.agentignore` or project files for thresholds.
- **No changes to gentic skills or run artifacts** — this run is hooks + lib + tests + docs.
- **No compaction detection** — the valve is the whole answer to stale ledgers.
- **The spend estimate is not presented as a measurement** — the report says "estimated" and
  the docs state the ±heuristic nature.
- **No model-visible spend feedback.** The report is user-facing only; no UserPromptSubmit
  context injection about token spend (that would itself spend tokens every prompt).
- **No `/usage`-style command or dashboard** — one advisory line at Stop is the whole surface.

## Definition of Done

- [ ] **D1 — A parameterless repeat Read of an unchanged file is denied with a message naming
  the already-in-context fact, the offset/limit escape, and the once-per-file bound.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_duplicate_read_is_denied_once` ·
      first Read of a temp file exits 0, identical second Read exits 2 with stderr containing
      "already" and "offset" · expected RED: `AssertionError: 0 != 2 : duplicate read was not denied`

- [ ] **D2 — The valve holds: the third identical Read passes, a Read with offset or limit
  passes, and a Read of a since-modified file passes and refreshes the ledger.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_valve_never_denies_twice_per_path` ·
      after one deny the same Read exits 0; separate cases assert offset/limit and modified-file
      passes · expected RED: `AssertionError: 2 != 0 : valve failed — second deny on same path`

- [ ] **D3 — Bare `cat` of one file > 89 KB is denied once with a ranged-read suggestion;
  piped, redirected, multi-file, small-file, and `head`/`tail` forms all pass.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_bare_cat_of_large_file_is_denied_once` ·
      90 KB temp file: `cat f` exits 2 (stderr suggests a range), retry exits 0; `cat f | wc -l`,
      `cat small`, `head f` all exit 0 · expected RED: `AssertionError: 0 != 2 : bare cat passed`

- [ ] **D4 — Estimated spend accumulates in session state: a Read adds a stat-based estimate at
  PreToolUse, a Bash result adds its serialised size at PostToolUse, and both survive a turn
  boundary.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_spend_accumulates_across_turns` ·
      after a Read and a Bash with output, `session.spend_est` > 0 and grows monotonically across
      a `begin_turn` boundary · expected RED: `AssertionError: 0 not greater than 0 : no spend recorded`

- [ ] **D5 — Stop emits the spend line exactly once, only at ≥ 55k estimated tokens, joined into
  the single combined advisory message; below threshold it stays silent.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_spend_report_threshold_and_once` ·
      seeded state below threshold → no "estimated" in Stop output; above → one message containing
      "tokens"; second Stop silent · expected RED: `AssertionError: 'tokens' not found in '' : no spend report`

- [ ] **D6 — An exact repeat of a read-only Bash command with no intervening edit increments a
  counter and is never denied; an intervening edit resets eligibility.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_repeat_readonly_bash_counted_not_denied` ·
      same `grep` twice → exit 0 both times and `bash_repeats == 1`; edit between runs → 0
      (assert via `.get`, a KeyError is a test error) ·
      expected RED: `AssertionError: 0 != 1 : repeat not counted`

- [ ] **D7 — Legacy state upgrades in place: a pre-change state file (no new keys) fed into the
  new guard path still produces a correct deny, with every hook exiting cleanly — the new keys
  grow lazily instead of crashing or disabling the guard.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_legacy_state_upgrades_in_place` ·
      seed a hand-written legacy state JSON (evidence/touched/session, no new keys), then run the
      duplicate-read sequence: first Read exits 0, second exits 2, and no hook writes a traceback ·
      expected RED: `AssertionError: 0 != 2 : no deny on legacy state` (guard absent, so the
      sequence passes straight through — the same missing-feature RED as D1, proven on old state)

- [ ] **D8 — The whole harness is green: new suite registered in `run.sh`, hostile-input sweep
  still clean, latency medians still under 150 ms with the ledger active.**
      verify: `bash .claude/hooks/tests/run.sh` exits 0 with no `FAIL` line
      contract: `run.sh` suite list gains `test_token_efficiency`; its PreToolUse latency bench
      (a Read payload) now traverses the new ledger · expected RED (registration):
      run.sh shows no `test_token_efficiency` line until added — checked by inspection of the run log

- [ ] **D9 — The hooks README documents both guards, the valve, the estimate's heuristic
  nature, and the spend report.**
      verify: `cd .claude/hooks && python3 tests/test_token_efficiency.py`
      contract: `tests/test_token_efficiency.py` · `test_docs_document_the_guards` ·
      `.claude/hooks/README.md` mentions the duplicate-read guard, the 89 KB cat guard, the
      once-per-path valve, and "estimate" · expected RED:
      `AssertionError: 'valve' not found in … : hooks README does not document the guards`

- [ ] **D10 — `install.sh --check` lists the new lib module and test suite as pending, proving
  they are tracked and installable; nothing is installed by this run.**
      verify: `./install.sh --check; echo exit=$?` — output contains
      `lib/token_efficiency.py` and `tests/test_token_efficiency.py`, exit non-zero
      contract: manual inspection step (same as the prior run's D12) — files must be staged or
      committed before `--check` can see them · expected RED: paths absent while untracked

## Risks & early signals
- **The dupe guard fires on this very session** (dogfooding): the first legitimate deny will
  appear while building this run. Early signal that the valve works: the retry passes and work
  continues. A deny loop = the valve is broken; that is a stop-the-line bug, rung 1 immediately.
- **Stat-identity false negatives**: mtime granularity or editors that rewrite files can make a
  changed file look unchanged (same size, same mtime_ns is near-impossible after a real edit —
  risk accepted). The valve caps the damage at one retry.
- **Latency**: pre_tool_use does not appear to touch session state today (verify at Execute
  time). Adding load+save per Read/Bash event is new I/O on the hot path; the run.sh bench will
  catch a blowout. If the median regresses,
  fall back to load-on-Read/Bash-only (the matcher already limits events) and measure again.
- **PostToolUse payload shape drift** for `tool_output` sizes: use defensive serialisation
  (`json.dumps(default=str)` in a try) — a sizing failure must degrade to 0, never to a crash.
- **Two guards sharing a valve ledger** could mask each other (cat-deny consuming the read
  guard's one shot for the same path). Acceptable: the bound is per *path*, and one steer per
  path per session is the design intent; the tests pin it.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
