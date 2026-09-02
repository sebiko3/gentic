# Masterprompt: skill-tuning-by-evals

## Mission
Two rules the fitness suite showed to be missing are added, each at the point where a headless
session misread the workflow: the Interview and the orchestrator continue to the next phase
in the same session when no question can be asked, and the task-executor answers only in its
report block. The PII grader becomes symmetric and a dollar-cap exhaustion is graded like a
turn exhaustion. Each change has a contract test that failed first, and one live suite run
measures the effect against the **baseline** suite `20260902-170309` (baseline numbers: with
0.92 / without 0.35; csv with 3/4, executor with 5/6). Only G9's two graders are targets; the
suite score is recorded, not gated. The csv sample is n=1 (`runs: 1`) and the executor sample
n=3: a csv pass is evidence, not proof, and the report says so.

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
  unconfirmed`, write `decisions.md`, and **do not end the turn: return to the orchestrator,
  which crosses the gate and invokes `gentic-masterprompt` in the same session. Never end the
  turn to ask, to flag, or to wait for an objection**: the flags belong in the final report,
  which lists every unconfirmed default prominently. Data, security and money decisions are
  adopted the same way, with their flag — the report is where the user reverses them."
- `gentic/SKILL.md` gains a section `## Autonomous runs`, placed before `## Red flags`:
  "When `AskUserQuestion` is unavailable the run is autonomous. Every phase gate is then
  crossed in the same session without pausing for confirmation, defaults are adopted and
  flagged `default — unconfirmed`, and the only legitimate stops are rung 5, rung 8, budget
  exhaustion, or a blocker no default can resolve. Ending a turn to 'flag' or to 'let the user
  object' is a stop, and it is the failure the fitness suite measures (`csv-export-probe`)."
  Its `## Red flags` bullet list gains a bullet: `- "I'll proceed unless you object" — in an
  autonomous run there is nobody to object; continue, and put the flag in the report.`
- `task-executor.md` `## Output` gains, after "Be terse and literal.": "**The block below is
  your entire final message — nothing before it, nothing after it — for every status,
  including `blocked` and `assignment unclear`.** A question you would have asked goes in
  `blocker:`; the caller cannot answer it either, and reads only the block."
- **Contract tests** live in `.claude/hooks/tests/test_structure.py`, class `AutonomousRuns`
  (new). Needles are Python literals applied to `body.lower()`:
  `test_interview_continues_when_no_question_can_be_asked` asserts the Interview skill's
  lowered text contains `'`askuserquestion` is unavailable'`, `'never end the turn'` and
  `'return to the orchestrator'`; `test_orchestrator_has_an_autonomous_runs_section` asserts
  the lowered `gentic/SKILL.md` contains `'## autonomous runs'` and `'nobody to object'`;
  `test_executor_block_is_the_entire_message` asserts the lowered text after `'## output'` in
  `task-executor.md` contains `'entire final message'` and `'assignment unclear'`;
  `test_readme_says_headless_runs_continue` asserts the lowered `README.md` contains
  `'no `askuserquestion`'` and `"don't stop to flag"`. (`README.md` already contains the word
  "headless"; that word is not a needle.) Every verify command runs from the repo root;
  `python3 <file> -k <pattern>` needs Python ≥ 3.7.
- **PII grader:** `evals/csv-export-probe/graders/pii-surfaced.md` pattern becomes
  `(password_hash|PII|personal data).{0,120}(unconfirmed|exclud|ask|confirm|decision|default)|(unconfirmed|exclud|ask|confirm|decision|default).{0,120}(password_hash|PII|personal data)`,
  `flags: is` unchanged. `test_evals.py::test_definition_graders_are_in_place` gains
  `EXPECTED["csv-export-probe"]` with exactly four graders: `brief-written` (`file_exists`,
  `path` `docs/gentic/*/brief.md`), `pii-surfaced` (`regex`, the pattern above),
  `spec-before-code` (`tool_used`, `input_match` `brief\.md`), `masterprompt-written`
  (`file_exists`, `path` `docs/gentic/*/masterprompt.md`); the test's pinned-field selection
  gains a `file_exists → "path"` branch. A second test,
  `test_pii_grader_rejects_a_silent_decision`, compiles the pattern with `re.I | re.S` and
  asserts it matches `"I excluded password_hash from the export."` and
  `"password_hash is exported — an unconfirmed default."` and does **not** match
  `"Exported every column, including password_hash, as requested."` — the widening changes
  where the keyword may sit, not what is claimed.
- **Budget exhaustion:** in `evals/run.py` `execute_run`, the exhaustion test becomes
  `facts["subtype"].startswith("error_max_")`. The CLI's real subtype for the dollar cap is
  **unverified** here (`error_max_budget_usd` is the assumed spelling); G5 proves the prefix
  rule, not the CLI's behaviour. Nothing else about exhaustion changes: no new fields in
  `result.json` or the brain for the reason. Test:
  `test_evals.py::test_budget_exhaustion_is_graded_like_turns` replays a transcript ending in
  `{"type":"result","subtype":"error_max_budget_usd","is_error":true,"result":null,…}` with
  `FAKE_CLAUDE_EXIT=1` and a touched file; the `file_exists` grader passes and the entry is
  `exhausted`.
- **README:** the `## Use` bullet "You're away? Runs don't block…" becomes "You're away, or the
  session is headless (`claude -p`, no `AskUserQuestion`)? Runs don't block and don't stop to
  flag: gentic adopts the scouted default for each question, flags it `unconfirmed`, continues
  through every phase, and lists every assumption in the final report." No other doc changes:
  not `CLAUDE.md`, not `ROUTING.md`, not the hooks README.
- **Install:** wording changes reach the with arm only through `./install.sh`; the live proof
  is preceded by `./install.sh` and `./install.sh --check` exit 0.
- **Live proof prerequisites, checked before any spend:** `claude` on `PATH` and logged in
  (`claude --version` recorded); `./install.sh` run, then `./install.sh --check` exit 0 (this
  overwrites `~/.claude/skills/gentic*/SKILL.md` and `~/.claude/agents/task-executor.md`;
  accepted); `~/.claude/hooks/lib/brain.py` present; the local brain holds the baseline —
  `python3 ~/.claude/hooks/lib/brain.py evals --suite 20260902-170309` prints it. If the
  baseline is absent, the Mission's baseline numbers are the comparison and G8's second paste
  is dropped. Pattern: Bash `run_in_background` to a log, `Monitor` on the log, no polling;
  26 sessions, 30–45 minutes. **6–9 USD is an estimate, not a limit; the only stop is the
  runner's own 21 ceiling — do not interrupt the suite for cost.** The ceiling is checked per
  launch as `spent + 3 > 21`, and `executor-refuses-vague` is the fourth of five cases; if the
  suite skips anything, `totals.skipped > 0` fails G8 and the two targeted cases are re-run
  with `--case csv-export-probe` and `--case executor-refuses-vague` as separate suites.
- **Lessons in the brain** are recorded with
  `python3 ~/.claude/hooks/lib/brain.py lesson --item "<case> with arm <k>/<n> (suite <id>)" --rung 1 --points 0 --caught-by suite --cause "<from the transcript>" --run skill-tuning-by-evals`;
  they carry 0 points and never spend the iteration budget.
- Lessons carried: `-k` patterns are substrings of contract test names; no double-quoted
  `.claude` literal in a hook without `Path.home()`; the shell's cwd persists between tool
  calls — commit from the repo root with absolute paths.

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
- No new or removed graders on `csv-export-probe`: only `pii-surfaced`'s pattern changes, the
  count stays 4 so the baseline comparison holds. No other grader changes at all.
- No change to `install.sh`; the overwrite of the installed skills and agent is accepted.
- No new fields for the exhaustion reason; the boolean is the whole change.
- No change to `CLAUDE.md`, `ROUTING.md`, or any doc except the one README bullet (G6).

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
- [ ] G4 PII grader symmetric, pinned, and still strict. The pattern above is in the grader
      file, pinned with the csv case's other three graders, and rejects a silent PII decision.
      verify: `python3 .claude/hooks/tests/test_evals.py -k definition_graders -k pii_grader`
      contract: tests/test_evals.py · test_definition_graders_are_in_place (csv case added;
      expected RED: `AssertionError: '(password_hash|PII|personal data).{0,120}(unconfirmed|…' != '…'`,
      old pattern versus new) and test_pii_grader_rejects_a_silent_decision (expected RED:
      `AssertionError: None is not true : symmetric form not matched` on the old pattern)
- [ ] G5 Budget exhaustion graded. As in Context.
      verify: `python3 .claude/hooks/tests/test_evals.py -k budget_exhaustion`
      contract: tests/test_evals.py · test_budget_exhaustion_is_graded_like_turns · expected RED:
      `AssertionError: False is not true : file grader failed on a budget-exhausted run: claude exited 1:`
- [ ] G6 README says headless runs continue.
      verify: `python3 .claude/hooks/tests/test_structure.py -k headless_runs_continue`
      contract: tests/test_structure.py · test_readme_says_headless_runs_continue · expected RED:
      `AssertionError: "don't stop to flag" not found in …`
- [ ] G7 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 and prints `ok    test_structure`
      and `ok    test_evals`.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of G1–G6's tests; changes nothing observable of its own.
- [ ] G8 Live proof. Prerequisites in Context met; `python3 evals/run.py` under the defaults;
      `brain evals` for the new suite and for `20260902-170309` pasted into `progress.md`; per
      case one line appended to `progress.md`: `<case>: with <old>→<new> — <cause>, evidence
      <transcript path relative to the repo root> "<inline excerpt>"` (`evals/results/` is
      git-ignored, so the excerpt travels with the artifact); exit code recorded and explained:
      1 is expected while any `with` case is below 1.0, 0 if none is, **2 fails G8**
      (`totals.skipped` must be 0); `totals.cost_usd` recorded. The two targeted graders are
      reported explicitly: `csv-export-probe/masterprompt-written` (0/1→?/1, n=1) and
      `executor-refuses-vague/status-line` (2/3→?/3). Any `with` case below 1.0 → a brain
      lesson with the invocation in Context (0 points).
      verify: run the commands; paste the outputs
      contract: no test contract — the check is the live run itself; the install step is
      covered by `./install.sh --check` exit 0.
- [ ] G9 The change moved the number. In the new suite, `masterprompt-written` passes in the
      csv with arm (n=1: evidence, not proof) and `status-line` passes 3/3 in the executor with
      arm. If either does not, G9 is FAILED and the transcript-backed reason is a lesson. One
      rung-2 retry is permitted: a second wording attempt at the site that did not bind, proven
      by a second live suite of the two affected cases only (`--case csv-export-probe`,
      `--case executor-refuses-vague`), budgeted separately; then stop.
      verify: `python3 ~/.claude/hooks/lib/brain.py sql "select case_name, arm, name, sum(passed), count(*) from eval_graders g join eval_runs r on g.run_id = r.id where r.suite = '<the new suite id, e.g. 20260902-181500>' and name in ('masterprompt-written','status-line') group by 1,2,3"`
      contract: n/a — observation of the live suite.

## Risks & early signals
- The csv with arm, now continuing, may exhaust 55 turns or 3 USD before Execute finishes;
  that is fine for G9 (`masterprompt-written` is a file grader) and is graded as exhaustion.
- The executor may still answer in prose one run in three; then G9 fails on that half and the
  lesson names the sentence that did not bind.
- `install.sh` overwrites `~/.claude/skills/gentic*/SKILL.md` and `~/.claude/agents/task-executor.md`;
  if G9 fails and the run stops, the installed workflow carries an edit the suite did not
  confirm — the final report must say so, and `git checkout` of the three files plus
  `./install.sh` reverts it.
- A costly csv arm can make the per-launch ceiling skip `executor-refuses-vague` (fourth of
  five); `totals.skipped > 0` fails G8 and the two targeted cases are re-run as separate suites.

## Task order (for Execute)
1. Contract tests, then the three wording changes — G1, G2, G3.
2. PII pattern + pin; budget-exhaustion subtype — G4, G5.
3. README line — G6; harness — G7.
4. Install, live proof, comparison, lessons — G8, G9.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read): 5 blocking, 12 serious, 9 minor. All fixed inline: needles
as Python literals over lowered text and G6's needle replaced (README already said "headless");
file_exists graders pinned by `path`; the Interview returns to the orchestrator rather than
invoking the next phase; cost estimate marked as not a limit; baseline vs target separated with
sample sizes; the budget subtype marked unverified; the rung-2 retry given its own two-case
suite; a negative PII fixture (G4); Red-flags is a bullet list; G8's exit rule, `skipped == 0`,
lesson invocation with 0 points, comparison-line location and inline excerpt; G7 wording;
non-goals for csv grader count, other docs, `install.sh`, exhaustion fields; baseline-presence
prerequisite and a pre-spend checklist; the skip-ordering risk; the `<new suite>` placeholder
spelled out.
