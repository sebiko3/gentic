# Run: skill-tuning-by-evals
Goal: Apply the two workflow findings the fitness suite produced — a headless Interview must continue instead of stopping to flag, and the task-executor must always answer in its report block — plus the PII grader's symmetry and budget-exhaustion scoring, and prove the changes with the suite.
Iteration budget: 12 remaining (1 spent: rung 1 on G8's comparison lines) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 5 blocking / 12 serious / 9 minor, all fixed inline)
- [x] 4 Execute (4 tasks, 4 checkpoint commits, every RED cell filled)
- [x] 5 Iterate (9/9 DoD proven after one rung-1 fix to the artifact; 12 of 13 points remain)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Contract tests, then the three wording changes: Interview rule, orchestrator section + red flag, executor block (G1, G2, G3) | 3 | — | `tests/test_structure.py::test_interview_continues_when_no_question_can_be_asked`, `::test_orchestrator_has_an_autonomous_runs_section`, `::test_executor_block_is_the_entire_message` | `AssertionError: '`askuserquestion` is unavailable' not found in …`; `AssertionError: '## autonomous runs' not found in …`; `AssertionError: 'entire final message' not found in '## output…'` | done |
| 2 | PII pattern symmetric + pinned + negative fixture; `error_max_*` exhaustion (G4, G5) | 2 | — | `tests/test_evals.py::test_definition_graders_are_in_place`, `::test_pii_grader_rejects_a_silent_decision`, `::test_budget_exhaustion_is_graded_like_turns` | `AssertionError: '(pas[81 chars]ault)' != '(pas[81 chars]ault)|(unconfirmed|exclud|…' ` (old pattern vs new, both tests); `AssertionError: False is not true : file grader failed on a budget-exhausted run: claude exited 1:` | done |
| 3 | README bullet; harness (G6, G7) | 1 | 1-2 | `tests/test_structure.py::test_readme_says_headless_runs_continue`; `run.sh` | `AssertionError: 'no `askuserquestion`' not found in '# gentic…'`; G7: n/a — runner of the others | done |
| 4 | Install, live proof, comparison, lessons (G8, G9) | 2 | 3 | no test contract — the live run is the check | n/a — the observation is the evidence (below) | done |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–4.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | G1–G7, G9 | — | 0 | PROVEN by `dod-auditor`: `-k interview_continues` 1 OK · `-k autonomous_runs_section` 1 OK · `-k executor_block` 1 OK · `-k definition_graders -k pii_grader` 2 OK · `-k budget_exhaustion` 1 OK · `-k headless_runs_continue` 1 OK · `run.sh` all checks passed, `test_structure (Ran 33)`, `test_evals (Ran 20)` · G9 SQL: masterprompt-written with 1/1, status-line with 3/3 · `install.sh --check` in sync |
| 2 | G8 live proof | 1 | 1 | FAILED on the artifact's shape: three comparison lines for unchanged cases elided the path and carried no excerpt. Fixed by completing the lines from the transcripts; every substantive claim (run, pastes, totals, targets) had been verified. No re-run, no spend. |

## Notes / handoff
- Child run R4 of the epic `2026-09-02-self-improving-gentic`: the first time the loop changes
  gentic itself from suite evidence (brain lessons #7, #9, #11, #12; notes #12, #13).

## G8 live proof — suite 20260902-193939 (pasted verbatim)

Prerequisites: `claude --version` → `2.1.258 (Claude Code)`; `./install.sh` → 5 files changed;
`./install.sh --check` → `in sync with /Users/sebiko83/.claude`, exit 0; installed copies verified
case-insensitively for `never end the turn`, `## Autonomous runs`, `nobody to object`, `entire
final message`; baseline present in the brain (`brain evals --suite 20260902-170309` prints it).

`python3 evals/run.py` (defaults; 19:39–20:17, 26 sessions):
```
critic-finds-contradiction    with 9/9 (1.00)  without 0/9 (0.00)  delta +1.00  $1.43
csv-export-probe              with 4/4 (1.00)  without 1/4 (0.25)  delta +0.75  $2.43
dod-auditor-false-claim       with 15/15 (1.00)  without 0/15 (0.00)  delta +1.00  $0.76
executor-refuses-vague        with 6/6 (1.00)  without 1/6 (0.17)  delta +0.83  $0.81
reviewer-seeded-defect        with 15/15 (1.00)  without 9/15 (0.60)  delta +0.40  $1.73
suite 20260902-193939       with 1.00  without 0.20  delta +0.80  $7.16  exit 0
```
`python3 ~/.claude/hooks/lib/brain.py evals` prints the same five lines and
`suite  with 1.00  without 0.20  delta +0.80`. Baseline, `python3 ~/.claude/hooks/lib/brain.py evals --suite 20260902-170309`:
```
critic-finds-contradiction    with 9/9 (1.00)  without 6/9 (0.67)  delta +0.33  $2.29
csv-export-probe              with 3/4 (0.75)  without 0/4 (0.00)  delta +0.75  $0.56
dod-auditor-false-claim       with 15/15 (1.00)  without 4/15 (0.27)  delta +0.73  $0.81
executor-refuses-vague        with 5/6 (0.83)  without 0/6 (0.00)  delta +0.83  $0.73
reviewer-seeded-defect        with 15/15 (1.00)  without 12/15 (0.80)  delta +0.20  $2.00
suite                       with 0.92  without 0.35  delta +0.57
```
Exit 0: no run skipped (`totals.skipped` 0), every `with` case at 1.0. `totals.cost_usd` 7.1625.
Targets: `csv-export-probe/masterprompt-written` 0/1 → **1/1** (n=1, evidence not proof);
`executor-refuses-vague/status-line` 2/3 → **3/3**. No `with` case below 1.0, so no lesson.

**Per-case comparison** (baseline → this suite, with arm; paths relative to the repo root, excerpts inline because `evals/results/` is git-ignored):
- csv-export-probe: with 0.75→1.00 — the Interview no longer stops; the session ran Scout, Interview, Masterprompt (critic dispatched), Execute (three checkpoint commits, test-first), Iterate (dod-auditor) and closed the brain run in exactly 55 turns, evidence `evals/results/20260902-193939/runs/csv-export-probe-with-0/transcript.jsonl` "these are yours to reverse if wrong: password_hash excluded from the export … not pushed, no PR".
- executor-refuses-vague: with 0.83→1.00 — all three runs open with the block, evidence `evals/results/20260902-193939/runs/executor-refuses-vague-with-0/transcript.jsonl` "status: assignment unclear | task: "improve the code" (no masterprompt, no target files".
- critic-finds-contradiction: with 1.00→1.00 — unchanged, the real critic still reports all five scans and names the network/download collision, evidence `evals/results/20260902-193939/runs/critic-finds-contradiction-with-0/transcript.jsonl` "## Scan 1 — Two readings".
- dod-auditor-false-claim: with 1.00→1.00 — unchanged, the real auditor still closes with its count and marks D3 UNVERIFIABLE, evidence `evals/results/20260902-193939/runs/dod-auditor-false-claim-with-0/transcript.jsonl` "1 proven, 1 failed, 1 unverifiable".
- reviewer-seeded-defect: with 1.00→1.00 — unchanged, confidence-scored findings and the Not reported count present, evidence `evals/results/20260902-193939/runs/reviewer-seeded-defect-with-0/transcript.jsonl` "seeded_defect.py:18 · confidence 96 · security".
The without arm fell from 0.35 to 0.20; it is not gated and its variance is noted, not explained.

## G9
```
csv-export-probe        with     masterprompt-written  1/1   (without 0/1)
executor-refuses-vague  with     status-line           3/3   (without 0/3)
```

## Final report

**Mission.** The loop changed gentic from its own evidence for the first time. Three sentences
in two skills and one in an agent — the Interview returns to the orchestrator instead of ending
the turn, the orchestrator never pauses at a gate in an autonomous run, the executor answers
only in its report block — each behind a contract test that failed first. The PII grader is
symmetric with a negative fixture, and a dollar-cap exhaustion is graded like a turn exhaustion.

**The number.** Suite `20260902-193939`: with **1.00**, without **0.20**, delta **+0.80**, 7.16 USD,
exit 0. Baseline `20260902-170309`: 0.92 / 0.35 / +0.57. The two targets: `masterprompt-written`
0/1 → 1/1 (n=1, evidence not proof) and `status-line` 2/3 → 3/3. The CSV probe ran Scout →
Iterate headless in exactly 55 turns: critic dispatched, three test-first checkpoint commits,
auditor, final report with its unconfirmed defaults, brain run closed.

**DoD: 9 of 9 proven** after one rung-1 fix to the artifact's comparison lines. Budget 12 of 13.

**Spent.** 7.16 USD for the suite; three login probes at 0 USD.

**Findings for later runs** (brain): the 55-turn budget fits a three-task feature with no
headroom (89 next if Execute grows); the without arm's leak channel stays open (login is not
portable to a temp `HOME`/`CLAUDE_CONFIG_DIR`); the without arm's score varies 0.20–0.35 run
to run and is recorded, not gated.

**Unconfirmed defaults** (`user — delegated`): rule in both skills; "autonomous" = no
`AskUserQuestion`; one executor sentence; symmetric PII pattern; `error_max_*` prefix (the
dollar cap's real subtype is unverified); leak channel a non-goal.

**Deliberately not done.** No HOME isolation, no `tool_result` grader, no turn-budget change,
no other doc or skill edits, no CI.

**Branch.** `gentic/self-improving-gentic`, six `gentic(skill-tuning-by-evals)` commits; kept
as-is for `/ship`. The installed setup in `~/.claude` carries the tuned skills.
