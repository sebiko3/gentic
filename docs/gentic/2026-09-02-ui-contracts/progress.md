# Run: ui-contracts
Goal: UI becomes a first-class Definition-of-Done contract — an executable e2e spec as the contract, a `ui-tester` agent that drives the real browser and files screenshots as evidence, and a Scout that walks a running product before it asks anything.
Iteration budget: 11 remaining (2 spent: rung 1 on U7's screenshot method, rung 1 on U8's turn budget) (rungs spend it; task sizes never do)

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
