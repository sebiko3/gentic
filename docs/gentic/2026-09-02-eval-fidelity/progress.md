# Run: eval-fidelity
Goal: Make the fitness function faithful — keep every transcript, score a max-turns exhaustion on what the session produced instead of zeroing it, rewrite the agent graders to assert what each agent definition adds, run agent cases three times, and give workflow cases a turn budget that lets the five phases finish.
Iteration budget: 10 remaining (3 spent: rung 3 on F10) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions and the turn budget; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 12 minor on draft 1, all fixed inline)
- [x] 4 Execute (5 tasks, 5 checkpoint commits plus one rung-3 commit, every RED cell filled)
- [x] 5 Iterate (9/10 DoD proven; F8 proven in substance, failed to the letter — recorded, not reworded; 10 of 13 points remain)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Transcripts on disk, exhaustion classification, last-message fallback (F1, F2, F3) | 5 | — | `tests/test_evals.py::test_transcript_is_kept_per_run`, `::test_exhausted_run_is_scored_on_its_files`, `::test_last_message_falls_back_to_assistant_text` | `AssertionError: None is not true : transcript.jsonl missing`; `AssertionError: False is not true : file grader failed on an exhausted run: claude exited 1:`; after F1+F2 landed: `AssertionError: False is not true : no match for /nearly there/ in last_message` | done |
| 2 | Brain `exhausted` column (guarded ALTER), record, summary (F4) | 2 | 1 | `::test_brain_exhausted_column_and_summary` | `AssertionError: 'exhausted' not found in ['id', 'ts', 'project', 'suite', 'case_name', 'arm', 'run_index', 'model', 'cost_usd', 'turns', 'is_error', 'skipped']` | done |
| 3 | Per-run cost accumulation, budgets 3, runs 3, 55 turns, parser rule, agent graders/prompts/fixtures (F5, F6) | 5 | 1 | `::test_invocation_flags_per_arm`, `::test_five_cases_are_well_formed`, `::test_money_ceiling_and_exit_codes`, `::test_definition_graders_are_in_place` | `AssertionError: Lists differ: […'--max-budget-usd', '2'…] != […'3'…]`; `AssertionError: 21 != 55`; `AssertionError: 1 != 3` (×4 agent cases); `AssertionError: 3 != 2 : ceiling ignored runs inside a case`; `AssertionError: 'subagent_type": "dod-auditor' != '"subagent_type": "dod-auditor"'` | done |
| 4 | Docs and harness (F7, F8) | 2 | 1-3 | `::test_docs_fidelity_is_documented`; `run.sh` | `AssertionError: 'transcript.jsonl' not found in '# gentic…'`; F8: n/a — runner of the others | done |
| 5 | Live proof, comparison, lessons (F9, F10) | 2 | 4 | n/a — observation of the real system; output pasted here | n/a — the observation is the evidence (below) | done |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–5.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 0 | F1–F7 | — | 0 | PROVEN by `dod-auditor` (fresh `GENTIC_BRAIN`): `-k transcript` 2 OK · `-k exhausted_run` 1 OK · `-k last_message` 1 OK · `-k brain_exhausted` 1 OK + `test_brain` 13 OK · `-k invocation -k five_cases -k money` 3 OK · `-k definition_graders` 1 OK · `-k docs_fidelity` 1 OK |
| 1 | F10 shape graders discriminate (suite 20260902-162750) | 3 | 3 | FAILED: `closing-count` 3/3 and `five-scans` 3/3 in the without arm. Root cause from the transcripts: `init.agents` in the without arm lists `dod-auditor, masterprompt-critic, task-executor, code-reviewer` — the workspace has no `.git`, so the project root resolves to this repo and `--setting-sources project` loads `.claude/agents/`. Redesign within the spec: workspaces move outside any repository; transcripts and stderr are copied into `evals/results/<suite>/`. Then the suite is re-run. |
| 2 | F9, F10 (suite 20260902-170309, after rung 3) | — | 0 | PROVEN — both `brain evals` outputs byte-identical to the paste; `totals` exit 1, skipped 0, cost 6.381; five comparison lines; without-arm shape graders 2/3, 0/3, 0/3. |
| 3 | F8 harness green | — | 0 | `run.sh` exit 0, `all checks passed`, medians 30.9 / 32.6 / 40.1 ms — but `test_evals (Ran 18 tests)`, not the literal `17` the spec pinned before rung 3 added `test_workspaces_live_outside_the_repository`. **Proven in substance, failed to the letter.** The item is not reworded; the divergence is recorded here and in the final report. No rung spent. |

## Notes / handoff
- Child run R3 of the epic `2026-09-02-self-improving-gentic`, re-scoped from "adjective compiler
  and retro" to eval fidelity by R2's three suite-caught lessons (brain #3, #4, #5). The adjective
  compiler and retro move to a later run. Brain consulted first: 5 lessons, 2 notes recalled.
- Rung 3 (F10): `tests/test_evals.py::test_workspaces_live_outside_the_repository` — RED
  `AssertionError: True is not false` (workspace under the evals dir) → GREEN after workspaces
  moved to `tempfile.mkdtemp(prefix="gentic-evals-<suite>-")` and transcripts copied to
  `evals/results/<suite>/runs/<case>-<arm>-<n>/`. The masterprompt's Context still names the old
  workspace path; recorded here rather than edited.

## F9 live proof — suite 20260902-170309 (after rung 3; pasted verbatim)

`./install.sh --check` → `in sync with /Users/sebiko83/.claude`, exit 0.

`python3 evals/run.py` (defaults: both arms, one run for the workflow case, three per agent case, sonnet, 3 / 21 USD; 17:03–17:33):
```
critic-finds-contradiction    with 9/9 (1.00)  without 6/9 (0.67)  delta +0.33  $2.29
csv-export-probe              with 3/4 (0.75)  without 0/4 (0.00)  delta +0.75  $0.56
dod-auditor-false-claim       with 15/15 (1.00)  without 4/15 (0.27)  delta +0.73  $0.81
executor-refuses-vague        with 5/6 (0.83)  without 0/6 (0.00)  delta +0.83  $0.73
reviewer-seeded-defect        with 15/15 (1.00)  without 12/15 (0.80)  delta +0.20  $2.00
suite 20260902-170309       with 0.92  without 0.35  delta +0.57  $6.38  exit 1
below threshold: csv-export-probe, executor-refuses-vague
```
`python3 ~/.claude/hooks/lib/brain.py evals` (latest):
```
suite 20260902-170309
critic-finds-contradiction    with 9/9 (1.00)  without 6/9 (0.67)  delta +0.33  $2.29
csv-export-probe              with 3/4 (0.75)  without 0/4 (0.00)  delta +0.75  $0.56
dod-auditor-false-claim       with 15/15 (1.00)  without 4/15 (0.27)  delta +0.73  $0.81
executor-refuses-vague        with 5/6 (0.83)  without 0/6 (0.00)  delta +0.83  $0.73
reviewer-seeded-defect        with 15/15 (1.00)  without 12/15 (0.80)  delta +0.20  $2.00
suite                       with 0.92  without 0.35  delta +0.57
```
`python3 ~/.claude/hooks/lib/brain.py evals --suite 20260902-125057` (R2):
```
suite 20260902-125057
critic-finds-contradiction    with 2/2 (1.00)  without 2/2 (1.00)  delta +0.00  $0.97
csv-export-probe              with 0/3 (0.00)  without 1/3 (0.33)  delta -0.33  $0.95
dod-auditor-false-claim       with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.33
executor-refuses-vague        with 1/2 (0.50)  without 2/2 (1.00)  delta -0.50  $0.36
reviewer-seeded-defect        with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.43
suite                       with 0.70  without 0.87  delta -0.17
```
Exit 1 matches the numbers: no run skipped; two `with` cases below 1.0. `result.json`: `totals.cost_usd` 6.381 ≤ 21,
`skipped` 0, every run scored, none exhausted, workspaces under `/var/folders/…/gentic-evals-20260902-170309-…/workspaces`.
An intermediate suite `20260902-162750` (before rung 3, workspaces still inside the repo) scored with 0.83 /
without 0.77 and is kept in the brain as the contaminated baseline.

**Per-case comparison** (R2 → this suite, with arm; evidence under `evals/results/20260902-170309/runs/`):
- critic-finds-contradiction: with 1.00→1.00 — unchanged; the with arm dispatches the real agent every run, evidence `critic-finds-contradiction-with-0/transcript.jsonl`.
- csv-export-probe: with 0.00→0.75 — exhaustion no longer scores 0 and the Interview now adopts defaults headlessly (brief, decisions, scout gate commit); the remaining failure is `masterprompt-written`: the session stops at turn 23 to "flag" two security defaults "unless you say otherwise" instead of continuing, evidence `csv-export-probe-with-0/transcript.jsonl` (final message).
- dod-auditor-false-claim: with 1.00→1.00 — the real auditor emits the verdict table, UNVERIFIABLE for D3 and the closing count in all three runs, evidence `dod-auditor-false-claim-with-0/transcript.jsonl`.
- executor-refuses-vague: with 0.50→0.83 — two of three runs print `status: assignment unclear`; run 0 answers in prose questions without the report block its definition mandates, evidence `executor-refuses-vague-with-0/transcript.jsonl`.
- reviewer-seeded-defect: with 1.00→1.00 — `confidence <n>` lines and the `Not reported` count present in all three runs, evidence `reviewer-seeded-defect-with-0/transcript.jsonl`.

## F10 — shape graders in suite 20260902-170309
```
critic-finds-contradiction   without  five-scans     2/3
dod-auditor-false-claim      without  closing-count  0/3
executor-refuses-vague       without  status-line    0/3
```
All three below 1.0 in the without arm → PROVEN. The two without-arm `five-scans` passes have a
cause worth knowing: the Task dispatch failed (`Agent type 'masterprompt-critic' not found`), so the
model ran `find ~/.claude/agents`, read the installed definition, and impersonated it through a
general-purpose agent (evidence `critic-finds-contradiction-without-0/transcript.jsonl`). The
without arm lacks the machinery but not the files; `used-the-agent` therefore measures an attempt.
Both recorded as brain notes for the next eval run.

## Final report

**Mission.** The fitness number can be trusted. Every eval run leaves `transcript.jsonl` and
`stderr.txt` under `evals/results/<suite>/runs/`; a session that hits its turn limit is graded
on what it produced; the four agent cases assert the shapes their definitions promise and run
three times; the workflow case has 55 turns and a 3 USD cap; and, from a rung-3 finding, eval
workspaces live outside any repository so the without arm cannot inherit this repo's agents.

**The number.** Suite `20260902-170309`: with gentic **0.92**, without **0.35**, delta **+0.57**,
6.38 USD, exit 1. R2's suite read 0.70 / 0.87 / −0.17; the intermediate suite before rung 3
(workspaces inside the repo, without arm contaminated) read 0.83 / 0.77. All three are in the
brain. Per-case: every agent case is 1.00 with gentic except the executor (0.83); the workflow
case rose from 0.00 to 0.75.

**DoD: 9 of 10 proven, F8 proven in substance.** `run.sh` is green with 18 eval tests where the
spec, written before rung 3, pinned 17. Not reworded. Budget: 10 of 13 remaining (rung 3 on F10).

**What the fitness function found, for the runs after this one** (all brain lessons/notes):
1. `gentic-interview`/`gentic` headless: the non-interactive rule is applied at the Interview,
   but the session then *stops to flag* security defaults "unless you say otherwise" instead of
   continuing to Masterprompt (23 turns of 55 used). The rule needs "adopt, flag in the report,
   continue — never stop to wait". A skill change, measured by this suite.
2. `task-executor` answers a spec-less assignment in prose one run in three; its definition
   mandates the `status:` report block. A definition change, measured by `status-line`.
3. The without arm lacks the harness's agents (Task returns "not found") but not the files: the
   model found `~/.claude/agents/*.md` with `find`, read one, and impersonated it. A clean
   without arm needs a temp `HOME`/`CLAUDE_CONFIG_DIR`; `used-the-agent` measures an attempt
   and wants a `tool_result` grader type.
4. `pii-surfaced` is order-sensitive (keyword must follow `password_hash`); a protected pattern,
   unchanged here, symmetric in the next eval run.

**Spent.** 6.59 USD (intermediate suite) + 6.38 USD (clean suite) + 0.03 USD (max-turns probe).

**Unconfirmed defaults** (all `user — delegated`; the turn budget explicitly): 55 turns and 3 USD
per run; exhausted runs graded; transcripts raw and unscrubbed; shape graders and exact
`subagent_type` matching; `runs: 3` for agent cases; `eval_runs.exhausted` via guarded ALTER;
workspaces in the system temp directory (rung 3).

**Deviations recorded, not hidden.** F8's literal count (17 vs 18). The masterprompt's Context
names `evals/results/<suite>/workspaces/` as the workspace location; rung 3 moved workspaces to
`tempfile.mkdtemp` and transcripts to `results/<suite>/runs/`; F1 holds by its own text.

**Deliberately not done.** No skill or agent edited; no HOME isolation for the without arm; no
`tool_result` grader; no compare flag; no scrubbing; no CI; no adjective compiler, no retro.

**Branch.** `gentic/self-improving-gentic`, nine `gentic(eval-fidelity)` commits; kept as-is for `/ship`.
