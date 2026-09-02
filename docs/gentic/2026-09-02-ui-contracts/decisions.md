# Decisions: ui-contracts

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Browser | **Claude in Chrome** (`mcp__claude-in-chrome__*`), in-app Browser (`mcp__Claude_Browser__*`) as fallback and for `preview_start`. | In-app Browser only | The user's real Chrome carries logged-in sessions; they asked for it. | user |
| Contract form | `contract: ui · <spec file> · <test name> · <flow asserted> · expected RED: <locator/assertion failure>`; executable half = the project's e2e runner (Playwright, Cypress…); no runner ⇒ a `ui-tester` verification with a screenshot, flagged `not reproducible in CI`. | Browser-only contracts | A contract must be reproducible where CI runs; a screenshot is evidence, not a test. | user — delegated |
| Evidence | `docs/gentic/<run>/evidence/`, committed with the run, screenshots at half scale, at most 5 per run. | Outside the repo; unlimited | Artifacts are documentation; PNGs must stay small. | user — delegated |
| `ui-tester` | Fifth agent; `tools:` unrestricted (browser MCP tools must reach it); forbidden by instruction from editing code; fixed report block. | Give `dod-auditor` browser tools | The auditor's tool set is pinned and its job is commands; looking is a separate, worse-informed role. | user — delegated |
| Scout variant | "Runnable product": if a run instruction exists, start the app, walk ≤ 8 routes, screenshot each, inventory the features in the brief; 13-tool-call time box. | Always; never | Questions asked from a screenshot are sharper; the box keeps Scout short. | user — delegated |
| Proof | Live `ui-tester` dispatch against the CSV fixture on `127.0.0.1:8000` (screenshot saved into this run's evidence), plus `csv-export-probe` with arm 4/4. | Offline only | An agent that has never opened a page is not proven; the probe guards the skill edits. | user — delegated |
| Adjective rubric for "awesome" | Deferred to the adjective-compiler run. | Add now | Separate mechanism. | user — delegated |
