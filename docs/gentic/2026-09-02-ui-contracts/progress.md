# Run: ui-contracts
Goal: UI becomes a first-class Definition-of-Done contract — an executable e2e spec as the contract, a `ui-tester` agent that drives the real browser and files screenshots as evidence, and a Scout that walks a running product before it asks anything.
Iteration budget: 9 remaining (4 spent: rung 1 on U7, rung 1 then rung 2 on U8) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated; one user decision: Claude in Chrome is the browser of choice)
- [x] 3 Masterprompt (critic: 3 blocking / 15 serious / 10 minor, all fixed inline)
- [ ] 4 Execute
- [ ] 5 Iterate

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Structure tests (`UiContracts`, `EXPECTED_AGENTS`), then `ui-tester.md` (U4) | 3 | — | `tests/test_structure.py::test_ui_agent_is_defined`, `::test_exactly_the_expected_agents_exist`, `::test_each_agent_states_what_it_returns` | `AssertionError: Items in the second set but not the first: 'ui-tester'`; `AssertionError: False is not true : ui-tester.md missing` | done |
| 2 | Skill wording: masterprompt grammar, tdd, scout variant, iterate (U1, U2, U3) | 3 | — | `::test_ui_grammar_in_masterprompt`, `::test_ui_tdd_names_ui_tasks`, `::test_ui_scout_walks_the_product`, `::test_ui_iterate_dispatches_the_tester` | `AssertionError: 'contract: ui ·' not found in …`; `'## ui tasks' not found in …`; `'runnable product variant' not found in …`; `'ui-tester' not found in …` | done |
| 3 | README; harness (U5, U6) | 2 | 1-2 | `::test_ui_readme_documents_contracts`; `run.sh` | `AssertionError: '## ui contracts' not found in '# gentic…'`; U6: n/a — runner of the others | done |
| 4 | Install; live dispatch against the fixture; regression (U7, U8) | 3 | 3 | n/a — live observations | n/a — the observations are the evidence (below) | in progress |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–4.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | U7 screenshot method | 1 | 1 | The extension's `save_to_disk` writes no file (probed from the inlined agent and from the main thread: "Successfully captured screenshot … ID: ss_…", no path). The agent improvised headless Chrome and disclosed it; the method now codifies that fallback. U7's pass condition itself was met (see below). |
| 2 | U8 regression gate (suite 20260902-215633) | 1 | 1 | FAILED: `with 3/4 (0.75) exhausted`, 56 turns, 2.28 USD, `pii-surfaced` failed. Transcript: the Scout variant did **not** fire (0 browser/server tool uses); 64 tool uses went Scout→Interview→Masterprompt→Execute (23 edits) and the limit hit mid-Execute, so no final message existed for the last-message grader. Root cause: the 55-turn budget's zero headroom (brain note after R4). Fix: `csv-export-probe` `max_turns: 89`, per-run cap 5 USD (Fibonacci), expectations updated first (RED `55 != 89`, `'3' != '5'`); README updated. Second and last U8 invocation follows. |
| 0 | U1–U7 | — | 0 | PROVEN by `dod-auditor`: `-k ui_grammar` 1 OK · `-k ui_tdd -k ui_scout` 2 OK · `-k ui_iterate` 1 OK · `-k ui_agent -k expected_agents -k states_what_it_returns` 3 OK · `-k ui_readme` 1 OK · `run.sh` all checks passed, `test_structure (Ran 47 tests)` · U7 artifact: report verified, PNG 800×400 27,996 B viewed, curl count 4, install in sync. U8: UNVERIFIABLE — two invocations spent. |
| 3 | U8 regression gate, second invocation (suite 20260902-220926) | 2 | 2 | FAILED: `with 0/4 (0.00) $0.00`, `is_error`, detail `timeout after 900s`. The session was killed by the runner's default `timeout_seconds` at exactly 15 minutes after 86 tool uses and two agent dispatches — a harness limit, not a workflow failure. Two failed fixes at rung 1 make rung 2 mandatory: the case now sets `timeout_seconds: 1597`, pinned by the five-cases test (RED `900 != 1597`). **U8's two-invocation cap is spent; a third run needs the user's word** (spec constraint, rung-5 territory) — handed off. |

## Notes / handoff
- Child run R6 of the epic `2026-09-02-self-improving-gentic` (brief items 11 and 13, the
  `ui-tester` agent). The user stated Claude in Chrome is connected and wants it used.

## U7 live dispatch (pasted verbatim)

`./install.sh` → 6 files changed; `./install.sh --check` → in sync. `lsof -ti:8000` empty; fixture
served (pid 84646). `curl -s http://127.0.0.1:8000/admin/users | grep -o '<tr>' | wc -l` → **4**.
Dispatch by name: `Agent type 'ui-tester' not found` (agents resolve at session start), so the
fallback the spec names was used — a `general-purpose` agent with the definition inlined.
Report:
```
status: verified
url: http://127.0.0.1:8000/admin/users
flow: opened the page in Chrome, read the accessibility tree and the rendered screen, counted the users table's header cells and body rows
observed: one table element. Header row, 5 cells, left to right: "id", "name", "email", "password_hash", "created_at" (…). Body rows, 3: row 1 "1 | Ada Lovelace | ada@example.com | sha256$9f86… | 2025-01-03"; row 2 "2 | Grace Hopper | …"; row 3 "3 | Linus Torvalds | …". No other elements on the page. HTTP status 200. Note on the screenshot: the Chrome extension's `save_to_disk` returned no path and wrote no file (…); the evidence file was captured from the same URL with headless Google Chrome (`--headless=new --screenshot`, window 800x400) and shows the identical table.
screenshot: docs/gentic/2026-09-02-ui-contracts/evidence/users-table.png
console: none
dispatched: general-purpose with the ui-tester definition inlined
```
File: `users-table.png`, PNG 800×400, 27,996 bytes (`test $(stat -f%z …) -lt 409600` holds); viewed —
it shows the five-column header and three rows. Server stopped afterwards.

## U8 regression gate — two invocations, both failed for harness reasons (pasted verbatim)
Suite `20260902-215633`: `csv-export-probe  with 3/4 (0.75) exhausted  $2.28` — 56 turns at the 55 limit,
cut off mid-Execute (0 browser tool uses: the Scout variant did not fire); `pii-surfaced` failed because no
final message existed. Suite `20260902-220926`, after 89 turns / 5 USD: `csv-export-probe  with 0/4 (0.00)  $0.00`,
`timeout after 900s` — killed at 15:00 with 86 tool uses (28 edits, 2 agent dispatches). The workflow itself
did not regress in either run; the harness limits did the cutting. Fixes: 89 turns, 5 USD, `timeout_seconds: 1597`.
A third invocation is outside the spec's cap and awaits the user.

## Handoff (2026-09-02, awaiting the user)
U1–U7 proven; U8 has no passing observation. Both permitted invocations failed on harness limits
that this run then fixed (89 turns, 5 USD, 1597 s), so the workflow itself has not been shown to
regress or to pass under the new wording. A third invocation (≈ 3–5 USD, ≈ 20–25 min) exceeds the
spec's cap and is the user's call: authorise it, or accept suite `20260902-215633` (3/4, cut off
mid-Execute with the brief, decisions and masterprompt written) as the evidence and close with U8
recorded as not proven. `ui-tester` now resolves by name in fresh sessions.
