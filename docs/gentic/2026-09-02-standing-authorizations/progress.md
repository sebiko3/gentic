# Run: standing-authorizations
Goal: A per-project consent layer — a `## gentic authorizations` section in the project's CLAUDE.md, read by a deterministic helper, that lets a run push and open a PR only when granted; plus a concurrency valve on subagent spawns and a STOP flag every phase honours.
Iteration budget: 13 of 13 remaining — no escalation rung was spent.

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated all decisions; recorded as `user — delegated`)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 8 minor, all fixed inline; trust file added)
- [x] 4 Execute (5 tasks, 5 checkpoint commits, every RED cell filled)
- [x] 5 Iterate (7/7 DoD proven by dod-auditor; 13 of 13 points remain)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Helper `authorized` mode with the trust file; parser shape (H1, H2) | 3 | — | `tests/test_project_conventions.py::test_authorized_reads_the_section`, `::test_authorized_fails_closed`, `::test_branch_and_commit_still_need_a_slug` | `AssertionError: 2 != 0 : authorized push`; `AssertionError: 2 != 1 : untrusted must be a no` (the slug test passed on arrival: it pins existing behaviour) | done |
| 2 | Session lock, valve in both hooks, reset per prompt (H3) | 3 | — | `tests/test_guard_and_session.py::test_concurrency_valve_denies_a_sixth_agent`, `::test_valve_counts_parallel_spawns`, `::test_valve_resets_on_a_new_prompt` | `AssertionError: None != 'deny' : sixth spawn was not denied`; `AssertionError: 0 != 5 : parallel spawns lost updates` (the reset test passed on arrival: nothing was counted yet — it pins the boundary) | done |
| 3 | Installer block, live settings, harness matcher assertion (H5) | 2 | 2 | `tests/test_install.py::test_settings_block_matcher_covers_subagents` | `AssertionError: 'Task|Agent' not found in '    "PreToolUse":      [{"matcher": "Bash|Read|Edit|Write|MultiEdit|NotebookEdit|NotebookRead",'` | done |
| 4 | Wording in eight sites + structure tests (H4) | 3 | 1 | `tests/test_structure.py::StandingAuthorizations` (8) | eight failures, e.g. `AssertionError: '## gentic authorizations' not found in '# gentic routing…'`, `'authorized open-pr' not found in …`, `'trusted-projects' not found in …` | done |
| 5 | Harness, install, regression run, repo state (H6, H7) | 2 | 1-4 | n/a — live observations | n/a — the observations are the evidence (below) | done |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–5.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| 1 | H1–H6 | — | 0 | PROVEN by `dod-auditor`: `-k authorized_reads` 1 OK · `-k fails_closed -k need_a_slug` 2 OK · `-k valve` 3 OK · `-k StandingAuthorizations` 8 OK · matcher test 1 OK + live matcher `…|Task|Agent` · `run.sh` exit 0, four suite lines, Configuration ran, zero `skip` |
| 2 | H7 | — | 0 | PROVEN — `result.json` 4/4 graders passed, exit 0, cost 2.6177; helper outputs from the repo root match the paste byte for byte; `install.sh --check` in sync. Caveat recorded: n=1; `num_turns` 72 vs `--max-turns` 55 (brain note). |

## Notes / handoff
- Child run R5 of the epic `2026-09-02-self-improving-gentic` (brief items 14 and 16; item 15,
  budget as a currency, moves to `gentic-epic` where its consumer lives). Brain consulted: no
  prior notes on authorizations, pushes or concurrency.

## H6 harness (after tasks 1–4)
`bash .claude/hooks/tests/run.sh` → exit 0, `all checks passed`; `ok    test_guard_and_session (Ran 16 tests)`,
`ok    test_install (Ran 17 tests)`, `ok    test_structure (Ran 41 tests)`, `ok    test_project_conventions (Ran 26 tests)`;
medians 34.6 / 37.3 / 44.3 ms; Configuration section ran (`ok    PreToolUse matcher covers Bash/Read/Edit/Write/Task`).

## H7 this repo's state (from the repo root, install in sync)
```
$ python3 .claude/hooks/lib/project_conventions.py authorized --list
project not trusted: /Users/sebiko83/code/gentic (add its path to /Users/sebiko83/.claude/gentic/trusted-projects)   # stderr
(nothing on stdout) exit 0
$ python3 .claude/hooks/lib/project_conventions.py authorized push
project not trusted: …   # stderr
no
exit 1
```
Live `~/.claude/settings.json` PreToolUse matcher: `Bash|Read|Edit|Write|MultiEdit|NotebookEdit|NotebookRead|Task|Agent`
(backup `settings.json.bak-20260902-205111`).

## H7 regression gate — suite 20260902-205323 (pasted verbatim)
`./install.sh --check` → `in sync with /Users/sebiko83/.claude`, exit 0.
`python3 evals/run.py --case csv-export-probe --arm with` (20:53–21:06):
```
csv-export-probe              with 4/4 (1.00)  $2.62
suite 20260902-205323       with 1.00  $2.62  exit 0
```
`result.json`: cost 2.6177, exhausted false, no failing grader; `num_turns` 72 with `--max-turns 55`
and subtype `success` — the CLI's turn count and its limit count different things (brain note).
The eval workspace's `CLAUDE.md` is this repo's (grants nothing) and its path is not trusted, so
the new Iterate step printed `no` and the run did not push. Verbatim from the transcript's final
message: "Not pushed or opened as a PR — this repo isn't in your trusted-projects list, so per your
`CLAUDE.md` that stays a manual step (`/ship` when you're ready)." (`authorized push` ×5,
`authorized open-pr` ×4, `not trusted` ×1, `git push` ×0, `gh pr create` ×0 in the transcript.)

## Final report

**Mission.** A project can grant gentic standing permissions in its own `CLAUDE.md`, and the
grant counts only when the user has also listed the project's git-root path in
`~/.claude/gentic/trusted-projects` — a clone can never grant itself. `project_conventions.py
authorized <action>` answers `yes`/`no` and fails closed on anything missing. A run whose
project grants `push` and `open-pr` now ends its Iterate phase by following `/ship`'s steps
(commit the report first; preconditions, branch guard, verify, review, push, PR; findings to the
PR body) and reporting the PR URL; every other project behaves exactly as before, as the
regression run showed by declining to push. A hook refuses a sixth concurrent foreground
subagent (locked counter, reset per prompt, background spawns uncounted), and a `STOP` file in
the run directory halts a run before the next task or rung.

**DoD: 7 of 7 proven.** Budget 13 of 13. Five tasks, each RED first.

**Regression gate.** `csv-export-probe` with arm 4/4 (1.00) at 2.62 USD with the new wording
installed; the run consulted the helper, got `no`, and stopped where `/ship` would begin.

**Machine changes outside the repo.** `~/.claude/settings.json` PreToolUse matcher gained
`|Task|Agent` (backup `settings.json.bak-20260902-205111`); the installed skills, command,
hooks and helper were re-synced. No trust file was created: this repository is not trusted and
grants nothing.

**Unconfirmed defaults** (`user — delegated`): the two-factor trust model and the trust file's
location; the six-word vocabulary with four inert reserved words; fail-closed semantics;
`/ship` steps 1–4 and 6 as the consumer with `dod-auditor` skipped at ship time; valve at 5,
foreground only; `STOP` untracked; budget currency deferred to `gentic-epic`.

**Stated and unexercised.** No agent session pushed to a remote in this run: the deterministic
half (grant + trust ⇒ `yes`) is unit-tested, the prose half is contract-tested, and the first
real push under a grant belongs to the release lane (R6), which owns CI and can watch it land.

**Deliberately not done.** No consumer for `merge-on-green`, `deploy-preview`,
`use-workflow-tool`, `spawn-teams`; no `/gentic` command file; no hook for STOP; no eval case
for authorizations; no CI.

**Branch.** `gentic/self-improving-gentic`, eight `gentic(standing-authorizations)` commits;
kept as-is for `/ship`.
