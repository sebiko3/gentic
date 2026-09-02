# Masterprompt: gentic-evals

## Mission
After this run gentic can be scored. `python3 evals/run.py` runs every case under `evals/`
headlessly through `claude -p`, once with the user's installed setup and once with
`--setting-sources project` (no user skills, hooks or agents), grades each run with graders
whose verdict is a pure function of the transcript and the files the agent created, prints a
per-case line with the with/without pass rates and their delta, writes `result.json` for
humans and rows into the brain for later runs, tied to the sha256 of the installed skills and
agents that produced them. Five cases exist: the README's CSV-export probe and one behavioural
test per agent. Playwright, Cypress, Lighthouse and axe count as verification evidence. Every
runner behaviour is proven offline through a fake `claude`; one real suite run at Iterate
proves the number is real.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Definitions
- **Run** — one `claude -p` session for one (case, arm, run index), in its own fresh workspace.
- **Run score** — passed graders ÷ total graders for that run (an errored or timed-out run
  scores 0: every grader fails with the error as detail).
- **Case pass rate (per arm)** — the unweighted mean of that case's run scores in that arm.
- **Suite pass rate (per arm)** — the unweighted mean of the case pass rates.
- **Delta** — `with − without`, per case and for the suite. Reported to two decimals.
- **Suite ID** — the local timestamp `YYYYMMDD-HHMMSS` at launch. It is the results directory
  name (`evals/results/<suite>/`), the `suite` field in `result.json` and in every brain row,
  and the brain run slug — so every suite run is its own brain `run` and history accumulates.
- **Console line format**, one per case, then one suite line:
  `csv-export-probe            with 3/3 (1.00)  without 1/3 (0.33)  delta +0.67  $1.42`
  `suite 20260902-141500        with 0.87         without 0.31         delta +0.56  $9.80  exit 1`
  A skipped (ceiling) case prints `skipped: suite budget` in place of the numbers.

## Context
- **Invocation** (exact, in this order):
  `claude -p <prompt> --output-format stream-json --verbose --max-turns <N>
  --max-budget-usd <B> --permission-mode dontAsk --allowedTools <T…> --no-session-persistence
  --model <M> [--setting-sources project]`, stdin from `/dev/null`, `cwd` = the run's
  workspace, env = the parent's env plus `GENTIC_BRAIN=<evals/results/<suite>/hooks-brain.sqlite>`
  so hook events from eval sessions never enter the user's real brain. `claude` is resolved
  through `PATH` with `shutil.which`, never a hardcoded path. Output is JSON lines: `assistant`
  messages carry `content` blocks of `type: tool_use` (`name`, `input`); the final `result`
  line carries `result` (last message text), `total_cost_usd`, `num_turns`, `is_error`.
  `Task` and `Agent` are the same subagent tool across builds; a `tool_used` grader for either
  name matches both.
- **Preflight** (before any run; `--dry-run` performs it too): `claude --help` output must
  contain every flag the runner emits (`--output-format`, `--verbose`, `--max-turns`,
  `--max-budget-usd`, `--permission-mode`, `--allowedTools`, `--no-session-persistence`,
  `--model`, `--setting-sources`); a missing flag → print `preflight: claude lacks <flag>` and
  exit 1 without launching. Then `bash install.sh --check` (from the repo root) must exit 0 so
  the `with` arm measures the checkout under test; drift → print the drift and exit 1.
  `--skip-install-check` bypasses only the second step (for tests and for deliberate runs
  against a stale install). The installed `claude --version` is written into `result.json`.
- **Fake `claude` for tests.** Tests prepend a temp dir to `PATH` holding an executable
  `claude` (a Python script). With `--help` it prints a canned help text containing the flags
  above (a test may remove one to exercise preflight). Otherwise it writes a JSON record to
  `$FAKE_CLAUDE_ARGV` — `{"argv": […], "cwd": …, "files": <sorted relative paths present in
  cwd>, "env_brain": $GENTIC_BRAIN}` — appending one line per invocation; creates each path
  listed in `$FAKE_CLAUDE_TOUCH` (colon-separated, relative to cwd); replays the file named by
  `$FAKE_CLAUDE_TRANSCRIPT` to stdout; exits `$FAKE_CLAUDE_EXIT` (default 0). Every
  `test_evals` test sets `GENTIC_BRAIN` and `CLAUDE_HOOK_STATE_DIR` to its own temp paths
  itself; the `run.sh` export is a backstop, not the mechanism. Tests never invoke `install.sh`.
- **Case layout.** A *case* is any child directory of `evals/` containing `prompt.md`;
  `evals/results/` and loose files are ignored. `prompt.md` = YAML-style frontmatter + body
  (the prompt). Frontmatter keys: `name`, `tags`, `runs` (default 1), `max_turns` (default 13),
  `timeout_seconds` (default 900), `allowed_tools`, `model`. `tags` is recorded in
  `result.json` and used by nothing else in this run. Optional `case.yaml` with the dotted key
  `context.scaffold_script: <file relative to the case dir>`. Graders: `graders/*.md`,
  frontmatter `type` plus type-specific keys; the body is rubric text the runner ignores.
  **Parser:** one flat `key: value` parser for both files, stdlib only; values that start
  with `[` are JSON arrays, `true`/`false`/integers are converted, everything else is a
  string; nested YAML is not supported and `case.yaml` uses dotted keys. Unknown keys
  (`append_system_prompt`, `env`, `context.add_dirs`, `context.history_file`) are recorded
  under `warnings` in `result.json`, never an error.
- **Model precedence:** `--model` > frontmatter `model` > `sonnet`. The resolved model is
  always passed explicitly and recorded on each arm entry in `result.json` (the top-level
  `model` is the suite default).
- **Workspace and scaffold.** Each run gets a fresh directory `evals/results/<suite>/workspaces/<case>-<arm>-<n>/`
  (retained after the run; `evals/results/` is git-ignored). When `case.yaml` names
  `context.scaffold_script`, it runs with `bash` in the workspace before the `claude` call,
  with `EVAL_CASE_DIR` (the case directory) and `EVAL_REPO` (the repository root) set; a
  non-zero exit fails that run (score 0, detail = the script's stderr). **The runner never
  copies fixtures itself**: every case with a `fixture/` directory has a `case.yaml` whose
  script copies what it needs. **The file snapshot for `file_exists` is taken after the
  scaffold exits and before `claude` starts**; scaffold output is never "created".
- **Graders.** Exactly three types ship in this run. `regex`: `pattern` (Python `re`),
  `flags` (letters from `i`, `m`, `s`), `match: contains` (default) | `not_contains`,
  `target: last_message` (default) | `files` (the newline-joined sorted list of created
  paths). `file_exists`: `path` is a glob (`fnmatch`, case-sensitive) matched against created
  paths. `tool_used`: `tool`, optional `input_match` (regex over `json.dumps(input, sort_keys=True)`),
  `min` (default 1), `max` (optional). Any other `type` yields one failed grader result with
  detail `unsupported grader <type>`; the case's other graders still run. A timed-out run
  (`timeout_seconds`) is killed, marked `is_error`, and every grader fails with detail
  `timeout after <N>s`. No retries: an errored run is a run.
- **Order and money.** Cases execute strictly sequentially in the order listed below, `with`
  arm before `without`, runs in index order; no parallelism. `--max-budget-usd` (per run,
  default 2) is passed through. Before launching a run the runner checks
  `spent + per_run_budget > --suite-budget-usd` (default 21) and, if so, skips the run,
  records `skipped: suite budget`, and continues to the report; the true ceiling is therefore
  21. Exit codes: 2 if any run was skipped; else 1 if any `with` case pass rate is below
  `--threshold` (default 1.0); else 0. `--arm with|without|both` (default `both`), `--runs N`
  overrides frontmatter, `--case <glob>` filters by directory name, `--dry-run` runs
  preflight and prints each case, its grader count, and the exact argv per arm, invoking
  nothing else, exit 0 (or 1 on preflight failure).
- **Results.** `evals/results/<suite>/result.json` (parents created):
  `{suite, claude_version, model, install_in_sync, warnings:[…], cases:[{name, tags,
  arms:{with:[{model, cost_usd, turns, is_error, skipped, graders:[{name, type, passed, detail}]}], without:[…]},
  pass_rate:{with, without}, delta}], totals:{pass_rate:{with, without}, delta, cost_usd, skipped}}`.
  No HTML, no `latest` symlink, no index, no run-over-run comparison: the brain is the history.
- **Brain.** `.claude/hooks/lib/brain.py` gains two tables —
  `eval_runs(id, ts, project, suite, case_name, arm, run_index, model, cost_usd, turns, is_error, skipped)` and
  `eval_graders(id, run_id, name, type, passed, detail)` — two best-effort functions
  `record_eval_run(cwd, suite, case_name, arm, run_index, model, cost_usd, turns, is_error, skipped) -> run_id | None`
  and `record_eval_grader(run_id, name, type, passed, detail)` (best-effort = any exception is
  swallowed and `None` returned, exactly like `record_event`), and a subcommand
  `evals [--suite ID] [--all]` printing, per case of the latest (or named) suite, the console
  line format above computed from the tables (cost = sum of `eval_runs.cost_usd`, never from
  grader rows). The runner imports `brain` from `.claude/hooks/lib` (via `sys.path`) and
  calls, in process: `brain.main(["run","start",<suite>,"--goal","eval suite <suite>"])`,
  `brain.main(["stamp",<suite>, <installed skill and agent files>])` where the files are
  `${CLAUDE_HOME:-$HOME/.claude}/skills/gentic*/SKILL.md` and `${CLAUDE_HOME:-$HOME/.claude}/agents/*.md`
  (the ones the `with` arm actually runs), then the record functions per run, and finally
  `brain.main(["run","finish",<suite>,"--outcome","done"|"stopped"])` (`stopped` when any run
  was skipped). The project key is the repo's (cwd = repo root). `--no-brain`: no brain call
  of any kind. The runner honours `GENTIC_BRAIN` for its own writes like any CLI user.
- **The five cases** (directory names, in execution order). Prompts are the exact strings
  shown. Cases 2–5: `max_turns: 8`, `allowed_tools: ["Read","Glob","Grep","Bash","Task"]`.
  1. `csv-export-probe` — `case.yaml` scaffold: copies `fixture/` in, copies `$EVAL_REPO/CLAUDE.md`
     to `./CLAUDE.md` (so the routing text is the real one, never a stale copy), runs
     `git init -q && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -qm init`.
     Fixture (stdlib only, at most 5 files and 200 lines in total): `app.py` — an
     `http.server`-based admin dashboard with routes `/admin/users` and `/admin/orders` over an
     in-memory `USERS` list whose rows carry `id, name, email, password_hash, created_at`;
     `tests/test_app.py` — `unittest` tests runnable with `python3 -m unittest`; `README.md`.
     Prompt: `Add CSV export to the admin dashboard. Should work for the users table and be fast.`
     `max_turns: 21`, `allowed_tools: ["Read","Glob","Grep","Write","Edit","Bash"]`.
     Graders: `brief-written` — `file_exists`, `path: docs/gentic/*/brief.md`;
     `pii-surfaced` — `regex`, `pattern: (password_hash|PII|personal data).{0,120}(unconfirmed|exclud|ask|confirm|decision|default)`, `flags: is`;
     `spec-before-code` — `tool_used`, `tool: Write`, `input_match: brief\.md`, `min: 1`.
  2. `dod-auditor-false-claim` — `case.yaml` scaffold copies `fixture/masterprompt.md` and
     creates `present.txt`. The masterprompt has two DoD items: `present.txt exists` (verify
     `test -f present.txt`) and `missing.txt exists` (verify `test -f missing.txt`).
     Prompt: `Dispatch the dod-auditor agent on ./masterprompt.md and relay its per-item verdicts verbatim.`
     Graders: `reports-failed` — `regex`, `pattern: \bFAILED\b`; `reports-proven` — `regex`,
     `pattern: \bPROVEN\b`; `used-the-agent` — `tool_used`, `tool: Task`, `input_match: dod-auditor`.
  3. `critic-finds-contradiction` — `case.yaml` scaffold copies `fixture/masterprompt.md`,
     whose Constraints say `No network access of any kind during the run` while DoD item 2
     says `The dataset is downloaded from https://example.com/data.csv into ./data/`.
     Prompt: `Dispatch the masterprompt-critic agent on ./masterprompt.md and relay its findings verbatim.`
     Graders: `names-the-contradiction` — `regex`,
     `pattern: network.{0,160}(download|data\.csv|DoD)|(download|data\.csv|DoD).{0,160}network`, `flags: is`;
     `used-the-agent` — `tool_used`, `tool: Task`, `input_match: masterprompt-critic`.
  4. `executor-refuses-vague` — no fixture, no `case.yaml`.
     Prompt: `Dispatch the task-executor agent with exactly this assignment and nothing else: "improve the code". Relay its reply verbatim.`
     Graders: `refuses` — `regex`, `pattern: assignment unclear|blocked`, `flags: i`;
     `used-the-agent` — `tool_used`, `tool: Task`, `input_match: task-executor`.
  5. `reviewer-seeded-defect` — `case.yaml` scaffold copies
     `$EVAL_REPO/.claude/hooks/tests/fixtures/seeded_defect.py` to `./seeded_defect.py` (no
     second copy in the repo).
     Prompt: `Dispatch the code-reviewer agent on ./seeded_defect.py, naming that file as the review scope, and relay its findings verbatim.`
     Graders: `finds-injection` — `regex`, `pattern: load_user`; `finds-silent-failure` —
     `regex`, `pattern: record_login`; `ignores-decoy` — `regex`,
     `pattern: get_usr_nm[^\n]{0,80}confidence (8|9)\d`, `match: not_contains` (the decoy may
     be mentioned and dismissed; it may not be reported as a finding at or above 80).
- **Verification regex.** `post_tool_use.py` `VERIFICATION` gains the alternatives
  `playwright|cypress|lighthouse|axe` inside the existing `\b(…)\b` group. `\baxe\b` therefore
  matches `npx @axe-core/cli` and any `axe` binary; intended.
- **Repo hygiene.** `.claude-plugin/plugin.json` carries exactly four keys:
  `name: "gentic"`, `version: "0.2.0"`, `description`, `experimental: {"evals": "evals"}`.
  `.gitignore` gains `evals/results/`. The `for suite in …` loop in `.claude/hooks/tests/run.sh`
  gains `test_evals`; nothing in `run.sh` invokes `evals/run.py`. `test_structure.py`'s
  `markdown_files()` scope is `.claude/**/*.md` plus root `README.md` and root `CLAUDE.md`;
  `evals/**` is outside it and stays outside.
- **Lessons carried from R1** (provenance: brain lessons #1, #2): a hook file must never
  contain a double-quoted `.claude` path literal without `Path.home()` on the same line, or
  the harness isolation grep fails; every `-k` pattern in a verify command must be a substring
  of its contract test's name.
- Precedent: `tests/test_brain.py` (subprocess-driven, `GENTIC_BRAIN` isolation),
  `tests/test_install.py`, `lib/brain.py` `record_event` (the best-effort shape).
- Environment: Claude Code 2.1.258, Python 3.13, macOS (no `timeout(1)`; use
  `subprocess.run(timeout=…)`). Runner requires `git` and `python3 ≥ 3.9` on `PATH`.

## Decisions (inlined; all `user — delegated`)
Home-grown runner over `claude -p` reading the official case layout; three grader types;
`without` = `--setting-sources project`; `sonnet` default; budgets 2 per run / 21 per suite;
scores in two brain tables plus `result.json`; agent tests as cases; four-key manifest; one
live suite run at Iterate under the real install. The `with` arm deliberately runs against
the user's real `~/.claude` with an unattended `dontAsk` allow-list including `Bash`: that is
what the official sandbox does and what "as the user runs it" means; the workspace is a temp
directory, the hooks' brain is redirected, and nothing else is sandboxed. Stated, accepted.

## Constraints
- Stdlib only in `evals/run.py` and `lib/brain.py`; the runner may use `subprocess`.
- `run.sh` stays offline and within its latency budgets; `test_gate.py` stays at 19 passing;
  `test_brain.py` stays at 13 passing plus whatever E5 adds.
- No real `claude` call inside any test. The live proof happens once, at Iterate.
- Every task test-first via `gentic-tdd`; observed RED in `progress.md`.

## Non-goals
- No `llm` or `baseline` graders; no judge model; no fourth grader type even where a case
  would benefit.
- No CI, no scheduled runs, no gardener; nothing runs the suite unattended.
- No changes to skills or agents to make a case pass: a failing case is a finding for the
  epic, recorded as a lesson.
- No MCP mocks; no `add_dirs`, `history_file`, `append_system_prompt`, `env` support.
- No parallelism, no `--jobs`; no retries, no best-of-N, no variance statistics.
- No HTML report, no publishing, no `latest` symlink, no results index, no run-over-run diff.
- No manifest keys beyond the four; no `install.sh` change; evals stay repo-only.
- No `--tag` selector (tags are recorded only).

## Definition of Done
- [ ] E0 Preflight. With a fake `claude --help` lacking `--no-session-persistence`, the runner
      exits 1 printing `preflight: claude lacks --no-session-persistence` and never invokes
      `claude` with a prompt; with a complete help it proceeds. `--skip-install-check` skips
      the install check only.
      verify: `python3 .claude/hooks/tests/test_evals.py -k preflight`
      contract: tests/test_evals.py · test_preflight_refuses_a_missing_flag · expected RED:
      `AssertionError: 2 != 1 : runner did not refuse` (before the runner exists, python exits 2)
- [ ] E1 Discovery and dry run. `--dry-run` lists every case (children with `prompt.md`;
      `results/` ignored) with its grader count and the exact argv per arm, invoking nothing.
      verify: `python3 .claude/hooks/tests/test_evals.py -k dry_run`
      contract: tests/test_evals.py · test_dry_run_lists_cases_and_argv · two temp cases plus a
      `results/` dir yield exactly two names; `--setting-sources project` appears in the
      without argv only; `$FAKE_CLAUDE_ARGV` is never written · expected RED:
      `AssertionError: 2 != 0 : runner did not run`
- [ ] E2 Invocation. A run invokes `claude` from `PATH` with the exact flag list in Context,
      stdin `/dev/null`, `cwd` a fresh workspace per run, `GENTIC_BRAIN` pointed at the suite's
      `hooks-brain.sqlite`; `without` adds `--setting-sources project`; model precedence holds.
      verify: `python3 .claude/hooks/tests/test_evals.py -k invocation`
      contract: tests/test_evals.py · test_invocation_flags_per_arm · expected RED:
      `AssertionError: False is not true : claude was never invoked`
- [ ] E3 Graders. `regex` contains/not_contains with flags over `last_message` and `files`;
      `file_exists` over created paths only; `tool_used` with `input_match`/`min`/`max` and
      Task/Agent equivalence; an unsupported type is one failed grader; a timed-out run fails
      every grader with `timeout after <N>s`.
      verify: `python3 .claude/hooks/tests/test_evals.py -k graders`
      contract: tests/test_evals.py · test_graders_score_a_replayed_transcript · expected RED:
      `AssertionError: 0 != 6 : graders were not evaluated`
- [ ] E4 Scaffold and snapshot. The scaffold runs before `claude` with `EVAL_CASE_DIR` and
      `EVAL_REPO`; the file it copies is present at invocation and is *not* counted as
      created; a failing scaffold scores the run 0 with its stderr as detail.
      verify: `python3 .claude/hooks/tests/test_evals.py -k scaffold`
      contract: tests/test_evals.py · test_scaffold_runs_first_and_is_not_created · expected
      RED: `AssertionError: 'fixture.txt' not found in [] : scaffold did not run before claude`
- [ ] E5 Brain. Per run one `eval_runs` row and one `eval_graders` row per grader; `run start`,
      `stamp` (installed files) and `run finish` happen; `brain evals` prints the console line
      format for the latest suite with cost summed from `eval_runs`; `--no-brain` makes no brain
      call of any kind (no rows, no run, no stamps).
      verify: `python3 .claude/hooks/tests/test_evals.py -k brain_rows` and
      `python3 .claude/hooks/tests/test_brain.py`
      contract: tests/test_evals.py · test_brain_rows_and_evals_summary · expected RED:
      `AssertionError: 0 != 2 : no eval_runs rows in brain`
- [ ] E6 Money and exit codes. Sequential order as listed; the ceiling is checked before
      launch against `spent + per-run budget`; a skipped run prints `skipped: suite budget`
      and the suite exits 2; a `with` case below threshold exits 1; all passing exits 0;
      `result.json` totals carry cost, delta and `skipped`.
      verify: `python3 .claude/hooks/tests/test_evals.py -k money`
      contract: tests/test_evals.py · test_money_ceiling_and_exit_codes · fake transcripts
      costing 8 each with per-run budget 8 and a ceiling of 21 run two and skip the third ·
      expected RED: `AssertionError: 0 != 2 : suite ceiling did not stop the third run`
- [ ] E7 The five cases. `evals/` holds exactly the five case directories named in Context;
      each `prompt.md` parses with the stated `max_turns` and `allowed_tools`; each grader is a
      supported type with the stated keys; cases 1, 2, 3, 5 have `case.yaml` and an executable
      scaffold; case 1's fixture is stdlib-only, ≤ 5 files, ≤ 200 lines, and its tests pass
      under `python3 -m unittest` from the fixture directory.
      verify: `python3 .claude/hooks/tests/test_evals.py -k five_cases`
      contract: tests/test_evals.py · test_five_cases_are_well_formed · expected RED:
      `AssertionError: [] != ['csv-export-probe', 'dod-auditor-false-claim', …]`
- [ ] E8 UI test runners count. `post_tool_use` payloads for `npx playwright test`,
      `cypress run`, `lighthouse http://localhost`, `npx @axe-core/cli` with exit 0 record
      evidence; `npx playwright test` with exit 1 records RED.
      verify: `python3 .claude/hooks/tests/test_tdd.py -k ui_test_runners`
      contract: tests/test_tdd.py · test_ui_test_runners_are_verification_commands · expected
      RED: `AssertionError: [] != [...] : playwright run was not recorded as evidence`
- [ ] E9 Live proof. Preceded by `./install.sh --check` exiting 0 (output pasted). Then
      `python3 evals/run.py` (defaults: both arms, one run, sonnet, budgets 2/21) prints a
      with-line, a without-line and a numeric delta for each of the five cases and a suite
      line; `python3 .claude/hooks/lib/brain.py evals` lists the same five cases with the same
      numbers; the exit code matches the printed numbers (0 iff every with pass rate ≥ 1.0;
      2 iff any case skipped; else 1). Any case the runner could not score is named with its
      reason. Any `with` case scoring below 1.0 becomes a brain `lesson` with `--caught-by suite`.
      verify: run the three commands; paste all output into `progress.md`
      contract: n/a — no code changes for this item; it is the single observation of the real
      system and the pasted output is the evidence.
- [ ] E10 Harness. The suite loop in `run.sh` includes `test_evals`; `run.sh` never mentions
      `evals/run.py`; `bash .claude/hooks/tests/run.sh` exits 0 with a `test_evals` line.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: tests/test_evals.py · test_harness_registers_evals_offline · expected RED:
      `AssertionError: 'test_evals' not found in 'for suite in …'`
- [ ] E11 Docs. `README.md` gains `## The fitness function` naming `evals/run.py`, both arms,
      `--setting-sources project`, the 2/21 budgets, `brain evals`, and the sentence that the
      case layout follows `claude plugin eval`'s format as documented for Claude Code 2.1.258,
      unverified against the command because it is early-access; `.claude/hooks/README.md`
      names the four UI runners in the verification vocabulary.
      verify: `python3 .claude/hooks/tests/test_evals.py -k docs_evals`
      contract: tests/test_evals.py · test_docs_evals_are_documented · expected RED:
      `AssertionError: '## The fitness function' not found in …`
- [ ] E12 Manifest and hygiene. `.claude-plugin/plugin.json` parses with exactly the four
      keys; `git check-ignore -q evals/results/x` succeeds.
      verify: `python3 .claude/hooks/tests/test_evals.py -k manifest`
      contract: tests/test_evals.py · test_manifest_and_gitignore · expected RED:
      `AssertionError: False is not true : .claude-plugin/plugin.json missing`

## Risks & early signals
- Headless gentic may not reach `brief.md` within 21 turns; with no `AskUserQuestion` in `-p`
  the non-interactive rule applies. A with-arm failure on case 1 at E9 is a *finding about the
  workflow*, logged as a lesson, not a reason to loosen the case.
- Real spend: at most 21 USD per suite run by construction; E9 is one run.
- `--permission-mode dontAsk` denies anything not allow-listed; cases list every tool they need.
- The `without` arm may still read the fixture's `CLAUDE.md` routing text and try to follow it
  without the skills; that is the point — the delta measures the skills and agents.

## Task order (for Execute)
1. Runner skeleton: parser, discovery, argv, preflight, `--dry-run`, fake-`claude` test
   harness — E0, E1.
2. Invocation and workspaces — E2.
3. Graders, snapshot, scaffold, timeout — E3, E4.
4. Brain tables, record functions, `brain evals`, runner integration, `--no-brain` — E5.
5. Money, order, exit codes, `result.json` totals — E6.
6. The five cases, fixtures, scaffolds, manifest, gitignore — E7, E12.
7. Verification regex — E8.
8. Harness registration and docs — E10, E11.
9. Live proof — E9 (Iterate-time evidence, pasted; lessons for any with-arm failure).

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read) on the first draft: 6 blocking, 21 serious, 12 minor. All
fixed inline: pass rate, suite ID, console format and delta defined; fixture/scaffold rule and
snapshot point pinned; brain calls quoted as they are; model precedence, timeout, `--no-brain`
scope stated; `results/` excluded from discovery; ceiling checked before launch with budgets
that let five cases complete; cost kept on run rows; E9 given a real pass condition, an install
precondition and brain redirection for eval sessions; preflight added (E0); distinct REDs per
item; case graders rewritten to assert payloads (contradiction, PII, decoy) rather than
vocabulary; unsupported-grader semantics; hermetic E12; sequential/no-retry/no-index/four-key
non-goals; flat dotted-key parser; stdlib fixture with a size bound; R1 lessons inlined;
editorial self-corrections removed.
