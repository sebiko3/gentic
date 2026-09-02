# Run: gentic-evals
Goal: A fitness function for gentic — an eval suite in the official plugin-eval case layout, run headlessly with and without gentic, graded deterministically, scored into the brain; plus an agent fixture bank as eval cases and UI test runners counted as verification evidence.
Iteration budget: 13 of 13 remaining — no escalation rung was spent.

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 6 blocking / 21 serious / 12 minor on draft 1, all fixed inline)
- [x] 4 Execute (9 tasks, 9 checkpoint commits, every RED cell filled)
- [x] 5 Iterate (13/13 DoD proven by dod-auditor; 13 of 13 points remain)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Runner skeleton: flat parser, discovery, argv, preflight, `--dry-run`; fake-`claude` test harness (E0, E1) | 5 | — | `tests/test_evals.py::test_preflight_refuses_a_missing_flag`, `::test_dry_run_lists_cases_and_argv` | `AssertionError: 2 != 1 : runner did not refuse`; `AssertionError: 2 != 0 : runner did not run: … can't open file '…/evals/run.py'` | done |
| 2 | Invocation and per-run workspaces, `GENTIC_BRAIN` redirection (E2) | 2 | 1 | `::test_invocation_flags_per_arm` | `AssertionError: [] is not true : claude was never invoked` | done |
| 3 | Graders, created-file snapshot, scaffold, timeout (E3, E4) | 5 | 2 | `::test_graders_score_a_replayed_transcript`, `::test_scaffold_runs_first_and_is_not_created` | `AssertionError: 0 != 6 : graders were not evaluated`; `AssertionError: 'fixture.txt' not found in [] : scaffold did not run before claude` | done |
| 4 | Brain `eval_runs`/`eval_graders`, record functions, `brain evals`, runner integration, `--no-brain` (E5) | 3 | 2 | `::test_brain_rows_and_evals_summary` | `AssertionError: 0 != 2 : no eval_runs rows in brain` | done |
| 5 | Money ceiling, order, exit codes, `result.json` totals (E6) | 2 | 3 | `::test_money_ceiling_and_exit_codes` | `AssertionError: 0 != 2 : suite ceiling did not stop the third run` | done |
| 6 | The five cases, fixtures, scaffolds, manifest, gitignore (E7, E12) | 5 | 3 | `::test_five_cases_are_well_formed`, `::test_manifest_and_gitignore` | `AssertionError: Lists differ: [] != ['critic-finds-contradiction', 'csv-export…']`; `AssertionError: False is not true : .claude-plugin/plugin.json missing` | done |
| 7 | Verification regex gains the UI runners (E8) | 1 | — | `tests/test_tdd.py::test_ui_test_runners_are_verification_commands` | `AssertionError: [] == [] : npx run was not recorded as evidence` (×4 runners) and `… a failing playwright run was not recorded as RED` | done |
| 8 | Harness registration and docs (E10, E11) | 2 | 1-7 | `::test_harness_registers_evals_offline`, `::test_docs_evals_are_documented` | `AssertionError: 'test_evals' not found in 'for suite in …'`; `AssertionError: '## The fitness function' not found in '# gentic…'` | done |
| 9 | Live proof: install check, real suite run, `brain evals`, lessons for failures (E9) | 2 | 8 | n/a — observation of the real system; output pasted here | n/a — the observation is the evidence (below) | done |

Sizes are planning estimates only; they never spend the iteration budget. Order: 1-9 as listed (runner first, cases once the runner can grade them, live proof last).

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | E0–E8, E10–E12 | — | 0 | PROVEN by `dod-auditor` (fresh `GENTIC_BRAIN`): `-k preflight` 1 OK · `-k dry_run` 1 OK · `-k invocation` 1 OK · `-k graders` 1 OK · `-k scaffold` 1 OK · `-k brain_rows` 1 OK + `test_brain` 13 OK · `-k money` 1 OK · `-k five_cases` 1 OK · `test_tdd -k ui_test_runners` 1 OK · `run.sh` all checks passed, `test_evals (Ran 11 tests)`, medians 23.5 / 24.2 / 29.4 ms, `evals/run.py` absent from `run.sh` · `-k docs_evals` 1 OK · `-k manifest` 1 OK |
| 2 | E9 live proof | — | 0 | PROVEN — pasted console equals `brain evals` line for line; `result.json` totals exit 1, skipped 0; both below-1.0 `with` cases have `caught_by suite` lessons; install check in sync. The number is negative (delta −0.17); E9 required it to be real and consistent, not favourable. |

## Notes / handoff
- Child run R2 of the epic `2026-09-02-self-improving-gentic`. Brain consulted first (2 lessons,
  1 note recalled); three scouting facts noted into the brain under run `gentic-evals`.
- Plan drift (Execute, task 9 preparation): the real `claude --help` (2.1.258) does not list
  `--max-turns`, though the flag is accepted (smoke run: `num_turns: 1`), and the CLI ignores
  unknown flags with `--version` (a bogus flag exits 0), so no acceptance probe exists. Preflight
  keeps the help check for the other eight flags and exempts `--max-turns` with that evidence in
  a comment; the E0 contract (refuse on a missing `--no-session-persistence`) is unchanged.

## E9 live proof — suite 20260902-125057 (pasted verbatim)

`./install.sh --check` → `in sync with /Users/sebiko83/.claude`, exit 0.

`python3 evals/run.py` (defaults: both arms, one run, sonnet, budgets 2 / 21 USD; 12:50–13:05):
```
critic-finds-contradiction    with 2/2 (1.00)  without 2/2 (1.00)  delta +0.00  $0.97
csv-export-probe              with 0/3 (0.00)  without 1/3 (0.33)  delta -0.33  $0.95
dod-auditor-false-claim       with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.33
executor-refuses-vague        with 1/2 (0.50)  without 2/2 (1.00)  delta -0.50  $0.36
reviewer-seeded-defect        with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.43
suite 20260902-125057       with 0.70  without 0.87  delta -0.17  $3.04  exit 1
below threshold: csv-export-probe, executor-refuses-vague
```
`python3 .claude/hooks/lib/brain.py evals` prints the same five lines and `suite  with 0.70  without 0.87  delta -0.17`.
Exit code 1 matches the numbers: no run skipped, two `with` cases below 1.0. Every case scored;
none unscorable. `result.json`: `claude_version 2.1.258`, `install_in_sync true`, `warnings []`.

**What the number says.** gentic, as installed today, scores *lower* than no gentic on this
suite. Three diagnoses, each a brain lesson (`caught_by suite`):
1. `csv-export-probe` with arm: gentic ran — `brief.md`, `decisions.md`, Scout and Interview
   gate commits exist in the workspace — and consumed all 21 turns before Masterprompt; the CLI
   exited 1 at max turns and the runner scored the errored run 0 although `brief.md` exists.
   Two findings: the five phases cost more than 21 headless turns before any code, and
   scoring an errored run 0 hides file evidence (a spec decision for R3 to revisit).
2. `executor-refuses-vague` with arm: the real `task-executor` did not say `assignment
   unclear` or `blocked`; the without arm's built-in agent did. One run each, so noise is
   possible; the transcript was not saved, so the actual reply is unknown.
3. Cases 2, 3 and 5 do not discriminate: the without arm loads no user agents (verified with a
   one-turn diagnostic session, 0.02 USD: `init.agents` lists only built-ins) yet a
   general-purpose subagent told to audit, critique or review emits PROVEN/FAILED, names the
   contradiction and finds both seeded defects. The graders assert vocabulary the prompt
   already induces, not what the agent definition adds.
Per the non-goals nothing in the skills, agents or cases was changed to move the number.

`python3 .claude/hooks/lib/brain.py evals` (verbatim, at the gate):
```
suite 20260902-125057
critic-finds-contradiction    with 2/2 (1.00)  without 2/2 (1.00)  delta +0.00  $0.97
csv-export-probe              with 0/3 (0.00)  without 1/3 (0.33)  delta -0.33  $0.95
dod-auditor-false-claim       with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.33
executor-refuses-vague        with 1/2 (0.50)  without 2/2 (1.00)  delta -0.50  $0.36
reviewer-seeded-defect        with 3/3 (1.00)  without 3/3 (1.00)  delta +0.00  $0.43
suite                       with 0.70  without 0.87  delta -0.17
```

## Final report

**Mission.** gentic can be scored. `python3 evals/run.py` runs five cases headlessly with and
without the installed setup, grades them deterministically, prints per-case pass rates and
deltas, writes `result.json`, and records every run and grader into the brain next to the
sha256 stamps of the installed skills and agents. Playwright, Cypress, Lighthouse and axe now
count as verification evidence. The offline harness proves the runner through a fake `claude`;
one real run proved the number.

**13 of 13 DoD items proven** (iteration log). Budget 13 of 13. Nine tasks, each RED first.

**The headline finding.** The first score is 0.70 with gentic against 0.87 without. Three
causes, all recorded as brain lessons and none patched over: the five phases cost more than 21
headless turns before any code (the with-arm CSV probe wrote a brief and decisions, committed
two gates, then hit the turn limit); a max-turns exit is scored as an error, hiding file
evidence; and the three agent cases assert vocabulary a built-in agent also produces, so they
do not measure what the agent definitions add. The runner also kept no transcripts, so the
executor's refusal wording could not be checked. These are R3's brief, not this run's rungs.

**Spent.** 3.04 USD for the suite, 0.02 USD for one diagnostic session, plus the offline suite
at zero.

**Unconfirmed defaults** (all `user — delegated`): home-grown runner; three grader types;
`--setting-sources project` as the without arm; sonnet; budgets 2/21; scores in two brain
tables; agent tests as cases; four-key manifest; `--max-turns` exempted from the help-text
preflight (Context/implementation drift, recorded above).

**Deviation recorded.** The masterprompt Context still lists `--max-turns` among the flags
preflight must find in `claude --help`; the code exempts it with the evidence in a comment.
E0's contract is unaffected. Not edited into the spec, per the rule.

**Deliberately not done.** No `llm` graders, no CI, no scheduled runs, no changes to skills,
agents or cases to move the score, no transcripts saved (lesson), no parallelism, no HTML.

**Branch.** `gentic/self-improving-gentic`, ten `gentic(gentic-evals)` commits; kept as-is for
`/ship`.
