# Brief: skill-tuning-by-evals

## Mission (as understood)
The suite is trustworthy and it returned two precise change requests about gentic itself.
This run applies them, and only them, then proves the change with the same suite: the with
arm's CSV probe should reach Masterprompt, and the executor should answer in its report block
three times out of three. Two smaller fidelity fixes ride along because the same live run
verifies them: the PII grader becomes symmetric, and a session that exhausts its dollar cap
is graded like one that exhausts its turns.

## Facts
- Brain lesson #11 (suite 20260902-170309, `runs/csv-export-probe-with-0/transcript.jsonl`):
  the headless Interview adopted defaults and wrote `decisions.md`, then the session's final
  message flagged two security defaults "I'll proceed with these defaults unless you say
  otherwise" and ended at turn 23 of 55. Masterprompt was never written.
- `gentic-interview/SKILL.md:37-39`, the non-interactive rule: "do not block. Adopt the brief's
  recommended default … make sure the final report to the user lists every unconfirmed
  default prominently." It never says *continue to the next phase in the same session*, and
  it says nothing about ending the turn. `gentic/SKILL.md` has no autonomous-run section at
  all; only `gentic-execute:33` ("If autonomous: … and continue") and `gentic-masterprompt:58`
  mention autonomy.
- Brain lessons #9 and #12: one run in three, the real `task-executor` answers a spec-less
  assignment in prose questions. `task-executor.md:50-66` says "Your final message is
  consumed by another agent … Be terse and literal" and shows the block, but the rule that
  the block *is* the whole message, even for `blocked` and `assignment unclear`, is not stated.
- Brain lesson #8: `pii-surfaced`'s pattern requires the keyword after `password_hash`; the
  with arm wrote "excluding `password_hash` from the export" and scored 0. Protected in R3.
- The runner treats only `error_max_turns` as exhaustion (`evals/run.py`, `execute_run`). With
  a 3 USD cap and 55 turns, a session can now hit the dollar cap first; the CLI's result
  subtype for that is undocumented here and would be scored as an error today.
- `test_structure.py` holds the contract-test precedent for skill and agent wording
  (`TestFirstSpine`, `BrainWiring`); `test_evals.py::test_definition_graders_are_in_place`
  pins grader patterns per case (agent cases only; the csv case's patterns are not pinned).
- Isolation probes this run (free, no API spend): a throwaway `HOME`, with or without a copy of
  `~/.claude.json`, and a throwaway `CLAUDE_CONFIG_DIR` all end in `Not logged in` — the login
  state is not portable. The without-arm leak channel (the model finding the installed agent
  files with `find ~/.claude/agents`) therefore stays open; it requires guessing the real home
  path once the workspace is outside the repo.
- R3's clean suite: with 0.92 / without 0.35; csv with 3/4 (`masterprompt-written` failed),
  executor with 5/6 (`status-line` failed once).

## Patterns to follow
- Docs and prompts are behaviour: every wording change gets a contract test that fails first
  (`test_structure.py` pattern; CLAUDE.md "Docs and prompts count as behaviour").
- Smallest change: one rule added where the misreading happened, not a rewrite of the skill.
- The suite is the proof; one live run at Iterate, pasted, compared with 20260902-170309.

## Constraints discovered
- The without arm's leak channel cannot be closed without losing the login; out of scope.
- Changing skill wording changes the installed copies via `install.sh`; the live proof must
  run after `./install.sh --check` exits 0.
- Cost: one live suite ≈ 6–8 USD; the csv with arm may now run 55 turns (≈ 2–3 USD, capped at 3).

## Open decisions (all resolved by delegation — see decisions.md)
1. Where the "continue" rule lives — Interview skill only / Interview + orchestrator. Default:
   both: the Interview says it, and `gentic/SKILL.md` gets an "Autonomous runs" section so the
   orchestrator never stops between phases either.
2. Executor wording — a sentence in Output stating the block is the entire final message,
   including for refusals. Default: yes.
3. PII grader — symmetric pattern. Default: yes (a bug, not a loosening; the claim is unchanged).
4. Budget exhaustion — treat `error_max_budget_usd` (and any `error_max_*`) like
   `error_max_turns`. Default: yes.
5. Leak channel — non-goal (probed). Default: as stated.
