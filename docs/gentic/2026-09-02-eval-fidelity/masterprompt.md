# Masterprompt: eval-fidelity

## Mission
After this run the fitness number can be trusted. Every eval run leaves its transcript on
disk; a session that hits its turn limit is graded on what it produced; the four agent cases
assert the output shape each agent definition promises, so a built-in agent no longer passes;
agent cases run three times; the workflow case has 55 turns and a 3 USD cap. The suite runs
once more, live, and the two suites are recorded side by side.

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
  concatenated `text` blocks of the last `assistant` message in the transcript; otherwise "".
- **Run classification** (`execute_run`): `exhausted` = the result subtype is
  `error_max_turns`; such a run is *not* `is_error` and its `_error` is None, so graders run.
  `is_error` = scaffold failure, timeout, a non-zero exit with no `error_max_turns` subtype, or
  `is_error: true` with any other subtype. Both flags are in the arm entry, `result.json`, the
  console (`exhausted` printed after the fraction, e.g. `with 2/4 (0.50) exhausted`) and the
  brain.
- **Transcripts:** `execute_run` writes `proc.stdout` to `<workspace>/transcript.jsonl` and
  `proc.stderr` to `<workspace>/stderr.txt` before parsing; a timed-out run writes whatever was
  captured (use `exc.stdout`/`exc.stderr`, which may be None → empty). The arm entry carries
  `transcript` and `stderr` as paths relative to `evals/results/<suite>/`.
- **Brain:** `lib/brain.py` `ensure_schema` adds `exhausted INTEGER DEFAULT 0` to `eval_runs`
  when `PRAGMA table_info(eval_runs)` lacks it (guarded `ALTER TABLE`). `record_eval_run`
  gains a trailing `exhausted` argument (default 0). `eval_summary`/`cmd_evals` append
  ` exhausted` to an arm's fraction when any of its runs was exhausted.
- **Budgets:** `DEFAULT_RUN_BUDGET` becomes 3.0 (console/argv `--max-budget-usd 3`);
  `DEFAULT_SUITE_BUDGET` stays 21.0. `csv-export-probe`: `max_turns: 55`, `runs: 1`.
  Agent cases: `max_turns: 8`, `runs: 3`.
- **Agent graders** (files under `evals/<case>/graders/`; replace R2's where named):
  - `dod-auditor-false-claim`: fixture gains item `D3 The README reads well` with
    `verify: inspection, no stated pass condition` (the scaffold also creates `README.md`
    with one line). Graders: `reports-failed` (`regex` `\bFAILED\b`), `reports-proven`
    (`regex` `\bPROVEN\b`), `reports-unverifiable` (`regex` `\bUNVERIFIABLE\b`),
    `closing-count` (`regex` `\d+ proven, \d+ failed, \d+ unverifiable`, `flags: i`),
    `used-the-agent` (`tool_used`, `tool: Task`, `input_match: "subagent_type": "dod-auditor"`).
  - `critic-finds-contradiction`: `names-the-contradiction` unchanged; `five-scans` (`regex`
    `(?=.*two readings)(?=.*contradiction)(?=.*unverifiable)(?=.*missing non-goal)(?=.*unstated assumption)`,
    `flags: is`); `used-the-agent` with `input_match: "subagent_type": "masterprompt-critic"`.
  - `executor-refuses-vague`: `status-line` (`regex` `^\s*status:\s*(assignment unclear|blocked)`,
    `flags: im`) replaces `refuses`; `used-the-agent` with `input_match: "subagent_type": "task-executor"`.
  - `reviewer-seeded-defect`: `finds-injection`, `finds-silent-failure`, `ignores-decoy`
    unchanged; `confidence-scored` (`regex` `confidence \d{2,3}`); `not-reported-count`
    (`regex` `not reported`, `flags: i`).
  - `csv-export-probe`: `brief-written`, `pii-surfaced`, `spec-before-code` unchanged;
    `masterprompt-written` (`file_exists` `docs/gentic/*/masterprompt.md`).
  A grader value containing `:` (the `"subagent_type": "…"` patterns) must survive the flat
  parser: `parse_flat` splits on the **first** colon only, which keeps `input_match: "subagent_type": "x"`
  as the value `"subagent_type": "x"` after the outer quote strip — verify in a test, since the
  quote-strip rule removes a leading and trailing `"` only when they are the same character
  at both ends; write these values without outer quotes: `input_match: "subagent_type": "dod-auditor"`
  parses to `"subagent_type": "dod-auditor"` because the value starts and ends with `"` — that
  strips to `subagent_type": "dod-auditor`. **Therefore the parser gains one rule:** a value is
  unquoted only when it starts with a quote *and* the matching quote is its last character
  *and* contains no other quote; otherwise it is kept verbatim.
- **Comparison at the live proof:** `brain evals --suite 20260902-125057` and `brain evals`
  (latest) are both pasted; the report states, per case, whether the with-arm rate rose, fell
  or held, and why, from the transcripts.
- Lessons carried: every `-k` pattern must be a substring of its contract test's name; no
  double-quoted `.claude` literal in a hook without `Path.home()`; specs must not mandate
  literals the harness forbids.
- Environment: Claude Code 2.1.258, macOS, Python 3.13. Install must be in sync before the
  live proof (`./install.sh --check`).

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
- No transcript pruning or retention policy.

## Definition of Done
- [ ] F1 Transcripts kept. Each run's workspace holds `transcript.jsonl` (the raw stdout) and
      `stderr.txt`; the arm entry in `result.json` names both, relative to the suite directory.
      verify: `python3 .claude/hooks/tests/test_evals.py -k transcript`
      contract: tests/test_evals.py · test_transcript_is_kept_per_run · the file's content equals
      the fake's replayed transcript · expected RED: `AssertionError: False is not true :
      transcript.jsonl missing`
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
      has `max_turns: 55`, `runs: 1`; the four agent cases have `runs: 3`, `max_turns: 8`.
      verify: `python3 .claude/hooks/tests/test_evals.py -k invocation -k five_cases`
      contract: tests/test_evals.py · test_invocation_flags_per_arm (updated expectation) and
      test_five_cases_are_well_formed (updated expectation) · expected RED:
      `AssertionError: Lists differ: […'--max-budget-usd', '2'…] != […'3'…]` and
      `AssertionError: 21 != 55`
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
      contract: tests/test_evals.py · test_docs_fidelity_is_documented · expected RED:
      `AssertionError: 'transcript.jsonl' not found in …`
- [ ] F8 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 with `test_evals (Ran N tests)`,
      N ≥ 16, and the three latency medians under 150 ms.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: covered by F1–F7's tests being registered in the existing suite; expected RED:
      none of its own — the harness is the runner of the others.
- [ ] F9 Live proof and comparison. `./install.sh --check` exit 0; `python3 evals/run.py`
      under the defaults completes with five case lines and a suite line, exit matching the
      numbers (0 / 1 / 2 rule from R2); `brain evals` for the new suite and for
      `20260902-125057` are both pasted; every case's with-arm change is explained from the
      transcripts; any `with` case below 1.0 becomes a brain `lesson` (`--caught-by suite`).
      Cost stays under the 21 USD ceiling.
      verify: run the commands; paste the outputs into `progress.md`
      contract: n/a — the single observation of the real system; the pasted output is the evidence.

## Risks & early signals
- 55 turns may still be exhausted by the with arm; the run is then graded on what exists and
  the exhaustion is a lesson, not a reason to raise the budget here.
- Three runs × four agent cases lengthen the live proof to 25–40 minutes; the background
  runner and monitor pattern from R2 applies.
- The `"subagent_type"` patterns stress the flat parser; F6's parser assertion catches it.

## Task order (for Execute)
1. Transcripts, exhaustion classification, last-message fallback — F1, F2, F3.
2. Brain column and summary — F4.
3. Budgets, runs, turn budget, parser rule, agent graders and fixtures — F5, F6.
4. Docs and harness — F7, F8.
5. Live proof, comparison, lessons — F9.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
