# Masterprompt: tdd-spec-first

## Mission
Make test-first development the structural spine of the gentic workflow rather than a single
delegated sentence inside one phase skill. After this run, a gentic spec designs the tests that
prove each Definition of Done item, the Execute phase routes every task through an explicit
test-first discipline that gentic owns (working with or without the superpowers plugin), a task
cannot be recorded as done without durable RED evidence in the run artifact, and the machine-wide
hook ledger notices when production code changes with no test having failed first.

## Context
Facts the work depends on. Paths are relative to the repository root `/Users/sebiko83/code/gentic`.

- The workflow is six markdown skills under `.claude/skills/`: `gentic` (orchestrator, with a
  sibling `ROUTING.md`), plus `gentic-scout`, `gentic-interview`, `gentic-masterprompt`,
  `gentic-execute`, `gentic-iterate`. `install.sh` copies tracked files under `.claude/` into
  `~/.claude` (install.sh:19-21, install.sh:39-47).
- Today TDD is one sentence in the entire workflow: `.claude/skills/gentic-execute/SKILL.md:23` —
  "**Failing test first.** If superpowers:test-driven-development is available, you MUST invoke it.
  Otherwise the inline rule holds: write the test, watch it fail, then implement." There is no
  definition of RED/GREEN, no evidence requirement, no defence against rationalisation.
- `.claude/skills/gentic-masterprompt/SKILL.md:35` defines a Definition of Done item as an
  observable claim plus a verification command. Nothing in the spec designs a *test*; tests are
  invented during Execute.
- The `progress.md` task-table template is at `.claude/skills/gentic/SKILL.md:64` with columns
  `# | Task | Size | Depends on | Status`. There is nowhere to record which test proves a task or
  that its failure was observed.
- `.claude/agents/task-executor.md` (contract summarised at `.claude/skills/gentic-execute/SKILL.md:48`)
  already requires a dispatched worker to return "the RED failure observed". The solo path demands
  no such thing, so the two execution paths disagree.
- `.claude/hooks/post_tool_use.py` maintains a per-turn ledger: `touched` (paths), `code_changed`
  (a non-prose file was edited), `evidence` (verification commands that succeeded), and a `session`
  sub-dictionary that survives across turns (lib/common.py:29-40).
- That ledger deliberately drops failing runs — `post_tool_use.py:74`: "An unknown exit code counts
  as evidence; a known failure does not." A failing test run is exactly the RED signal a test-first
  gate needs, so today it is discarded.
- `.claude/hooks/stop.py` holds one hard block (a success claim with no verification) and one
  advisory nudge. Its docstring, stop.py:4-7, states the governing rule: "Keeping the nudge
  advisory is deliberate — a second adversarial gate would make the setup something to work around
  rather than with."
- `.claude/hooks/tests/test_structure.py:171-177` fails the build when any markdown file references
  a superpowers skill without a conditional qualifier, so a hard dependency on the plugin is not an
  available design.
- `.claude/hooks/tests/run.sh:147` asserts that exactly **6** files match `skills/gentic*/SKILL.md`.
  Adding a seventh skill breaks this check until the number is updated.
- Test conventions: unittest suites run as `python3 tests/<name>.py` from `.claude/hooks/`, each
  registered in the suite list at `.claude/hooks/tests/run.sh:14`. `run.sh` is the full check and
  also enforces a 150 ms median latency budget for hooks and a hostile-input survival sweep.
- Documentation is already under test in this repo (`test_structure.py` asserts markdown-level
  contracts), so prose changes have a real test home.

## Decisions
From `decisions.md`. **Every row is `default — unconfirmed`**: the Interview ran non-interactively
under the user's standing delegation of 2026-08-11, and no decision fell into the categories gentic
reserves for the user regardless (security, money, other people's data, irreversible actions).

1. **The discipline lives in a new skill, `gentic-tdd`**, invoked per task by `gentic-execute`.
   Not an expansion of gentic-execute (length) and not plugin delegation (test_structure.py:171).
2. **The spec carries test *contracts*, not test code.** Each Definition of Done item names the
   test file, the test name, the behaviour asserted and the expected RED message. Literal test code
   is written during Execute. Rationale: `masterprompt.md` is the spec and the `progress.md` task
   table is the plan; embedding code in the spec duplicates the plan and bloats the artifact.
3. **RED evidence becomes durable**: the task table gains `Test` and `RED` columns, and a task may
   not be marked done while its `RED` cell is empty.
4. **Hook enforcement is advisory.** The ledger starts recording failing verification runs as RED
   evidence and `stop.py` gains a TDD nudge, at most once per session. No second hard block —
   stop.py:4-7 governs. Teeth come from the skill's Iron Law, the spec's test contracts and the
   un-fillable RED column instead.
5. **Scope is machine-wide for the hook, gentic-owned for the skill.** The nudge applies to any
   session; detecting an active run inside a hook would require new coupling.
6. **Tasks with no executable behaviour still need a test.** A task that changes documented
   behaviour extends a contract test. Only a task that changes nothing observable may write `n/a`
   in the `Test` column, and it must state why.
7. **No sixth phase.** Test design deepens the existing Masterprompt and Execute phases.

## Constraints
- Hooks: Python standard library only, no subprocesses, no network; every hook exits 0 on hostile
  input; the `UserPromptSubmit` and `PreToolUse` medians stay under 150 ms (`run.sh` measures both).
- A hook must never break a session. Only `block()` exits 2, and this run adds no new call to it.
- No markdown may reference a superpowers skill without a conditional qualifier
  ("If superpowers:X is available … Otherwise the inline rule holds"), enforced by
  `test_structure.py:171-177`.
- Phase skills stay concise: the new `gentic-tdd/SKILL.md` must not exceed 120 lines, and no
  existing phase skill may grow past 100 lines.
- English for all identifiers, comments and artifacts.
- **Bootstrap:** `gentic-tdd` does not exist when this run starts, so its own tasks are executed
  test-first under the inline rule at `gentic-execute/SKILL.md:23` until the skill exists, and under
  `gentic-tdd` itself from that task onward. Every task here writes its contract test first and
  records the observed RED — the run is the discipline's first proof.
- Run artifacts are committed documentation; checkpoint commits land only on the branch
  `gentic/tdd-spec-first`, one task per commit, never pushed.

## Non-goals
- **No sixth phase** is added; the phase count stays five.
- **No second hard block.** `pre_tool_use.py` is not touched, no edit is ever blocked for lacking
  a test, and the existing verification gate's semantics are unchanged.
- **This run does not write to `~/.claude`.** `install.sh` is not executed; the repository is the
  deliverable and installation stays the user's decision.
- **Superpowers content is not vendored or reproduced.** Composition stays conditional.
- **Past run artifacts under `docs/gentic/*/` are not retrofitted** with the new columns.
- **No test framework, runner or dependency is introduced.** New tests are stdlib `unittest`
  suites in the existing harness.
- **The hook does not attempt to judge test quality** — it observes file classes and exit codes,
  nothing semantic.
- **No new agent definitions.** `.claude/agents/` is unchanged; the discipline is a skill.
- **`gentic-scout` and `gentic-interview` are not modified** — test design belongs to the spec and
  the loop, not to discovery or question-asking.
- **The iteration-log schema is unchanged.** Only the task table gains columns.

## Definition of Done

Each item names the check that proves it and the test contract behind it. Test-contract fields:
*file* · *test name* · *behaviour asserted* · *expected RED*.

- [ ] **D1 — A `gentic-tdd` skill exists, states an Iron Law forbidding production code before a
  failing test, and is a complete discipline on its own (RED, verify-RED, GREEN, REFACTOR, an
  evidence format, and a rationalisation table).**
  verify: `cd .claude/hooks && python3 tests/test_structure.py`
  contract: `.claude/hooks/tests/test_structure.py` · `test_gentic_tdd_skill_is_self_contained` ·
  the file `.claude/skills/gentic-tdd/SKILL.md` exists, carries valid frontmatter with
  `name: gentic-tdd`, and contains all of: an iron-law statement, "RED", "GREEN", "REFACTOR",
  and a rationalisation/red-flag table. The `GENTIC_SKILL` pattern at `test_structure.py:51` must
  also gain `tdd`, or references to the new skill go unvalidated by
  `test_referenced_gentic_skills_exist` · expected RED:
  `AssertionError: .claude/skills/gentic-tdd/SKILL.md does not exist`

- [ ] **D2 — `gentic-execute` routes every task through `gentic-tdd`, and its per-task loop
  requires RED evidence before a task may be ticked.**
  verify: `cd .claude/hooks && python3 tests/test_structure.py`
  contract: `.claude/hooks/tests/test_structure.py` · `test_execute_routes_tasks_through_tdd` ·
  `gentic-execute/SKILL.md` names `gentic-tdd` and states that a task with an empty RED cell is not
  done · expected RED: `AssertionError: gentic-execute does not invoke gentic-tdd`

- [ ] **D3 — The masterprompt template requires a test contract on every Definition of Done item,
  and the critique pass scans for a missing one.**
  verify: `cd .claude/hooks && python3 tests/test_structure.py`
  contract: `.claude/hooks/tests/test_structure.py` · `test_masterprompt_requires_test_contracts` ·
  `gentic-masterprompt/SKILL.md` contains a `contract:` line in its DoD template naming all four
  fields, and its critique pass lists a test-contract scan · expected RED:
  `AssertionError: masterprompt template has no test contract`

- [ ] **D4 — The `progress.md` task-table template carries `Test` and `RED` columns.**
  verify: `cd .claude/hooks && python3 tests/test_structure.py`
  contract: `.claude/hooks/tests/test_structure.py` · `test_task_table_template_has_tdd_columns` ·
  the task-table header inside `gentic/SKILL.md` includes both `Test` and `RED` ·
  expected RED: `AssertionError: task table header lacks a RED column`

- [ ] **D5 — The ledger records a failed verification command as RED evidence, keyed separately
  from success evidence, while an unknown exit code still counts as success evidence as before.**
  verify: `cd .claude/hooks && python3 tests/test_tdd.py`
  contract: `.claude/hooks/tests/test_tdd.py` · `test_failing_verification_is_recorded_as_red` ·
  a `Bash` PostToolUse payload running `pytest tests/test_x.py` with `exit_code: 1` leaves a
  non-empty `red` list in the turn state, and the same command with exit code 0 does not.
  Assert via `state.get("red")`, not `state["red"]`: a `KeyError` is a test *error*, and a RED must
  be a clean failure · expected RED: `AssertionError: [] is not true : no RED recorded`

- [ ] **D6 — The ledger distinguishes test files from production files, recognising at minimum
  `test_*.py`, `*_test.go`, `*.test.ts`, `*.spec.js`, and any path under a `tests/`, `test/`,
  `spec/` or `__tests__/` directory.**
  verify: `cd .claude/hooks && python3 tests/test_tdd.py`
  contract: `.claude/hooks/tests/test_tdd.py` · `test_test_files_are_classified_separately` ·
  editing `tests/test_app.py` sets a test-file marker **and still sets `code_changed`** (the
  existing verification gate must keep firing on test-only turns), while editing `src/app.py` sets
  `code_changed` and no test marker ·
  expected RED: `AssertionError: False is not true : test file edit was not recorded`

- [ ] **D7 — `stop.py` emits an advisory TDD nudge when a turn changed production code with no test
  file touched and no RED observed, and that path never blocks.**
  verify: `cd .claude/hooks && python3 tests/test_tdd.py`
  contract: `.claude/hooks/tests/test_tdd.py` · `test_tdd_nudge_is_advisory` ·
  *production code* means a turn where `code_changed` is true and no test-file marker was set.
  After such an edit with no RED, `stop.py` exits 0 and its output mentions a failing test first · expected RED:
  `AssertionError: '' does not contain 'failing test'`

- [ ] **D8 — The TDD nudge is suppressed when the turn shows test-first behaviour, and fires at
  most once per session.**
  verify: `cd .claude/hooks && python3 tests/test_tdd.py`
  contract: `.claude/hooks/tests/test_tdd.py` · `test_tdd_nudge_suppressed_and_bounded` ·
  (a) a turn with RED evidence produces no TDD nudge, (b) a turn that touched a test file produces
  no TDD nudge, (c) two consecutive qualifying stops produce the nudge exactly once ·
  expected RED: `AssertionError: nudge fired twice in one session`

- [ ] **D9 — README.md and CLAUDE.md present test-first as the workflow's spine, naming
  `gentic-tdd` and the RED-evidence requirement.**
  verify: `cd .claude/hooks && python3 tests/test_structure.py`
  contract: `.claude/hooks/tests/test_structure.py` · `test_docs_document_the_tdd_spine` ·
  both `README.md` and `CLAUDE.md` mention `gentic-tdd` and RED evidence ·
  expected RED: `AssertionError: README.md does not mention gentic-tdd`

- [ ] **D10 — The whole harness is green, including the updated skill count and the unchanged
  latency and hostile-input budgets.**
  verify: `bash .claude/hooks/tests/run.sh` exits 0 with no `FAIL` line
  contract: `.claude/hooks/tests/run.sh` · the `test_tdd` suite is registered in the suite list and
  the `gentic*/SKILL.md` count check reads 7 · expected RED:
  `FAIL  expected 6 gentic skills in the repo`

- [ ] **D11 — No markdown introduced or edited by this run references a superpowers skill
  unconditionally, so gentic still works standalone.**
  verify: `cd .claude/hooks && python3 tests/test_structure.py -k superpowers`
  contract: existing test — `.claude/hooks/tests/test_structure.py` ·
  `test_superpowers_references_are_marked_conditional` · every superpowers reference carries a
  conditional qualifier · expected RED: a new unqualified reference is listed as an offender

- [ ] **D12 — `install.sh --check` reports the new skill as pending rather than erroring, proving
  the install path handles a seventh skill without this run writing to `~/.claude`.**
  verify: `./install.sh --check; echo "exit=$?"` — output lists `skills/gentic-tdd/SKILL.md` as
  missing and the exit status is non-zero (drift reported, nothing written)
  contract: manual inspection step, no new test — `install.sh` enumerates via `git ls-files`, so
  the new skill must be **staged or committed** before `--check` can see it at all ·
  expected RED: the path is absent from the drift list because the file is untracked

## Risks & early signals
- **Nudge noise.** A false-positive TDD nudge on every refactor would make the setup something to
  work around. Early signal: the nudge appears in a session that did nothing wrong. Bound: once per
  session, advisory only, suppressed by any test-file edit or any RED evidence (D8).
- **Skill sprawl.** A seventh skill is a real cost to the workflow's legibility. Early signal:
  `gentic-tdd` duplicating text from `gentic-execute`. Mitigation: execute keeps the loop, tdd
  keeps the discipline; the 120-line cap (Constraints) forces the split to stay honest.
- **Latency regression.** New path-classification work runs on every edit. Early signal: `run.sh`'s
  latency section. The classifier must be pure string work — no filesystem access.
- **Classifying test files could silently weaken the existing verification gate.** Found by this
  spec's own contradiction scan: an early draft of D6 had test files stop setting `code_changed`,
  which would have let a test-only turn claim success unverified. `code_changed` stays true for
  every non-prose edit; the test marker is strictly additive.
- **Retrofit pressure.** Existing run artifacts lack the new columns. Non-goal: they stay as they
  are; only the template changes.
- **The spec-drives-tests rule could become bureaucratic** for trivially small runs. Early signal:
  a DoD item whose test contract restates its verify command. Mitigation: a contract is required to
  name a *test*, and `n/a` with a stated reason is legal for tasks with nothing observable.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
