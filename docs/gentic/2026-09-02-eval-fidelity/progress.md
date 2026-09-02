# Run: eval-fidelity
Goal: Make the fitness function faithful — keep every transcript, score a max-turns exhaustion on what the session produced instead of zeroing it, rewrite the agent graders to assert what each agent definition adds, run agent cases three times, and give workflow cases a turn budget that lets the five phases finish.
Iteration budget: 10 remaining (3 spent: rung 3 on F10) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions and the turn budget; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 12 minor on draft 1, all fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Transcripts on disk, exhaustion classification, last-message fallback (F1, F2, F3) | 5 | — | `tests/test_evals.py::test_transcript_is_kept_per_run`, `::test_exhausted_run_is_scored_on_its_files`, `::test_last_message_falls_back_to_assistant_text` | `AssertionError: None is not true : transcript.jsonl missing`; `AssertionError: False is not true : file grader failed on an exhausted run: claude exited 1:`; after F1+F2 landed: `AssertionError: False is not true : no match for /nearly there/ in last_message` | done |
| 2 | Brain `exhausted` column (guarded ALTER), record, summary (F4) | 2 | 1 | `::test_brain_exhausted_column_and_summary` | `AssertionError: 'exhausted' not found in ['id', 'ts', 'project', 'suite', 'case_name', 'arm', 'run_index', 'model', 'cost_usd', 'turns', 'is_error', 'skipped']` | done |
| 3 | Per-run cost accumulation, budgets 3, runs 3, 55 turns, parser rule, agent graders/prompts/fixtures (F5, F6) | 5 | 1 | `::test_invocation_flags_per_arm`, `::test_five_cases_are_well_formed`, `::test_money_ceiling_and_exit_codes`, `::test_definition_graders_are_in_place` | `AssertionError: Lists differ: […'--max-budget-usd', '2'…] != […'3'…]`; `AssertionError: 21 != 55`; `AssertionError: 1 != 3` (×4 agent cases); `AssertionError: 3 != 2 : ceiling ignored runs inside a case`; `AssertionError: 'subagent_type": "dod-auditor' != '"subagent_type": "dod-auditor"'` | done |
| 4 | Docs and harness (F7, F8) | 2 | 1-3 | `::test_docs_fidelity_is_documented`; `run.sh` | `AssertionError: 'transcript.jsonl' not found in '# gentic…'`; F8: n/a — runner of the others | done |
| 5 | Live proof, comparison, lessons (F9, F10) | 2 | 4 | n/a — observation of the real system; output pasted here | | pending |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–5.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | F10 shape graders discriminate (suite 20260902-162750) | 3 | 3 | FAILED: `closing-count` 3/3 and `five-scans` 3/3 in the without arm. Root cause from the transcripts: `init.agents` in the without arm lists `dod-auditor, masterprompt-critic, task-executor, code-reviewer` — the workspace has no `.git`, so the project root resolves to this repo and `--setting-sources project` loads `.claude/agents/`. Redesign within the spec: workspaces move outside any repository; transcripts and stderr are copied into `evals/results/<suite>/`. Then the suite is re-run. |

## Notes / handoff
- Child run R3 of the epic `2026-09-02-self-improving-gentic`, re-scoped from "adjective compiler
  and retro" to eval fidelity by R2's three suite-caught lessons (brain #3, #4, #5). The adjective
  compiler and retro move to a later run. Brain consulted first: 5 lessons, 2 notes recalled.
- Rung 3 (F10): `tests/test_evals.py::test_workspaces_live_outside_the_repository` — RED
  `AssertionError: True is not false` (workspace under the evals dir) → GREEN after workspaces
  moved to `tempfile.mkdtemp(prefix="gentic-evals-<suite>-")` and transcripts copied to
  `evals/results/<suite>/runs/<case>-<arm>-<n>/`. The masterprompt's Context still names the old
  workspace path; recorded here rather than edited.
