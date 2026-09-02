# Masterprompt: eval-fidelity

## Mission
After this run the fitness number can be trusted. Every eval run leaves its transcript on
disk; a session that hits its turn limit is graded on what it produced; the four agent cases
assert the output shape each agent definition promises, so a built-in agent no longer passes;
agent cases run three times; the per-run budget becomes 3 USD for every case and the workflow
case gets 55 turns. The suite runs once more, live, and both suites' numbers are pasted into
`progress.md` with a per-case explanation drawn from the transcripts.

**R2** in this file means the previous eval run, whose suite is `20260902-125057` (its rows are
in this machine's brain and its `result.json` is under `evals/results/20260902-125057/`).

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- Runner: `evals/run.py` (R2). Relevant functions: `parse_transcript` (keeps only
  `result.result` as last message), `execute_run` (no stdout kept; exit ≠ 0 → `_error`),
  `grade` (any `_error` fails every grader), `skipped_run`, `run_suite` (console line via
  `console_line`, `result.json`, brain calls). Tests: `.claude/hooks/tests/test_evals.py`
  with the fake `claude` (`FAKE_CLAUDE_TRANSCRIPT`, `FAKE_CLAUDE_EXIT`, `FAKE_CLAUDE_TOUCH`,
  `FAKE_CLAUDE_ARGV`). `test_invocation_flags_per_arm` pins `--max-budget-usd 2`;
  `test_five_cases_are_well_formed` pins `max_turns` 21 (csv) / 8 (agents) and does not check
  `runs`. Both are contracts this run changes test-first.
- Exhaustion, verified on Claude Code 2.1.258: the final `result` line is
  `{"type":"result","subtype":"error_max_turns","is_error":true,"result":null,"num_turns":N,
  "total_cost_usd":C,"stop_reason":"tool_use"}` and the process exits 1. A normal end has
  `subtype: "success"` and a string `result`.
- **Last message rule:** `result.result` when it is a non-empty string; otherwise the
  concatenated `text` blocks of the last `assistant` message **that contains at least one
  non-empty `text` block** (an exhausted session's final assistant message is usually a bare
  `tool_use`, which must be skipped); otherwise "".
- **Run classification** (`execute_run`): `exhausted` = the result subtype is
  `error_max_turns`; such a run is *not* `is_error` and its `_error` is None, so graders run.
  `is_error` = scaffold failure, timeout, a non-zero exit with no `error_max_turns` subtype, or
  `is_error: true` with any other subtype. Both flags are in the arm entry, `result.json`, the
  console (`exhausted` printed after the fraction, e.g. `with 2/4 (0.50) exhausted`) and the
  brain.
- **Transcripts:** `execute_run` writes `proc.stdout` to `<workspace>/transcript.jsonl` and
  `proc.stderr` to `<workspace>/stderr.txt` **after `_created` has been computed**, and
  `snapshot()` additionally excludes those two names, so neither can ever count as a file the
  agent created (a test asserts this). A timed-out run writes whatever was captured
  (`exc.stdout`/`exc.stderr`, which may be None → empty). Every non-skipped, non-scaffold-error
  arm entry carries `transcript` and `stderr` as paths relative to `evals/results/<suite>/`;
  skipped and scaffold-error entries carry `null` for both. Transcripts are raw stdout: no
  scrubbing, truncation or compression (`evals/results/` is git-ignored).
- **Brain:** `lib/brain.py` `ensure_schema` adds `exhausted INTEGER DEFAULT 0` to `eval_runs`
  when `PRAGMA table_info(eval_runs)` lacks it (guarded `ALTER TABLE`). `record_eval_run`
  gains a trailing `exhausted` argument (default 0). `eval_summary`/`cmd_evals` append
  ` exhausted` to an arm's fraction when any of its runs was exhausted.
- **Budgets:** `DEFAULT_RUN_BUDGET` becomes 3.0 (argv `--max-budget-usd 3`, every case);
  `DEFAULT_SUITE_BUDGET` stays 21.0; `DEFAULT_MAX_TURNS` stays 13 — 55 is per-case. The
  `total_cost` accumulation moves inside the run loop (today it is added per case, so with
  `runs: 3` one case could spend six runs before the ceiling check saw any of it); the ceiling
  check therefore holds per run. Case configuration lives in each case's `prompt.md`
  frontmatter (`case.yaml` supports only `context.scaffold_script`): `csv-export-probe`
  `max_turns: 55`, `runs: 1`; the four agent cases `max_turns: 8`, `runs: 3`.
- **Agent graders** (files under `evals/<case>/graders/`; replace R2's where named):
  - `dod-auditor-false-claim`: `fixture/masterprompt.md` gains, after D2, exactly these lines:
    ```
    - [ ] D3 The README reads well
          verify: inspection
    ```
    and the scaffold also runs `printf 'Two files.\n' > README.md`. `prompt.md` becomes
    `Dispatch the dod-auditor agent on ./masterprompt.md and relay its verdict table and its closing count line verbatim.`
    Graders: `reports-failed` (`regex` `\bFAILED\b`), `reports-proven`
    (`regex` `\bPROVEN\b`), `reports-unverifiable` (`regex` `\bUNVERIFIABLE\b`),
    `closing-count` (`regex` `\d+ proven, \d+ failed, \d+ unverifiable`, `flags: i`),
    `used-the-agent` (`tool_used`, `tool: Task`, `input_match: "subagent_type": "dod-auditor"`).
  - `critic-finds-contradiction`: `prompt.md` becomes `Dispatch the masterprompt-critic agent on ./masterprompt.md and relay all of its scan sections verbatim.`;
    `names-the-contradiction` unchanged; `five-scans` (`regex`
    `(?=.*two readings)(?=.*contradiction)(?=.*unverifiable)(?=.*missing non-goal)(?=.*unstated assumption)`,
    `flags: is`); `used-the-agent` with `input_match: "subagent_type": "masterprompt-critic"`.
  - `executor-refuses-vague`: `prompt.md` becomes `Dispatch the task-executor agent with exactly this assignment and nothing else: "improve the code". Relay its report block verbatim.`;
    `status-line` (`regex` `^\s*status:\s*(assignment unclear|blocked)`, `flags: im`) replaces
    `refuses`; `used-the-agent` with `input_match: "subagent_type": "task-executor"`.
  - `reviewer-seeded-defect`: `prompt.md` becomes `Dispatch the code-reviewer agent on ./seeded_defect.py, naming that file as the review scope, and relay its findings and its closing "Not reported" line verbatim.`;
    `finds-injection`, `finds-silent-failure`, `ignores-decoy` unchanged; `confidence-scored`
    (`regex` `confidence \d{2,3}`, `flags: i`); `not-reported-count` (`regex` `not reported`,
    `flags: i`). This case deliberately gets **no** `used-the-agent` grader — do not add one;
    its denominator stays comparable with R2 plus the two new shape graders.
  - `csv-export-probe`: `brief-written`, `pii-surfaced`, `spec-before-code` unchanged;
    `masterprompt-written` (`file_exists` `docs/gentic/*/masterprompt.md`).
  Changing a case's `prompt.md` wording to request the output the graders assert is not a
  loosening; the protected list covers grader patterns only.
  **Parser rule (one rule, nothing else):** today `parse_flat` turns
  `input_match: "subagent_type": "dod-auditor"` into `subagent_type": "dod-auditor` because the
  value's first and last characters are both `"` (verified). The rule becomes: strip the outer
  quotes only when the value contains no further occurrence of *that same* quote character;
  otherwise keep the value verbatim. `parse_flat` gains no escape handling, no nesting, no new
  value types.
- **Comparison at the live proof:** after `./install.sh` (F4 changes `brain.py`, so the
  installed copy must be refreshed; this overwrites `~/.claude/hooks/lib/brain.py`) and
  `./install.sh --check` exit 0, run `python3 ~/.claude/hooks/lib/brain.py evals --suite 20260902-125057`
  and `python3 ~/.claude/hooks/lib/brain.py evals` (latest) and paste both into `progress.md`.
  If the R2 rows are absent from the brain, say so and paste `evals/results/20260902-125057/result.json`'s
  totals instead. Then, in `progress.md`, one line per case in exactly this shape:
  `<case>: with <old>→<new> — <cause>, evidence <transcript path relative to evals/results/>`.
- **Background pattern for the live proof:** the suite takes 25–40 minutes; launch it with the
  Bash tool's `run_in_background` writing to a log file, then arm a `Monitor` that echoes each
  case line and ends on the runner's exit line. Never poll with sleeps.
- Lessons carried: every `-k` pattern must be a substring of its contract test's name; no
  double-quoted `.claude` literal in a hook without `Path.home()`; specs must not mandate
  literals the harness forbids.
- Environment: Claude Code 2.1.258, macOS, Python 3.13; the live proof needs an authenticated
  `claude` on `PATH` with billing enabled; everything before F9 runs fully offline. The
  `exhausted` column is added to the user's machine-wide brain by an additive, idempotent
  `ALTER TABLE … ADD COLUMN … DEFAULT 0` the first time the new `brain.py` opens it; an older
  checkout keeps reading the migrated brain; no downgrade path is provided.
- Test fixtures: F2 and F3 each write their own transcript fixture inside the test; the shared
  module-level `TRANSCRIPT` in `test_evals.py` is not modified (`Money` and `Graders` depend on it).

## Decisions (inlined; all `user — delegated`, the turn budget explicitly so)
55 turns and 3 USD per run for workflow cases; exhausted runs graded; transcripts kept; agent
graders assert definition shapes and exact `subagent_type`; agent cases run three times;
`exhausted` column via guarded ALTER; comparison by two `brain evals` invocations.

## Constraints
- Stdlib only; no real `claude` call in tests; `run.sh` offline and within budgets;
  `test_gate` 19, `test_brain` 13 stay green; every task test-first with observed RED.
- Cases are never loosened to pass: a grader may become stricter or more specific, never
  looser. `pii-surfaced`, `names-the-contradiction`, `finds-*`, `ignores-decoy` keep their
  patterns byte-for-byte.
- The live proof is one suite run under the defaults (both arms, sonnet, 3/21).

## Non-goals
- No change to any skill or agent definition; the agents are measured, not tuned.
- No `brain evals --compare`, no diff feature, no HTML, no CI, no scheduling.
- No `llm` graders; no new grader types; no parallelism; no retries.
- No raising of the turn budget within this run if 55 is exhausted — that is a lesson.
- No adjective compiler, no `retro.md` (moved to a later run).
- No transcript pruning, retention policy, scrubbing, truncation or compression.
- No `exhausted` in `totals`, in the suite line, or behind any new CLI flag: the case line, the
  arm entry, `result.json`'s arm entries and `brain evals` are the whole surface.
- No general YAML upgrade to `parse_flat`.

## Definition of Done
- [ ] F1 Transcripts kept. Each run's workspace holds `transcript.jsonl` (the raw stdout) and
      `stderr.txt`; the arm entry in `result.json` names both, relative to the suite directory.
      verify: `python3 .claude/hooks/tests/test_evals.py -k transcript`
      contract: tests/test_evals.py · test_transcript_is_kept_per_run · the file's content equals
      the fake's replayed transcript, and a `file_exists` grader for `transcript.jsonl` fails
      (never "created") · expected RED: `AssertionError: False is not true : transcript.jsonl missing`
- [ ] F2 Exhausted runs are graded. A replayed transcript ending in `error_max_turns` with
      `FAKE_CLAUDE_EXIT=1` yields `exhausted: true`, `is_error: false`; a `file_exists` grader
      passes on a touched file and a `tool_used` grader on its tool_use; the console line shows
      `exhausted`. A non-zero exit whose result subtype is `success` stays `is_error`.
      verify: `python3 .claude/hooks/tests/test_evals.py -k exhausted_run`
      contract: tests/test_evals.py · test_exhausted_run_is_scored_on_its_files · expected RED:
      `AssertionError: False is not true : file grader failed on an exhausted run: claude exited 1:`
- [ ] F3 Last-message fallback. With `result: null`, a `regex` grader over `last_message`
      matches the last assistant text block; with a string result, the result wins.
      verify: `python3 .claude/hooks/tests/test_evals.py -k last_message`
      contract: tests/test_evals.py · test_last_message_falls_back_to_assistant_text · expected
      RED: `AssertionError: False is not true : no match for /nearly there/ in last_message`
- [ ] F4 Brain records exhaustion. `eval_runs` has an `exhausted` column (added to an existing
      brain by the guarded ALTER), `record_eval_run` stores it, and `brain evals` prints
      `exhausted` after that arm's fraction.
      verify: `python3 .claude/hooks/tests/test_evals.py -k brain_exhausted` and
      `python3 .claude/hooks/tests/test_brain.py`
      contract: tests/test_evals.py · test_brain_exhausted_column_and_summary · a brain created
      by R2's schema (table without the column) gains it · expected RED: `AssertionError:
      'exhausted' not found in ['id', 'ts', …]`
- [ ] F5 Budgets and runs. The invocation argv carries `--max-budget-usd 3`; `csv-export-probe`
      has `max_turns: 55`, `runs: 1`; the four agent cases have `runs: 3`, `max_turns: 8`; the
      suite ceiling is checked against cost accumulated per run (with `runs: 3` and fake runs
      costing 8 each under a 21 ceiling, the third run of the *first* case is skipped).
      verify: `python3 .claude/hooks/tests/test_evals.py -k invocation -k five_cases -k money`
      contract: tests/test_evals.py · test_invocation_flags_per_arm (expectation updated first),
      test_five_cases_are_well_formed (expectation updated first), test_money_ceiling_and_exit_codes
      (a `runs: 3` case added) · expected RED: `AssertionError: Lists differ:
      […'--max-budget-usd', '2'…] != […'3'…]`; `AssertionError: 21 != 55`;
      `AssertionError: 6 != 2 : ceiling ignored runs inside a case`
- [ ] F6 Agent graders assert the definitions. A contract test over `evals/` asserts the
      grader names and patterns listed in Context per case, that every `used-the-agent`
      `input_match` contains `"subagent_type"`, and that the protected patterns are unchanged;
      the flat parser keeps a value with an inner colon intact.
      verify: `python3 .claude/hooks/tests/test_evals.py -k definition_graders`
      contract: tests/test_evals.py · test_definition_graders_are_in_place · expected RED:
      `AssertionError: 'reports-unverifiable' not found in ['reports-failed', …]`
- [ ] F7 Docs. `README.md`'s fitness-function section mentions `transcript.jsonl`, `exhausted`,
      the 55-turn budget with the reason (22 turns for two phases in R2), `runs: 3`, and the
      3 USD cap.
      verify: `python3 .claude/hooks/tests/test_evals.py -k docs_fidelity`
      contract: tests/test_evals.py · test_docs_fidelity_is_documented · tokens `55`, `22 turns`,
      `transcript.jsonl`, `exhausted`, `runs: 3`, `3 USD` present (the reason itself is prose the
      token check does not verify) · expected RED: `AssertionError: 'transcript.jsonl' not found in …`
- [ ] F8 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 with `test_evals (Ran 17 tests)`
      and the three latency medians under 150 ms.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — F8 changes nothing observable of its own; it is the runner of F1–F7's tests.
- [ ] F9 Live proof and comparison. `./install.sh --check` exit 0; `python3 evals/run.py`
      under the defaults completes with five case lines and a suite line, exit matching the
      numbers (exit 2 iff any run skipped, else 1 iff any `with` case below 1.0, else 0);
      `brain evals` for the new suite and for `20260902-125057` are both pasted into
      `progress.md`; `progress.md` holds one line per case in the shape given in Context
      (`<case>: with <old>→<new> — <cause>, evidence <transcript path>`); any `with` case below
      1.0 becomes a brain `lesson` (`--caught-by suite`). `result.json` `totals.cost_usd` ≤ 21.
      verify: run the commands; paste the outputs into `progress.md`
      contract: n/a — the single observation of the real system; the pasted output is the evidence.
- [ ] F10 The shape graders discriminate. On the live suite, the `without` arm's rate on each of
      `closing-count`, `five-scans` and `status-line` is below 1.0 (a built-in agent does not
      produce the definitions' shapes). If any of the three is 1.0 in the without arm, F10 is
      FAILED and the grader is recorded as a lesson — it is not rewritten in this run.
      verify: `python3 ~/.claude/hooks/lib/brain.py sql "select case_name, arm, name, sum(passed), count(*) from eval_graders g join eval_runs r on g.run_id = r.id where r.suite = '<new suite>' and name in ('closing-count','five-scans','status-line') group by 1,2,3"`
      contract: n/a — an observation of the live suite; the query output is the evidence.

## Risks & early signals
- 55 turns may still be exhausted by the with arm; the run is then graded on the files it
  created, the tools it used and its last text, and the exhaustion is a lesson, not a reason to
  raise the budget here.
- `confidence-scored` may fail on the with arm if the reviewer re-cases or rephrases its
  template; that is recorded as a lesson, never a definition change (non-goal).
- Three runs × four agent cases lengthen the live proof to 25–40 minutes; the background
  runner and monitor pattern from R2 applies.
- The `"subagent_type"` patterns stress the flat parser; F6's parser assertion catches it.

## Task order (for Execute)
1. Transcripts, exhaustion classification, last-message fallback — F1, F2, F3.
2. Brain column and summary — F4.
3. Budgets (per-run accumulation), runs, turn budget, parser rule, agent graders, prompts and
   fixtures — F5, F6. Update each test's expectation before touching the case files, so the RED
   reads `21 != 55`, not the reverse.
4. Docs and harness — F7, F8.
5. Live proof, comparison, lessons — F9, F10 (after `./install.sh` and `--check` exit 0).

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read) on the first draft: 4 blocking, 14 serious, 12 minor. All
fixed inline: last-message rule skips text-less assistant messages; transcripts written after
the created-file snapshot and excluded from it; the parser paragraph replaced by one rule;
per-run budget applies to every case; configuration lives in `prompt.md`; exact fixture lines;
`confidence-scored` case-insensitive; per-run cost accumulation (F5); F8 RED as `n/a` with
reason; expectation-first order for F5; F9 given a per-case line shape; F10 added to measure
the without arm; `brain evals` path and install refresh spelled out; F7 tokens named; `null`
transcript paths for skipped/errored entries; N = 17; reviewer case explicitly without
`used-the-agent`; non-goals for `exhausted` surface, scrubbing, `DEFAULT_MAX_TURNS`, parser
scope; own fixtures for F2/F3; ALTER stated as additive/idempotent; R2 defined and the
background pattern spelled out; environment needs; prompt wording may change.
