# Masterprompt: ui-contracts

## Mission
A Definition of Done can name a UI flow as a contract, a fifth agent can look at the screen
and file a screenshot as evidence, and the Scout opens a runnable product before it asks
anything. The executable half of a UI contract is always the project's own e2e runner; the
browser is for evidence and exploration. Proven by one live `ui-tester` dispatch against a
locally served app and by `csv-export-probe` (the workflow eval case) scoring 4/4 again, as it
did on suite `20260902-205323` (4/4, 2.62 USD, 72 reported turns).

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
- **Scout** (`gentic-scout/SKILL.md`, Method): new step `5. **Runnable product variant** —
  only when the request touches a user-facing surface (a screen, a page, a flow someone clicks);
  a run that touches no UI skips this step. If the project says how to run itself (a
  `dev`/`start` script, `python3 app.py`, a README instruction), start it — the in-app
  Browser's `preview_start` when the project already has a `.claude/launch.json` entry,
  otherwise the project's command in the background — open it in Claude in Chrome (fallback:
  the in-app Browser), walk at most 8 routes starting from the ones the request names, save at
  most 5 half-scale screenshots under `docs/gentic/<run>/evidence/scout-<n>.png`, and write a
  **Feature inventory** section in the brief: one line per screen with what it shows and what
  the request needs that is missing. Never screenshot a production or authenticated surface or
  real personal data; use the project's own fixture or seed data, or skip the screenshot and say
  so. Time-box: 13 tool calls for the whole variant.`
- **Iterate** (`gentic-iterate/SKILL.md`, Verification step 1): append "A `ui` item has two
  halves: `dod-auditor` runs its e2e command; `ui-tester` opens the flow and files a screenshot
  under `docs/gentic/<run>/evidence/` — both go in the evidence column. An item flagged
  `not reproducible in CI` has only the second half and is reported as such."
- **The agent** `.claude/agents/ui-tester.md` — frontmatter `name: ui-tester`, `description`
  beginning `Use when` (a Definition-of-Done item names a UI flow, a UI failure must be
  reproduced with a screenshot, or a running product must be inspected before it is changed),
  `model: inherit`, `color: cyan`, **no `tools:` line** — it must inherit the MCP browser
  tools, and whether a `tools:` list may name MCP tools is unverified (agents resolve at
  session start, so it cannot be probed in this run; recorded as an unconfirmed default). The
  agent is therefore installed machine-wide with Edit, Write, Bash and Task available, and its
  own text is the only thing forbidding edits; the README says so. Body sections, each an
  `##` heading: `## Input` (a URL or a start command, one flow or one failure to reproduce, the
  evidence directory, which the caller has created with `mkdir -p`); `## Never` (edit source,
  run the project's tests, decide whether a behaviour is desirable — it reports what the screen
  shows, literally: the visible text, element names and counts it read, not a paraphrase; and
  never screenshot a production or authenticated surface or real personal data — fixture or
  seed data only, otherwise skip the screenshot and say so); `## Method` (Chrome first:
  `tabs_context_mcp{createIfEmpty:true}`, `navigate`, `read_page`/`find`, act with `computer`,
  screenshot with `save_to_disk: true` and `scale: 0.5`, `mv` the saved file into the evidence
  directory, `tabs_close_mcp`; if a `mcp__claude-in-chrome__*` call errors as unavailable, run
  `ToolSearch` once with the `select:` list above and retry, and if it still fails use
  `mcp__Claude_Browser__*` and report `screenshot: none (in-app browser)`); `## Output` — a
  fixed block:
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
- **README**: (a) the paragraph beginning `Four subagents, each closing a gap` becomes
  `Five subagents, each closing a gap the workflow had left to improvisation. All five are
  plain markdown in [.claude/agents/](.claude/agents). None of the reviewing three is given an
  edit tool.` with the rest of that paragraph unchanged, and a sentence after the table:
  `ui-tester is the one agent whose tools are not pinned: it must inherit the browser tools,
  so its own text is what forbids it to edit.`; (b) the agents table gains a `ui-tester` row;
  (c) a section `## UI contracts` before `## Standing authorizations` explains the contract
  form, the evidence directory, the `not reproducible in CI` flag, the no-real-data rule, and
  that Claude in Chrome is preferred with the in-app Browser as fallback.
- **Structure tests** (`test_structure.py`, class `UiContracts`; `EXPECTED_AGENTS` gains
  `"ui-tester"`). Exact names and what each asserts over lowered text:
  | test | file | asserts contains |
  |---|---|---|
  | `test_ui_grammar_in_masterprompt` | gentic-masterprompt | `'contract: ui ·'`, `'not reproducible in ci'` |
  | `test_ui_tdd_names_ui_tasks` | gentic-tdd | `'## ui tasks'` |
  | `test_ui_scout_walks_the_product` | gentic-scout | `'runnable product variant'`, `'feature inventory'`, `'user-facing surface'` |
  | `test_ui_iterate_dispatches_the_tester` | gentic-iterate | `'ui-tester'` |
  | `test_ui_agent_is_defined` | ui-tester.md | file exists; frontmatter `name` = `ui-tester`, `description` starts with `Use when`, no `tools` key; body contains `'claude-in-chrome'`, `'claude_browser'`, `'save_to_disk'`, `'never'`, `'personal data'` |
  | `test_ui_readme_documents_contracts` | README | `'## ui contracts'`, `'ui-tester'`, `'five subagents'` |
  The existing `test_each_agent_states_what_it_returns` covers the `## Output` heading. Every
  verify below also requires the output line `Ran N tests` with the N stated — `unittest -k`
  exits 0 on zero matches, so the count is the check. Repeated `-k` flags are OR-ed
  (Python ≥ 3.7).
- **Live proof.** `lsof -ti:8000` must be empty; then serve the CSV fixture in the background:
  `cd evals/csv-export-probe/fixture && python3 app.py &` (an unstyled `<table>` on
  `127.0.0.1:8000`, synthetic rows — the `password_hash` values are fixture strings, which is
  why this page may be screenshotted); stop it afterwards with `kill $(lsof -ti:8000)`. Run
  `mkdir -p docs/gentic/2026-09-02-ui-contracts/evidence` first. The independent check, run by
  the main thread: `curl -s http://127.0.0.1:8000/admin/users | grep -o '<tr>' | wc -l` → 4
  (header + three rows). Dispatch `ui-tester` (by name if the freshly installed agent resolves
  in this session; otherwise a `general-purpose` agent whose prompt is the verbatim contents of
  `.claude/agents/ui-tester.md` followed by the assignment, and the report says which) with: URL
  `http://127.0.0.1:8000/admin/users`, flow "the users table shows the columns id, name, email,
  password_hash, created_at and three rows", evidence directory as above. The screenshot is
  supporting evidence a human can view; the `curl` count is the machine-checkable half.
- **Money and mutation.** U8 is a billed `claude -p` session (up to 3 USD), requires
  `./install.sh --check` exit 0 immediately beforehand (it preflights the installed copy), and
  may be run at most twice in this run. `./install.sh` installs the fifth agent machine-wide.
- Lessons carried: `-k` patterns are substrings of contract test names; the shell's working
  directory persists between tool calls, so a `cd` into a run directory breaks the next call's
  relative paths — commit from the repo root with absolute paths; every agent needs a `## Output`
  heading; the last two 55-turn runs of the workflow case finished with no headroom.

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
- No browser tools for `dod-auditor`; no change to any hook *script* (`.claude/hooks/*.py`);
  the test suites under `.claude/hooks/tests/` do change.
- No changes to `evals/csv-export-probe/fixture/`, no server wrapper script, no port
  negotiation: if 8000 is taken, free it or say so.
- No `.claude/launch.json` is created; the Scout branch exists for projects that already have one.
- `ui-tester` gets no `tools:` line and is not added to `EXPECTED_TOOLS`; the tool-pinning
  test is not extended.
- No new skill directory; the skill count stays 8. The ≤ 5 / half-scale limits are prose.
- No release lane; no CI.

## Definition of Done
- [ ] U1 Grammar. The masterprompt skill carries the `ui` contract form and the craft bullet
      with the `not reproducible in CI` flag.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_grammar` prints `Ran 1 test` and `OK`
      contract: tests/test_structure.py · test_ui_grammar_in_masterprompt ·
      expected RED: `AssertionError: 'contract: ui ·' not found in …`
- [ ] U2 TDD and Scout. `gentic-tdd` has `## UI tasks`; `gentic-scout` has the runnable
      product variant, gated on a user-facing surface, with a feature inventory.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_tdd -k ui_scout` prints `Ran 2 tests` and `OK`
      contract: tests/test_structure.py · test_ui_tdd_names_ui_tasks, test_ui_scout_walks_the_product ·
      expected RED: `AssertionError: '## ui tasks' not found in …`
- [ ] U3 Iterate uses the agent. `gentic-iterate` names `ui-tester` for the screenshot half.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_iterate` prints `Ran 1 test` and `OK`
      contract: tests/test_structure.py · test_ui_iterate_dispatches_the_tester · expected RED:
      `AssertionError: 'ui-tester' not found in …`
- [ ] U4 The agent exists. `ui-tester.md` as in Context; the agent set is exactly five; it
      has a `## Output` heading; its description starts with `Use when`; no `tools` key.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_agent -k expected_agents -k states_what_it_returns` prints `Ran 3 tests` and `OK`
      contract: tests/test_structure.py · test_ui_agent_is_defined (plus the two existing
      tests, `EXPECTED_AGENTS` updated first) · expected RED: `AssertionError: agent set drifted: {…}`
      and `AssertionError: False is not true : ui-tester.md missing`
- [ ] U5 README. The five-subagents paragraph, the agents row, the unpinned-tools sentence and
      the `## UI contracts` section.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ui_readme` prints `Ran 1 test` and `OK`
      contract: tests/test_structure.py · test_ui_readme_documents_contracts · expected RED:
      `AssertionError: '## ui contracts' not found in …`
- [ ] U6 Harness green. `bash .claude/hooks/tests/run.sh` exits 0 and prints
      `ok    test_structure (Ran`; if only a latency-budget line fails on a loaded machine,
      re-run once and note it — that is not a U6 failure.
      verify: `bash .claude/hooks/tests/run.sh`
      contract: n/a — the runner of U1–U5's tests.
- [ ] U7 Live dispatch — flagged `not reproducible in CI`, exactly as the new grammar
      requires of a project with no e2e runner. Verified by the main thread before Iterate;
      `dod-auditor` verifies the artifact only: the pasted report block in `progress.md`, the
      screenshot file on disk, and the pasted `curl` count. Pass condition: `./install.sh` then
      `--check` exit 0; `curl -s http://127.0.0.1:8000/admin/users | grep -o '<tr>' | wc -l`
      → 4; the report has `status: verified`, `observed` names all five columns and three rows
      consistent with the count, and `screenshot:` names a file under
      `docs/gentic/2026-09-02-ui-contracts/evidence/` for which
      `test $(stat -f%z <path>) -lt 409600` holds. If the agent was dispatched through
      `general-purpose` with the definition inlined, the report says so.
      verify: the commands above; paste the report and the counts
      contract: n/a — a live observation; the check is the pasted report and the file, not a test.
- [ ] U8 Regression gate. With `./install.sh --check` exit 0 immediately before:
      `python3 evals/run.py --case csv-export-probe --arm with` prints the with-arm line with
      `4/4 (1.00)` and **no ` exhausted` flag**, and `result.json` shows `exhausted: false`.
      A lower score, or an exhausted flag, is a rung-1 entry; at most two invocations.
      verify: run it; paste suite id, cost, turns, exhausted
      contract: n/a — a live observation; n=1.

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

## Critique record
`masterprompt-critic` (cold read): 3 blocking, 15 serious, 10 minor. All fixed inline: the
Scout variant gated on a user-facing surface; an explicit test table with `Ran N tests` in
every verify (`-k` exits 0 on zero matches); `##` headings for the agent body; the byte check;
`csv-export-probe` and its baseline named; hook scripts vs test suites; the README's
five-subagents paragraph and the unpinned-tools sentence; U7 flagged `not reproducible in CI`
and verified by the main thread with a `curl` count as the machine-checkable half; `n/a`
contract wording; U8 rejects an exhausted run and states cost, install precondition and a
two-run cap; non-goals for the fixture, a wrapper, `launch.json`, the `tools:` line, a sixth
skill, prose limits; the agent's ToolSearch-then-fallback path; port check and stop command;
the machine-wide install stated; `mkdir -p`; Python and `-k` semantics; `Use when` for the
description; the no-real-data rule in both the agent and Scout.
