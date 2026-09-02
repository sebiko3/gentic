# Masterprompt: skill-tuning-by-evals

## Mission
Two rules the fitness suite showed to be missing are added, each at the point where a headless
session misread the workflow: the Interview and the orchestrator continue to the next phase
in the same session when no question can be asked, and the task-executor answers only in its
report block. The PII grader becomes symmetric and a dollar-cap exhaustion is graded like a
turn exhaustion. Each change has a contract test that failed first, and one live suite run
proves the effect against suite `20260902-170309` (with 0.92 / without 0.35; csv with 3/4,
executor with 5/6).

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- **Interview stop, verbatim from `runs/csv-export-probe-with-0/transcript.jsonl` (suite
  20260902-170309):** after writing `decisions.md` the final message says "I'll proceed with
  these defaults unless you say otherwise — just flagging 1 and 2 explicitly since they're
  security-relevant." and the session ends at turn 23 of 55. `masterprompt.md` never exists.
- `gentic-interview/SKILL.md` section `## Non-interactive rule` (lines 37-39) currently reads:
  "If the session is autonomous (user away, scheduled run, or AskUserQuestion unavailable): do
  not block. Adopt the brief's recommended default for every open decision, set Source to
  `default — unconfirmed`, and make sure the final report to the user lists every unconfirmed
  default prominently." It becomes:
  "If `AskUserQuestion` is unavailable, the session is autonomous — whatever it looks like.
  Adopt the brief's recommended default for every open decision, set Source to `default —
  unconfirmed`, write `decisions.md`, and **continue to `gentic-masterprompt` in the same
  session. Never end the turn to ask, to flag, or to wait for an objection**: the flags belong
  in the final report, which lists every unconfirmed default prominently. Data, security and
  money decisions are adopted the same way, with their flag — the report is where the user
  reverses them."
- `gentic/SKILL.md` gains a section `## Autonomous runs`, placed before `## Red flags`:
  "When `AskUserQuestion` is unavailable the run is autonomous. Every phase gate is then
  crossed in the same session without pausing for confirmation, defaults are adopted and
  flagged `default — unconfirmed`, and the only legitimate stops are rung 5, rung 8, budget
  exhaustion, or a blocker no default can resolve. Ending a turn to 'flag' or to 'let the user
  object' is a stop, and it is the failure the fitness suite measures (`csv-export-probe`)."
  Its Red flags table gains a row: `"I'll proceed unless you object" — in an autonomous run
  there is nobody to object; continue, and put the flag in the report`.
- `task-executor.md` `## Output` gains, after "Be terse and literal.": "**The block below is
  your entire final message — nothing before it, nothing after it — for every status,
  including `blocked` and `assignment unclear`.** A question you would have asked goes in
  `blocker:`; the caller cannot answer it either, and reads only the block."
- **Contract tests** live in `.claude/hooks/tests/test_structure.py`, class `AutonomousRuns`
  (new): `test_interview_continues_when_no_question_can_be_asked` asserts the Interview skill
  contains, case-insensitively, `AskUserQuestion` is unavailable`, `continue to `gentic-masterprompt``
  and `never end the turn`; `test_orchestrator_has_an_autonomous_runs_section` asserts
  `gentic/SKILL.md` contains `## Autonomous runs` and `nobody to object`;
  `test_executor_block_is_the_entire_message` asserts `task-executor.md` contains
  `entire final message` and `assignment unclear` within its `## Output` section.
- **PII grader:** `evals/csv-export-probe/graders/pii-surfaced.md` pattern becomes
  `(password_hash|PII|personal data).{0,120}(unconfirmed|exclud|ask|confirm|decision|default)|(unconfirmed|exclud|ask|confirm|decision|default).{0,120}(password_hash|PII|personal data)`,
  `flags: is` unchanged. `test_evals.py::test_definition_graders_are_in_place` gains the csv
  case's `pii-surfaced` pattern to its pinned set (`EXPECTED["csv-export-probe"]` with exactly
  `brief-written` (file_exists), `pii-surfaced` (regex, the pattern above), `spec-before-code`
  (tool_used, `brief\.md`), `masterprompt-written` (file_exists)).
- **Budget exhaustion:** in `evals/run.py` `execute_run`, the exhaustion test becomes
  `facts["subtype"].startswith("error_max_")` (covers `error_max_turns` and the dollar cap's
  subtype whatever its exact suffix); everything else about exhaustion is unchanged. Test:
  `test_evals.py::test_budget_exhaustion_is_graded_like_turns` replays a transcript ending in
  `{"type":"result","subtype":"error_max_budget_usd","is_error":true,"result":null,…}` with
  `FAKE_CLAUDE_EXIT=1` and a touched file; the `file_exists` grader passes and the entry is
  `exhausted`.
- **README:** the `## Use` bullet "You're away? Runs don't block…" becomes "You're away, or the
  session is headless (`claude -p`, no `AskUserQuestion`)? Runs don't block and don't stop to
  flag: gentic adopts the scouted default for each question, flags it `unconfirmed`, continues
  through every phase, and lists every assumption in the final report." Contract:
  `test_structure.py::test_docs_document_the_tdd_spine` is not touched; a new assertion in
  `AutonomousRuns.test_readme_says_headless_runs_continue` checks `README.md` contains `headless`.
- **Install:** wording changes reach the with arm only through `./install.sh`; the live proof
  is preceded by `./install.sh` and `./install.sh --check` exit 0.
- **Live proof pattern:** Bash `run_in_background` to a log, `Monitor` on the log, no polling.
  Expected cost 6–9 USD (the csv with arm may now use up to 55 turns / 3 USD). Suite ceiling 21.
- Lessons carried: `-k` patterns are substrings of contract test names; no double-quoted
  `.claude` literal in a hook without `Path.home()`; the shell's cwd persists between tool
  calls — commit from the repo root.

## Decisions (inlined; all `user — delegated`)
Rule in both the Interview and the orchestrator; "autonomous" defined by the tool's absence;
one executor sentence; symmetric PII pattern; `error_max_*` = exhaustion; leak channel a
non-goal (login is not portable to a temp `HOME` or `CLAUDE_CONFIG_DIR`, probed); one live suite.

## Constraints
- Only the three wording sites named in Context change in skills and agents; no other skill or
  agent text changes. The four agent cases' graders and prompts are unchanged.
- Stdlib only; tests offline; `run.sh` green within budgets; `test_gate` 19, `test_brain` 13.
- Every task test-first; observed RED in `progress.md`.

## Non-goals
- No `HOME`/`CLAUDE_CONFIG_DIR` isolation for the without arm; no `tool_result` grader.
- No change to the turn budget (55) or the caps (3 / 21).
- No rewrite of the Interview's question craft, rounds, or scoring; no change to rung rules.
- No adjective compiler, no `retro.md`, no CI, no scheduling.
- No loosening of any grader; the PII change widens where the keyword may sit, not what is claimed.

## Definition of Done
- [ ] G1 Interview continues. `gentic-interview/SKILL.md` carries the new non-interactive rule.
      verify: `python3 .claude/hooks/tests/test_structure.py -k interview_continues`
      contract: tests/test_structure.py · test_interview_continues_when_no_question_can_be_asked ·
      expected RED: `AssertionError: 'never end the turn' not found in …`
- [ ] G2 Orchestrator never pauses. `gentic/SKILL.md` has `## Autonomous runs` and the red-flag row.
      verify: `python3 .claude/hooks/tests/test_structure.py -k autonomous_runs_section`
      contract: tests/test_structure.py · test_orchestrator_has_an_autonomous_runs_section ·
      expected RED: `AssertionError: '## Autonomous runs' not found in …`
- [ ] G3 Executor answers in the block. `task-executor.md` Output states the block is the
      entire final message for every status.
      verify: `python3 .claude/hooks/tests/test_structure.py -k executor_block`
      contract: tests/test_structure.py · test_executor_block_is_the_entire_message · expected
      RED: `AssertionError: 'entire final message' not found in …`
- [ ] G4 PII grader symmetric and pinned. The pattern above is in the grader file and pinned by
      the definition-graders test together with the csv case's other three graders.
      verify: `python3 .claude/hooks/tests/test_evals.py -k definition_graders`
      contract: tests/test_evals.py · test_definition_graders_are_in_place (csv case added) ·
      expected RED: `AssertionError: '(password_hash|PII|personal data).{0,120}(unconfirmed|…' != '…'`
      (the old pattern versus the new one)
- [ ] G5 Budget exhaustion graded. As in Context.
      verify: `python3 .claude/hooks/tests/test_evals.py -k budget_exhaustion`
      contract: tests/test_evals.py · test_budget_exhaustion_is_graded_like_turns · expected RED:
      `AssertionError: False is not true : file grader failed on a budget-exhausted run: claude exited 1:`
- [ ] G6 README says headless runs continue.
      verify: `python3 .claude/hooks/tests/test_structure.py -k headless_runs_continue`
      contract: tests/test_structure.py · test_readme_says_headless_runs_continue · expected RED:
      `AssertionError: 'headless' not found in …`
- [ ] G7 Harness green. `bash .claude/hooks/tests/run.sh` exits 0; `test_structure` and
      `test_evals` lines present; latency medians under 150 ms.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of G1–G6's tests; changes nothing observable of its own.
- [ ] G8 Live proof. After `./install.sh` and `./install.sh --check` exit 0: `python3 evals/run.py`
      under the defaults; `brain evals` for the new suite and for `20260902-170309` pasted into
      `progress.md`; per case one line `<case>: with <old>→<new> — <cause>, evidence <path>`;
      exit code matches the numbers; `totals.cost_usd` ≤ 21. The two targeted graders are
      reported explicitly: `csv-export-probe/masterprompt-written` (0→?) and
      `executor-refuses-vague/status-line` (2/3→?/3). Any `with` case below 1.0 → brain lesson.
      verify: run the commands; paste the outputs
      contract: n/a — the single observation of the real system.
- [ ] G9 The change moved the number. In the new suite, `masterprompt-written` passes in the
      csv with arm and `status-line` passes 3/3 in the executor with arm. If either does not,
      G9 is FAILED and the transcript-backed reason is a lesson; the wording is not iterated
      blindly in this run (a second attempt is rung 2, once, then stop).
      verify: `python3 ~/.claude/hooks/lib/brain.py sql "select case_name, arm, name, sum(passed), count(*) from eval_graders g join eval_runs r on g.run_id = r.id where r.suite = '<new suite>' and name in ('masterprompt-written','status-line') group by 1,2,3"`
      contract: n/a — observation of the live suite.

## Risks & early signals
- The csv with arm, now continuing, may exhaust 55 turns or 3 USD before Execute finishes;
  that is fine for G9 (`masterprompt-written` is a file grader) and is graded as exhaustion.
- The executor may still answer in prose one run in three; then G9 fails on that half and the
  lesson names the sentence that did not bind.
- `install.sh` overwrites `~/.claude/skills/gentic*/SKILL.md` and `~/.claude/agents/task-executor.md`.

## Task order (for Execute)
1. Contract tests, then the three wording changes — G1, G2, G3.
2. PII pattern + pin; budget-exhaustion subtype — G4, G5.
3. README line — G6; harness — G7.
4. Install, live proof, comparison, lessons — G8, G9.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
