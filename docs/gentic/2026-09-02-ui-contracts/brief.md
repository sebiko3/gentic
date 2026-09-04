# Brief: ui-contracts

## Mission (as understood)
"Make this app more awesome" is mostly a claim about what a person sees and clicks, and gentic
today cannot make such a claim verifiable: no Definition-of-Done grammar for a UI flow, no
agent that can look at a screen, no Scout that opens the product before asking about it.
This run adds the three: a `ui` contract form whose executable half is the project's e2e
runner, a `ui-tester` agent that drives the real browser and files screenshots under the run
directory as evidence, and a "runnable product" variant of Scout that starts the app, walks
its routes and puts a feature inventory with screenshots into the brief.

## Facts
- Subagents inherit both browser tool sets (probed with a Haiku subagent): all
  `mcp__claude-in-chrome__*` and all `mcp__Claude_Browser__*` tools are available to an agent
  that does not restrict `tools:`, without a ToolSearch step. The main thread must load the
  Chrome tools with one ToolSearch call first.
- The user has the Claude in Chrome extension and asked that it be used; the in-app Browser
  pane is the fallback and is the one that can start a dev server (`preview_start`).
- `post_tool_use.py` already counts `playwright|cypress|lighthouse|axe` runs as verification
  evidence (R2, E8).
- `gentic-masterprompt/SKILL.md:37` defines the contract grammar
  (`contract: <test file> · <test name> · <behaviour asserted> · expected RED: …`); `:50`
  requires every item to name one; docs/prompts get contract tests; `n/a` only for the
  unobservable. `gentic-tdd` says a test must fail first and names RED as evidence in
  `progress.md`. `gentic-scout:21` has a Greenfield variant but nothing for a runnable product.
- `test_structure.py:23` pins `EXPECTED_AGENTS` to four; `:127` requires every agent to have
  an Output/Returns section; `:114` pins the three reviewers' tool sets (a new agent is not in
  that map). The README has an agents table.
- `dod-auditor` runs commands via `Bash`; it cannot look at a screen. Its tool set is pinned.
- The CSV fixture (`evals/csv-export-probe/fixture/app.py`) serves `/admin/users` on
  `127.0.0.1:8000` with stdlib only — a ready-made target for a live browser check.
- Screenshots: `computer` with `save_to_disk: true` returns a saved path (Chrome tools);
  the in-app Browser's `screenshot` returns an image only. Run artifacts are committed
  (CLAUDE.md Conventions), so evidence PNGs would be too.

## Patterns to follow
- Agents earn their place by being worse informed in a useful way: `ui-tester` sees the URL,
  the flow and nothing else — no spec, no diff — so it reports what the screen shows.
- Contract tests for wording; one live regression of the workflow case after skill edits.
- Fixed report blocks for agents (`task-executor`'s shape).

## Constraints discovered
- No Playwright in this repository and no eval fixture that can install it; the executable
  half of a `ui` contract is the *project's* runner, whatever it is, and the runner name is
  what the hooks recognise.
- Evidence PNGs land in git; keep them small (Chrome `scale: 0.5`) and few.
- The live proof needs a running app on this machine and a connected Chrome.

## Open decisions (all resolved by delegation — see decisions.md)
1. Browser — Claude in Chrome first, in-app Browser as fallback. **User's choice.**
2. Contract form — `contract: ui · <spec file> · <test name> · <flow asserted> · expected RED: <locator/assertion failure>`; without an e2e runner the contract is a `ui-tester` verification with a screenshot and is flagged `not reproducible in CI`. Default: as stated.
3. Evidence location — `docs/gentic/<run>/evidence/`, committed, ≤ 5 screenshots per run. Default: as stated.
4. Fifth agent — `ui-tester`, tools unrestricted (needs the MCP browser tools), forbidden by instruction from editing code. Default: as stated.
5. Scout variant — "runnable product": start the app if a run instruction exists, walk ≤ 8 routes, screenshot each, inventory in the brief; time-boxed to 13 tool calls. Default: as stated.
6. Proof — live `ui-tester` dispatch against the CSV fixture served locally, plus the workflow-case regression. Default: as stated.
