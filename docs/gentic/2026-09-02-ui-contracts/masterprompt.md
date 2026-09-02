# Masterprompt: ui-contracts

## Mission
A Definition of Done can name a UI flow as a contract, a fifth agent can look at the screen
and file a screenshot as evidence, and the Scout opens a runnable product before it asks
anything. The executable half of a UI contract is always the project's own e2e runner; the
browser is for evidence and exploration. Proven by one live `ui-tester` dispatch against a
locally served app and by the workflow case still scoring 4/4.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- **Browser tools.** Subagents that do not restrict `tools:` inherit every
  `mcp__claude-in-chrome__*` and `mcp__Claude_Browser__*` tool (probed). The main thread must
  first load Chrome tools with `ToolSearch` (`select:mcp__claude-in-chrome__tabs_context_mcp,
  mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,
  mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp`). Chrome:
  `tabs_context_mcp{createIfEmpty:true}` → `navigate` → `read_page`/`find`/`computer`;
  `computer{action:"screenshot", save_to_disk:true, scale:0.5}` returns a saved path. Tabs
  created are closed with `tabs_close_mcp` when done. Fallback (`mcp__Claude_Browser__*`):
  `preview_start{url}` or `navigate`, `read_page`, `computer{action:"screenshot"}` (image only —
  when no path can be saved, the report says `screenshot: none (in-app browser)`).
- **Contract grammar** (`gentic-masterprompt/SKILL.md`, the template line at ~37 and the
  "Definition of Done craft" bullets): add, after the existing `contract:` line in the
  template, a second form:
  `contract: ui · <e2e spec file> · <test name> · <flow asserted> · expected RED: <locator or assertion failure>`
  and a craft bullet: "**A UI behaviour gets a `ui` contract.** Its executable half is the
  project's e2e runner (Playwright, Cypress, or whatever the project already runs — the hooks
  recognise them); the browser is for evidence, not for the test. A project with no e2e runner
  gets a `ui-tester` verification with a screenshot instead, and the item is flagged
  `not reproducible in CI` so nobody mistakes the screenshot for a test."
- **TDD** (`gentic-tdd/SKILL.md`): a paragraph under "Tasks with no executable behaviour",
  titled `## UI tasks`: "A `ui` contract is RED when the e2e spec fails against the running app
  with the failure the contract predicted (a missing locator, a wrong text), and GREEN when it
  passes; paste the RED like any other. When the item is flagged `not reproducible in CI`, the
  RED and GREEN are two `ui-tester` reports with screenshots in `docs/gentic/<run>/evidence/`,
  and the task note says so."
- **Scout** (`gentic-scout/SKILL.md`, Method): new step `5. **Runnable product variant.** If
  the project says how to run itself (a `dev`/`start` script, `python3 app.py`, a README
  instruction), start it — the in-app Browser's `preview_start` when a `.claude/launch.json`
  entry exists, otherwise the project's command in the background — open it in Claude in Chrome
  (fallback: the in-app Browser), walk at most 8 routes, save at most 5 half-scale screenshots
  under `docs/gentic/<run>/evidence/scout-<n>.png`, and write a **Feature inventory** section in
  the brief: one line per screen with what it shows and what is missing. Time-box: 13 tool
  calls for the whole variant. Questions asked from a screenshot are sharper than questions
  asked from `ls`."
- **Iterate** (`gentic-iterate/SKILL.md`, Verification step 1): append "A `ui` item has two
  halves: `dod-auditor` runs its e2e command; `ui-tester` opens the flow and files a screenshot
  under `docs/gentic/<run>/evidence/` — both go in the evidence column. An item flagged
  `not reproducible in CI` has only the second half and is reported as such."
- **The agent** `.claude/agents/ui-tester.md` — frontmatter `name: ui-tester`, `description`
  trigger-style (use when a Definition-of-Done item names a UI flow, when a UI failure must be
  reproduced with a screenshot, or when a running product must be inspected before it is
  changed), `model: inherit`, `color: cyan`, **no `tools:` line** (it must inherit the MCP
  browser tools). Body: what it is given (a URL or a start command, one flow or one failure to
  reproduce, the evidence directory); what it never does (edit source, run tests, decide
  whether a behaviour is desirable — it reports what the screen shows); method (load nothing —
  the tools are present; Chrome first, in-app Browser fallback; `tabs_context_mcp`, navigate,
  `read_page`/`find`, act, screenshot with `save_to_disk` and `scale: 0.5`, move the file into
  the evidence directory with `Bash mv`, close its tab); output — a fixed block:
  ```
  status: verified | failed | blocked
  url: <the page>
  flow: <what was attempted, one line>
  observed: <what the screen showed, literal>
  screenshot: <path under docs/gentic/<run>/evidence/, or none (in-app browser)>
  console: <errors seen, or none>
  blocker: <present only when status is blocked>
  ```
  and the rule that `verified` without a screenshot path (when Chrome was available) is not
  `verified`.
- **README**: agents table gains a `ui-tester` row; a section `## UI contracts` before
  `## Standing authorizations` explains the contract form, the evidence directory, the
  `not reproducible in CI` flag, and that Claude in Chrome is preferred with the in-app
  Browser as fallback.
- **Structure tests** (`test_structure.py`): `EXPECTED_AGENTS` gains `"ui-tester"`; a class
  `UiContracts` with tests over lowered text: masterprompt skill contains
  `'contract: ui ·'` and `'not reproducible in ci'`; tdd contains `'## ui tasks'`; scout
  contains `'runnable product variant'` and `'feature inventory'`; iterate contains
  `'ui-tester'`; README contains `'## ui contracts'` and `'ui-tester'`; `ui-tester.md`
  contains `'claude-in-chrome'`, `'claude_browser'`, `'save_to_disk'` and has no `tools:`
  frontmatter key. The existing `test_each_agent_states_what_it_returns` covers its Output
  section.
- **Live proof.** Serve the CSV fixture: `cd evals/csv-export-probe/fixture && python3 app.py`
  in the background (port 8000; stop it afterwards). Dispatch `ui-tester` with: URL
  `http://127.0.0.1:8000/admin/users`, flow "the users table shows the columns id, name,
  email, password_hash, created_at and three rows", evidence directory
  `docs/gentic/2026-09-02-ui-contracts/evidence/`. Expect `status: verified`, a screenshot path
  under that directory that exists, and `observed` naming the five columns. Then the
  regression: `python3 evals/run.py --case csv-export-probe --arm with` → 4/4.
- Lessons carried: `-k` patterns are substrings of contract test names; commit from the repo
  root with absolute paths; every agent needs an Output section.

## Decisions (inlined; the browser is the user's, the rest `user — delegated`)
Chrome first, in-app fallback; the `ui` contract form with the e2e runner as its executable
half and the `not reproducible in CI` flag; evidence under the run directory, half scale, ≤ 5;
a fifth agent with unrestricted tools and a fixed block; the runnable-product Scout variant
with a 13-call box; one live dispatch and one regression run as proof.

## Constraints
- Only the wording sites named in Context change; `dod-auditor`'s pinned tool set is untouched.
- Screenshots ≤ 5 per run, half scale; the evidence directory is committed with the run.
- Every task test-first; observed RED in `progress.md`.

## Non-goals
- No Playwright added to this repository; no eval case for UI; no adjective rubric for
  "awesome"; no Lighthouse/axe integration beyond the existing verification regex.
- No browser tools for `dod-auditor`; no change to any hook.
- No release lane; no CI.

## Definition of Done
- [ ] U1 Grammar. The masterprompt skill carries the `ui` contract form and the craft bullet
      with the `not reproducible in CI` flag.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_grammar`
      contract: tests/test_structure.py · UiContracts.test_ui_grammar_in_masterprompt ·
      expected RED: `AssertionError: 'contract: ui ·' not found in …`
- [ ] U2 TDD and Scout. `gentic-tdd` has `## UI tasks`; `gentic-scout` has the runnable
      product variant with a feature inventory.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_tdd -k ui_scout`
      contract: tests/test_structure.py · test_ui_tdd_names_ui_tasks, test_ui_scout_walks_the_product ·
      expected RED: `AssertionError: '## ui tasks' not found in …`
- [ ] U3 Iterate uses the agent. `gentic-iterate` names `ui-tester` for the screenshot half.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_iterate`
      contract: tests/test_structure.py · test_ui_iterate_dispatches_the_tester · expected RED:
      `AssertionError: 'ui-tester' not found in …`
- [ ] U4 The agent exists. `ui-tester.md` with the frontmatter and body in Context; the agent
      set is exactly five; it has an Output section.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_agent -k expected_agents -k states_what_it_returns`
      contract: tests/test_structure.py · test_ui_agent_is_defined (and the two existing tests
      with `EXPECTED_AGENTS` updated first) · expected RED: `AssertionError: agent set drifted: {…}`
      then `AssertionError: False is not true : ui-tester.md missing`
- [ ] U5 README. Agents row and `## UI contracts` section.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_readme`
      contract: tests/test_structure.py · test_ui_readme_documents_contracts · expected RED:
      `AssertionError: '## ui contracts' not found in …`
- [ ] U6 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 with `ok    test_structure`.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of U1–U5's tests.
- [ ] U7 Live dispatch. After `./install.sh` and `--check` exit 0 (agents resolve at session
      start — if the freshly installed agent is not invocable in this session, dispatch it by
      reading `.claude/agents/ui-tester.md` into a `general-purpose` agent's prompt verbatim
      and say so): the `ui-tester` report has `status: verified`, `observed` names the five
      columns, and `screenshot:` names a file under `docs/gentic/2026-09-02-ui-contracts/evidence/`
      that exists and is smaller than 400 KB. The report is pasted into `progress.md`.
      verify: dispatch; `ls -la docs/gentic/2026-09-02-ui-contracts/evidence/`
      contract: no test contract — a live observation of the agent.
- [ ] U8 Regression gate. `python3 evals/run.py --case csv-export-probe --arm with` shows
      `4/4 (1.00)`; a lower score is a rung-1 entry.
      verify: run it; paste suite id, cost, turns
      contract: no test contract — a live observation; n=1.

## Risks & early signals
- Agents are resolved at session start, so `ui-tester` may not be dispatchable by name in this
  session; U7 names the fallback and requires saying so.
- Chrome may not be connected when U7 runs; the agent then falls back to the in-app Browser and
  reports `screenshot: none (in-app browser)`, which fails U7's screenshot clause — that is a
  finding, not a reason to loosen U7.
- The Scout variant adds tool calls to the workflow case; the 55-turn budget may be tighter
  (brain note: it fit with no headroom). U8 tells.

## Task order (for Execute)
1. Structure tests (all `UiContracts` + `EXPECTED_AGENTS`), then the agent file — U4.
2. Skill wording: masterprompt, tdd, scout, iterate — U1, U2, U3.
3. README — U5; harness — U6.
4. Install; live dispatch; regression — U7, U8.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
