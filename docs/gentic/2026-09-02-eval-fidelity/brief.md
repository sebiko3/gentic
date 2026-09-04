# Brief: eval-fidelity

## Mission (as understood)
R2 built the fitness function and its first number said gentic scores below no-gentic. R2's
own diagnosis says the number is not yet trustworthy: the workflow case was cut off by a turn
limit and then scored as if nothing existed, the agent cases pass for a built-in agent as well
as for the real one, and no transcript survived to say what the agents actually replied. This
run makes the number faithful before anyone acts on it: transcripts are kept, an exhausted
session is scored on what it produced, the agent graders assert the shape each agent
definition promises, agent cases run three times, and workflow cases get a turn budget that
lets Scout → Iterate finish. Then the suite runs again and the two suites are compared.

## Facts
- R2's suite `20260902-125057` (brain `eval_runs`): `csv-export-probe` with arm used 22 turns
  (limit 21) for Scout and Interview only, cost 0.55 USD; the without arm shipped code in 15
  turns for 0.40 USD. Agent cases used 2–3 turns and 0.13–0.55 USD each.
- A max-turns exhaustion is reported by `claude -p` as a `result` message with
  `subtype: "error_max_turns"`, `is_error: true`, `result: null`, `stop_reason: "tool_use"`, and
  process exit 1 (verified: one-turn Haiku session, 0.03 USD). The files it created and the
  tool uses it made are in the transcript regardless.
- `evals/run.py` today: `parse_transcript` keeps only `result.result` as the last message; an
  exit-1 run gets `_error = "claude exited 1: …"` and `grade()` fails every grader with that
  detail; stdout is never written to disk (`execute_run`, lines ~200-240).
- The without arm loads no user agents (`init.agents` = `claude, claude-code-guide, Explore,
  general-purpose, Plan, statusline-setup`; R2 diagnostic), yet R2's cases 2, 3 and 5 passed
  there: the graders match vocabulary the prompt itself induces.
- What each agent definition promises that a built-in agent does not produce:
  `dod-auditor` — a verdict table with `PROVEN | FAILED | UNVERIFIABLE`, a per-failure block,
  and a closing line `<n> proven, <n> failed, <n> unverifiable` (`.claude/agents/dod-auditor.md:54-68`);
  `masterprompt-critic` — five named scans, Two readings / Contradiction / Unverifiable DoD /
  Missing non-goal / Unstated assumption, reported even when clean (`masterprompt-critic.md:28-40`);
  `task-executor` — a fixed report block whose first line is `status: done | blocked |
  assignment unclear` (`task-executor.md:55`);
  `code-reviewer` — per finding `confidence <n>` and a closing **Not reported** count
  (`code-reviewer.md:75-82`).
- `tool_used` matches `input_match` over `json.dumps(input, sort_keys=True)`, so
  `"subagent_type": "dod-auditor"` is a stricter match than the bare name R2 used.
- R2's `test_five_cases_are_well_formed` pins `max_turns` 21/8 and the invocation test pins
  `--max-budget-usd 2`; both are contracts to change, test-first, when the numbers change.
- `eval_runs` has no column for exhaustion; the brain has no schema migrations (R1 non-goal).
  SQLite's `ALTER TABLE … ADD COLUMN` is idempotent when guarded by a `PRAGMA table_info` check.
- The hooks harness and `test_evals.py` (11 tests) are green; the fake `claude` replays any
  transcript, so exhaustion is testable offline by replaying an `error_max_turns` result with
  `FAKE_CLAUDE_EXIT=1`.

## Patterns to follow
- Everything offline through the fake `claude`; one live suite at Iterate (R2's shape).
- Contract tests over the case files for grader shape (R2's `test_five_cases_are_well_formed`).
- Fibonacci: turn budget 55, per-run cap 3 USD, suite ceiling 21, agent runs 3.
- Never loosen a case to pass; a `with` case below 1.0 is a lesson (R2 non-goal, kept).

## Constraints discovered
- Cost of the live proof: 4 agent cases × 2 arms × 3 runs ≈ 24 sessions at 0.15–0.55 USD, plus
  the workflow case at up to 3 USD per arm — roughly 10–14 USD, inside the 21 ceiling. Runs are
  sequential; wall clock ≈ 25–40 minutes.
- The turn budget is a user-delegated decision: 55 turns for workflow cases. R2 measured 22
  for two phases; Masterprompt with a critic dispatch, Execute with tests, and Iterate with an
  auditor plausibly need 40–50 more turns than 21. If 55 is still exhausted, that is the next
  lesson, not a reason to raise it in this run.
- Score semantics stay as R2 defined them (run score = passed ÷ total graders); only *which
  runs get graded* changes: exhausted runs are graded, errored runs are still 0.

## Open decisions (all resolved by delegation — see decisions.md)
1. Turn budget for workflow cases — 34 / 55 / 89. Default: **55**, with the per-run cap raised
   to 3 USD so the budget is reachable.
2. Exhausted-run scoring — grade on files, tools and the last assistant text vs. keep 0.
   Default: grade; mark `exhausted` separately from `is_error`.
3. Agent graders — assert the definitions' output shapes (table, five scans, status line,
   confidence + Not reported) and match `"subagent_type"` exactly. Default: yes.
4. Runs per agent case — 3 (frontmatter), workflow case 1. Default: as stated.
5. Brain column — add `exhausted` to `eval_runs` via a guarded ALTER. Default: yes.
