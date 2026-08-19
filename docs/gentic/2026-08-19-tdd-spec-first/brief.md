# Brief: tdd-spec-first

## Mission (as understood)
Gentic already calls itself spec-first, but TDD inside it is a single delegated line and the
spec never designs the tests. Make test-first and spec-driven development the *enforced spine*
of the workflow rather than an aspiration: the masterprompt should design the tests that prove
each Definition of Done item, Execute should be unable to record a task as done without RED-then-
GREEN evidence, and the hook ledger should notice when production code changes without a test
having failed first. Depth of discipline comparable to superpowers, but self-contained — gentic
must keep working when superpowers is absent.

## Facts
- Five phase skills plus the orchestrator live in `.claude/skills/gentic*/SKILL.md`; they are
  installed machine-wide into `~/.claude` by `install.sh` (install.sh:19-21, install.sh:39-47).
- TDD is currently **one sentence** in the whole workflow: "Failing test first. If
  superpowers:test-driven-development is available, you MUST invoke it. Otherwise the inline rule
  holds: write the test, watch it fail, then implement." (.claude/skills/gentic-execute/SKILL.md:23).
  No RED/GREEN definition, no evidence requirement, no rationalization defences.
- The masterprompt template has a Definition of Done with a named check per item
  (.claude/skills/gentic-masterprompt/SKILL.md:35) but **nothing about test design** — the check
  is a verification command, not a test contract. Tests are invented at Execute time.
- `progress.md`'s task table columns are `# | Task | Size | Depends on | Status`
  (.claude/skills/gentic/SKILL.md:64) — no column can hold RED evidence, so test-first leaves no
  durable trace and a resumed session cannot tell whether a task was done test-first.
- An evidence ledger already exists: `post_tool_use.py` records every edited path, whether the
  edit was code or prose, and every *successful* verification command (post_tool_use.py:68-84).
- That ledger **deliberately discards failing verification runs** — "An unknown exit code counts
  as evidence; a known failure does not" (post_tool_use.py:74). A failing test run is precisely
  the RED evidence a TDD gate needs, so today the signal is thrown away.
- `stop.py` consumes the ledger for one hard block (success claim with no verification) and one
  advisory nudge. Its docstring states the design rule explicitly: "a second adversarial gate
  would make the setup something to work around rather than with" (stop.py:4-7).
- `task-executor` already returns "the RED failure observed" in its report block
  (.claude/skills/gentic-execute/SKILL.md:48) — the fan-out path demands evidence the solo path
  does not. The two paths disagree today.
- Superpowers is installed at `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0`,
  but `test_structure.py:171-177` fails the build if any markdown references a superpowers skill
  without a conditional qualifier. A hard dependency is not available as a design option.
- Superpowers' own model: `test-driven-development` carries an Iron Law, a mandatory
  verify-RED step, a rationalization table and a completion checklist; `writing-plans` embeds the
  literal test code, the exact command and the *expected failure message* into every task step.
- Test conventions: `python3 tests/<suite>.py` unittest suites run by
  `.claude/hooks/tests/run.sh`, which also asserts markdown-level contracts. Documentation is
  already tested here (`test_structure.py`), so a docs-only change has a real test home.
- `run.sh:147` hard-codes an expected count of **6** `gentic*/SKILL.md` files; adding a phase
  skill breaks that check unless updated.

## Patterns to follow
- Phase skills are short (55-78 lines), open with Overview + a bolded core principle, and close
  with a "Common mistakes" or "Red flags" table (.claude/skills/gentic-iterate/SKILL.md:47-55).
- Conditional composition phrasing: "If superpowers:X is available, you MUST invoke it. Otherwise
  the inline rule holds: ..." (.claude/skills/gentic-execute/SKILL.md:23) — the only form that
  passes `test_structure.py:171`.
- Behaviour that must survive a doc rewrite is pinned by a contract test in
  `.claude/hooks/tests/test_structure.py`, not by prose alone.
- Hooks: standard library only, never break a session, advisory unless the block is the one
  sanctioned gate (lib/common.py:3-9).

## Constraints discovered
- No unconditional dependency on the superpowers plugin, enforced by a test.
- Hooks stay stdlib-only, sub-150ms median (run.sh latency budget), and must exit 0 on hostile
  input.
- At most one hard block in the setup; new enforcement is advisory unless it replaces the
  existing gate (stop.py:4-7).
- Artifacts are committed documentation; run artifacts must stay readable, not become forms.
- This run's own changes are markdown + Python hooks, so its tests are contract tests in
  `.claude/hooks/tests/`.

## Open decisions (ranked by leverage)
1. **Where the TDD discipline lives** — options: (A) a new `gentic-tdd` phase-companion skill
   invoked per task by Execute; (B) expand the inline rule inside `gentic-execute`; (C) keep
   delegating to superpowers. Recommended default: **A** — it matches how superpowers factors the
   discipline, keeps `gentic-execute` at its current readable length, makes the discipline
   invocable on its own, and removes the plugin dependency in substance rather than in wording.
2. **Whether the masterprompt designs the tests** — options: (A) every DoD item gains a *test
   contract* (test file, test name, the behaviour asserted, the expected RED message); (B) DoD
   keeps only its verification command as today. Recommended default: **A** — this is what makes
   the workflow spec-*driven* rather than spec-*checked*; without it the spec never constrains
   test design and Execute invents coverage.
3. **Whether RED evidence is recorded durably** — options: (A) add a `Test` and a `RED seen`
   column to the `progress.md` task table so test-first survives a resume; (B) leave the table and
   trust the transcript. Recommended default: **A** — the workflow's stated principle is that the
   run directory, not memory, carries state; RED evidence is currently the one piece of evidence
   with nowhere to live.
4. **Hook enforcement strength** — options: (A) ledger records failing verification runs and
   `stop.py` gains an *advisory* TDD nudge when code changed with no test file touched and no RED
   observed; (B) a second hard block; (C) no hook change. Recommended default: **A** — (B)
   contradicts the documented single-gate rule at stop.py:4-7, (C) leaves the enforcement purely
   exhortative, which is the gap being closed.
5. **Scope of the TDD rule outside gentic runs** — options: (A) machine-wide — the hook nudge
   applies to any code change, the skill discipline stays gentic-owned; (B) gentic runs only.
   Recommended default: **A** — hooks already run machine-wide and cannot see whether a run is
   active without new coupling.
6. **The rule for tasks with no executable behaviour** (docs, spec, prompt edits — a large share
   of this repo's own work) — options: (A) the contract test is the test: a task changing
   documented behaviour must add or extend a contract test in the project's suite, and only a
   task changing *nothing observable* may declare "no test" with a stated reason; (B) exempt
   non-code tasks. Recommended default: **A** — this repo already tests its markdown
   (`test_structure.py`), and a blanket exemption would let any prose-shaped task opt out.
