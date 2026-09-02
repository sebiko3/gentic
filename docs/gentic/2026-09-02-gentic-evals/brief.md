# Brief: gentic-evals

## Mission (as understood)
Give gentic a number. Today the claim that gentic changes an agent's behaviour rests on one
probe from August; nothing measures whether a change to a skill, hook or agent makes the
workflow better or worse. This run builds the fitness function: eval cases written in the
official `claude plugin eval` layout, executed headlessly by a runner of our own (because the
official command is early-access and disabled here), each case run twice — with gentic's
setup and without it — graded deterministically, with every score landing in the brain next
to the skill versions it was measured against. The four agents get their behavioural tests
the same way: a planted false claim, a planted contradiction, a vague assignment and the
existing seeded defect become eval cases. Finally, Playwright, Cypress, Lighthouse and axe
runs start counting as verification evidence, the gap R1's brief found.

## Facts
- `claude plugin eval` exists in 2.1.258 with the full option set (`--ablation with-without`,
  `--max-cost-usd`, `--judge-model`, `--json`, `--threshold`, `--runs`, `--tag`, `--no-publish`),
  but running it prints `plugin eval is currently in early access` and exits 0 having done
  nothing (verified in a temp dir). Enablement is per organisation; no public docs page.
- Its case layout (from the platform reference, via `claude-code-guide`): `evals/<case>/prompt.md`
  with frontmatter `name, tags, runs (3), max_turns (10), timeout_seconds (300), allowed_tools,
  model, append_system_prompt, env (EVAL_* only)`; optional `case.yaml` with
  `context.scaffold_script`, `context.add_dirs`, `context.history_file`; graders as
  `graders/*.md` with frontmatter `type: regex|tool_used|tool_order|file_exists|llm|baseline`.
  `regex` takes `pattern, flags, match: contains|not_contains, target: last_message|trace|files`;
  `tool_used` takes `tool, input_match, min, max`; `file_exists` takes a glob over files the
  agent *created*. A case passes when all graders pass; the suite passes at `--threshold` (1.0).
- Headless runs work: `claude -p "<prompt>" --output-format json --max-turns 1` returned a JSON
  array (a `system/init` message carrying `slash_commands` and `tools`, then a `result` with
  `result`, `total_cost_usd`, `num_turns`, `is_error`). One-turn Haiku cost 0.03 USD.
  `--output-format stream-json --verbose` yields per-message `tool_use` blocks.
- **The ablation arm exists natively:** `claude -p … --setting-sources project` loads none of
  the user's skills or hooks (gentic absent from `slash_commands`; 53 commands and 83 tools
  versus 82 and 130), while OAuth login still works. `--bare` skips hooks and plugins but
  demands `ANTHROPIC_API_KEY` (`Not logged in`), so it is unusable here.
- `claude -p` waits 3 s for stdin and warns unless stdin is `/dev/null`. `--max-budget-usd`
  caps one run; `--permission-mode dontAsk` plus `--allowedTools` is the official sandbox's
  shape; `--no-session-persistence` keeps eval sessions out of the user's history.
- macOS has no `timeout(1)`; a runner must use `subprocess.run(timeout=…)`.
- The existing agent fixture is `.claude/hooks/tests/fixtures/seeded_defect.py` with an
  `.expected.md` pass condition; it was verified by hand in the agent-automation-suite run, not
  by any script. `test_structure.py:211` only checks the two files exist and agree.
- `post_tool_use.py:26-36` `VERIFICATION` lists pytest/jest/vitest/mocha/ava/go/cargo/make/tsc
  and friends; `playwright|cypress|lighthouse|axe` are absent (grep confirmed in R1's brief).
- The brain (R1) has `events, notes, decisions, lessons, runs, stamps`; `stamp` already records
  sha256 per skill/agent file per run, which is what ties a score to a skill version. Its CLI
  subcommand set was declared exact *for that run*; extending it is this run's call.
- `install.sh` syncs only `.claude/`; anything under `evals/` or `.claude-plugin/` at the repo
  root stays repo-only, which is right — evals are development tooling, not user setup.
- `tests/run.sh` runs 13 suites offline in ~10 s; nothing in it spends money. `test_structure.py`
  scans `markdown_files()` under `.claude/` and the README for unresolvable references.

## Patterns to follow
- Offline first: the hooks harness never calls the network; the runner's own tests must drive
  it through a fake `claude` executable on `PATH` that replays canned stream-json and records
  its argv — the same isolation `GENTIC_BRAIN` and `CLAUDE_HOOK_STATE_DIR` give the brain and
  the ledger.
- Deterministic graders only (`regex`, `file_exists`, `tool_used`); `llm` graders are a
  non-goal — a judge that is itself an LLM is the thing being measured.
- Fibonacci constants: per-run budget 3 USD, suite ceiling 21 USD, default `max_turns` 13.
- Contract tests for docs and cases in the project suite; one task, one commit; RED in the table.
- R1's lessons: every `-k` verify pattern must be a substring of its contract test's name; no
  double-quoted `.claude` literal inside a hook.

## Constraints discovered
- Money: every real case run costs API spend. The suite must never run inside `run.sh`; it is
  invoked deliberately, with a per-run and a per-suite ceiling, and defaults to `runs: 1`.
- The user's session history and brain must stay clean: `--no-session-persistence`, a fresh
  temp workspace per run, `GENTIC_BRAIN` honoured by the runner (results go to the real brain
  only when the user runs it for real).
- The `with` arm must see gentic exactly as the user does: user settings, installed skills,
  hooks, agents — so the fixture workspace needs a `CLAUDE.md` carrying the routing section
  for adopted-project behaviour, and the run must happen after `install.sh` is in sync.
- Cases must stay valid for the official command, so a later switch costs nothing: the same
  files, the same frontmatter keys, the same grader types.

## Open decisions (all resolved by delegation — see decisions.md)
1. Runner location — `evals/run.py` at the repo root beside `evals/<case>/`, tests in
   `.claude/hooks/tests/test_evals.py`. Default: as stated (plugin-root layout).
2. Arms — `with` = user settings as installed; `without` = `--setting-sources project`.
   Default: as stated; `--bare` rejected (needs an API key).
3. Model for suite runs — `sonnet` by default, `--model` overrides; the live proof uses the
   default. Default: as stated (cost; the measured thing is the workflow, not the model).
4. Where scores live — a new `evals` table in the brain plus a `brain evals` subcommand
   (extending R1's "exact" set). Default: as stated.
5. Agent fixtures — as eval cases (the with arm has the agents; the without arm proves the
   delta), not as a separate `claude -p` harness. Default: as stated.
6. Manifest — `.claude-plugin/plugin.json` at the repo root so `claude plugin eval .` works the
   day it is enabled. Default: yes.
