# Run: sqlite-brain
Goal: Give gentic a persistent SQLite brain — structured memory (lessons, decisions, runs, events, stamps) plus free-form notes with full-text recall and unrestricted SQL — written to by the hooks and read by the phase skills.
Iteration budget: 11 remaining (2 spent: two rung-1 fixes after the audit) (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 6 blocking / 15 serious / 8 minor, all fixed inline; second cold read clean)
- [x] 4 Execute (6 tasks, 6 checkpoint commits, every RED cell filled)
- [x] 5 Iterate (13/13 DoD proven after two rung-1 fixes; 11 of 13 points remain)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | `lib/brain.py` core: schema, project key, note/recall (FTS + LIKE), sql with .bak, record_event with scrubbing (D1, D2, D6 storage) | 5 | — | `tests/test_brain.py::test_note_then_recall_finds_it`, `::test_recall_falls_back_to_like`, `::test_sql_is_unrestricted_inside_the_brain`, `::test_sql_destructive_statement_leaves_a_backup` | `AssertionError: 2 != 0 : brain CLI did not run: … can't open file '…/lib/brain.py'` (all four) | done |
| 2 | Hook wiring (post_tool_use, stop) + invisibility guard + third latency median (D6, D7, D12 latency) | 3 | 1 | `::test_hooks_write_events_to_the_brain`, `::test_brain_failure_is_invisible_to_hooks` | `AssertionError: 0 != 1 : no red event in brain`; after wiring, unguarded: `AssertionError: 'hook error' unexpectedly found in '{"systemMessage": "hook error (__main__): [Errno 20] Not a directory: …"}'` | done |
| 3 | decide/preference, lesson/lessons/stats, run/stamp, scoping (D3, D4, D5, D9) | 5 | 1 | `::test_preference_needs_two_agreeing_user_decisions`, `::test_lessons_recorded_and_summarised`, `::test_run_lifecycle_and_stamps`, `::test_lessons_default_to_current_project` | `AssertionError: 2 != 0 : brain CLI did not run: usage: brain.py [-h] [--project PROJECT] {note,recall,sql} …` (all four) | done |
| 4 | session_start brain line (D8) | 2 | 3 | `::test_session_start_mentions_brain_when_it_has_something` | `AssertionError: 'brain:' not found in ''` | done |
| 5 | `gentic-brain` skill, wiring into six skills, structure test, run.sh count + registration + isolation (D10, D12) | 3 | 1 | `tests/test_structure.py::test_brain_skill_is_wired_into_the_phases`, `tests/test_brain.py::test_harness_registers_and_isolates_the_brain_suite` | `AssertionError: False is not true : skills/gentic-brain/SKILL.md missing`; `AssertionError: 'test_brain' not found in 'for suite in test_lib … test_project_conventions; do'` | done |
| 6 | README + hooks README + installer test (D11, D13) | 2 | 1-5 | `::test_docs_document_the_brain`, `tests/test_install.py::test_source_list_includes_the_brain` | `AssertionError: '## The brain' not found in '# gentic…'`; `AssertionError: 'skills/gentic-brain/SKILL.md' not found in 'out of sync with …'` (observed before task 5's commit) | done |

Sizes are planning estimates only; they never spend the iteration budget. Order: 1, 2 (riskiest: hot-path latency), 3, 4, 5, 6.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | D1–D8, D10, D11, D13 | — | 0 | PROVEN by `dod-auditor` (fresh `GENTIC_BRAIN` per check): `-k recall` 2 OK · `-k sql` 2 OK · `-k preference` 1 OK · `-k lesson` 2 OK · `-k run_lifecycle` 1 OK · `-k hooks_write` 1 OK + `test_gate` 19 OK · `-k invisible` 1 OK · `-k session_start` 1 OK · `test_structure` 29 OK · `-k docs` 1 OK · `git ls-files -- .claude \| grep -c brain` → 3, `test_install` 16 OK |
| 2 | D12 harness exits 0 | 1 | 1 | FAILED then fixed. Root cause: `session_start.py:64` emitted `python3 "$HOME/.claude/hooks/lib/brain.py" …` — the literal D8 names — and the harness isolation grep (`run.sh` "hooks never write into a project's .claude directory") rejects any hook line with a double-quoted `.claude` path lacking `Path.home()`. The masterprompt's own Context predicted this collision and D8 ignored it. Fix: the notice now prints `python3 ~/.claude/hooks/lib/brain.py recall <words>` (single-quoted literal; the README's own form). D8's contract test still passes; D8's quoted wording is deviated from and recorded here, not edited. First retry still failed (double-quoted Python literal); second retry green. |
| 3 | D9 `-k scoping` runs no tests | 1 | 1 | FAILED then fixed. Root cause: the verify pattern `scoping` and the contract's test name `test_lessons_default_to_current_project` disagreed — a spec typo the critique pass missed. The test is renamed `test_scoping_lessons_default_to_current_project`, so the verify command runs it and the contract name survives as a substring. DoD text untouched. `-k scoping` → `Ran 1 test OK`. |

## Notes / handoff
- Child run R1 of the epic `2026-09-02-self-improving-gentic`; its brief and decisions apply.
- Stale line references in `masterprompt.md` Context (isolation grep cited at run.sh 87-96, skill
  count at 147; live file: 110-119 and 152). Noted, not a DoD item; the same drift produced D9.

## Final report

**Mission.** gentic has a persistent brain: `~/.claude/gentic/brain.sqlite` (`GENTIC_BRAIN`
overrides), stdlib `sqlite3`, WAL, FTS5 with a `LIKE` fallback. The hooks append `red`,
`verification`, `gate_block` and the three nudge kinds on their own, best-effort and invisible
on failure; the phase skills note, recall, decide, learn preferences, record lessons, stamp
skill versions and open/close runs through `python3 ~/.claude/hooks/lib/brain.py`; `sql` is
unrestricted with a `.bak` before destructive statements. Installed live via `./install.sh`
(17 files; `--check` in sync).

**13 of 13 DoD items proven**, all re-run fresh at the final gate after the rung fixes:
`test_brain` 13 OK · every `-k` verify command OK (recall 2, sql 2, preference 1, lesson 2,
run_lifecycle 1, hooks_write 1, invisible 1, session_start 1, scoping 1, docs 1) · `test_gate`
19 OK (unchanged) · `test_structure` 29 OK · `test_install` 16 OK · `run.sh` exit 0, all checks
passed, medians 23.4 / 25.0 / 30.4 ms · `git ls-files -- .claude | grep -c brain` → 3.

**Budget: 11 of 13 remaining.** The `dod-auditor` failed two items on its first pass, both
fixed at rung 1 (iteration log #2, #3). Every task went RED first; evidence in the task table.

**The brain's first contents, written by this run (dogfood):** `run start/finish sqlite-brain`,
stamps of eight skills and four agents, two `user` decisions and two `default` decisions, two
lessons (`caught_by auditor`), two notes, and the events the hooks recorded during the session.

**Unconfirmed defaults** (all `user — delegated` under blanket trust; listed so they can be
reversed): machine-wide location with env override; project key = git root basename (same-named
repos share memory); preferences learned across projects, latest user answer wins once chosen
twice, defaults never teach; hooks write only from `post_tool_use` and `stop`; 34 ms lock timeout;
free SQL with a single-level `.bak`; no schema migrations; no retention policy; an eighth skill
rather than folding the brain into `gentic`.

**Deviation recorded, not hidden.** D8's text names the notice literal
`python3 "$HOME/.claude/hooks/lib/brain.py" recall <words>`; the shipped notice prints
`python3 ~/.claude/hooks/lib/brain.py recall <words>` because the harness forbids the quoted
form inside a hook. The contract test passes; the DoD text was not edited.

**Deliberately not done** (non-goals held): no consumer of `events`, no dashboard, no evals,
no gardener, no retro.md, no adjective catalogue, no `zcontext` migration, no MCP server, no
embeddings, no import of old run artifacts, no PATH alias, no CI, no push, no PR.

**Branch.** `gentic/self-improving-gentic` holds the epic gates and this run's eight commits;
kept as-is for `/ship` (never pushed by a run).
