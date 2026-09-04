# Run: release-lane
Goal: After the PR opens, the run watches CI, feeds failures back as rung-1 fixes, deploys a preview and smokes it, and merges on green — each step gated by the project's grants — with a deterministic helper over `gh` and, for this repository, its first CI workflow.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated; the request itself is the "on request" for CI in this repo)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 11 minor, all fixed inline)
- [x] 4 Execute
- [x] 5 Iterate (dod-auditor: 8 proven, 0 failed, 0 unverifiable; no rung spent)

## Tasks
| # | Task | Size | Depends on | Test | RED | Status |
|---|------|------|------------|------|-----|--------|
| 1 | Fake `gh` harness; `release.py` `checks` and `wait` (L1, L2) | 3 | — | `tests/test_release.py::test_checks_reports_buckets_and_exit_codes`, `::test_wait_polls_until_settled`, `::test_wait_times_out`, `::test_wait_stops_on_a_hard_error` | `AssertionError: 2 != 0 : checks did not run: … can't open file '…/lib/release.py'`; `AssertionError: 2 != 0 : wait did not run`; `2 != 6`; `2 != 4` | done |
| 2 | `failed-logs`; `merge` with four gates (L3, L4) | 3 | 1 | `::test_failed_logs_prints_the_failing_job`, the five `::test_merge_*` | `AssertionError: 2 != 0 : failed-logs did not run`; `AssertionError: 2 != 1 : merge did not refuse`; `2 != 1` (×3); `2 != 0` (merges) | done |
| 3 | Wording in ship.md (four sites), gentic-iterate, README; `ReleaseLane` tests (L5) | 2 | — | `tests/test_structure.py::ReleaseLane` (3) | `AssertionError: '--through' not found in '---\ndescription: verify, review, commit, push and open a pr…'`; `'--through' not found in … gentic-iterate`; `'## the release lane' not found in …` | done |
| 4 | Workflow file, `run.sh` registration, harness, install (L6) | 2 | 1-3 | `::test_workflow_runs_the_harness_and_no_evals`, `::test_harness_registers_release_suite`; `run.sh`; `install.sh --check` | `AssertionError: False is not true : .github/workflows/gentic.yml missing`; `AssertionError: 'test_release' not found in 'for suite in …'` | done |
| 5 | Preconditions; push; live watch; live refusal (L7, L8) | 3 | 4 | n/a — live observations | n/a — live observations, no test contract; the evidence is pasted below | done |

Sizes are planning estimates only; they never spend the iteration budget. Order 1–5.

## Iteration log
| # | DoD item | Rung | Points | Result |
|---|----------|------|--------|--------|
| — | none | — | 0 | The audit proved L1–L8 on the first pass; 13 of 13 points remain. |

## Notes / handoff
- Child run R7 of the epic `2026-09-02-self-improving-gentic` (brief item 12). PR #2 is the live
  target; this repo grants nothing and is untrusted, so the gated steps are exercised as refusals.

## Task 5 preconditions (pasted)
`gh auth status` → `Token scopes: 'gist', 'read:org', 'repo', 'workflow'`.
`gh pr view 2 --json state,headRefName,isDraft,mergeable` → `OPEN`, `gentic/self-improving-gentic`, draft false, `MERGEABLE`.
Remote `https://github.com/sebiko3/gentic.git`. Push of the workflow commit: exit 0.

## L8 live refusal (pasted verbatim)
```
state before: OPEN
$ python3 .claude/hooks/lib/release.py merge --pr 2
not authorized: merge-on-green          # stderr
merge exit: 1
state after: OPEN
```
That no `gh pr merge` was issued is proven by L4's tests, not observed here.

## L7 live watch (pasted verbatim, 2026-09-04 11:14 CEST)
Push of the workflow commit `5330676`: `74b3ca6..5330676  gentic/self-improving-gentic -> gentic/self-improving-gentic`, exit 0.
```
$ python3 .claude/hooks/lib/release.py wait --pr 2 --timeout 1597 --interval 21
   0s  pass: 0  fail: 0  pending: 0  skipping: 0  cancel: 0  (no checks yet)
  22s  pass: 0  fail: 0  pending: 1  skipping: 0  cancel: 0
  45s  pass: 0  fail: 0  pending: 1  skipping: 0  cancel: 0
  67s  pass: 1  fail: 0  pending: 0  skipping: 0  cancel: 0
wait exit: 0
```
Green on the first run — no rung-1 fix was needed, no `failed-logs` output to paste.
`release.py checks --pr 2` afterwards: `pass  harness  https://github.com/sebiko3/gentic/actions/runs/33857348579/job/100973606191`, exit 0.

## Audit (dod-auditor, 2026-09-04)
L1–L6: every `unittest -k` run printed the exact `Ran N` count the item names (1/3/1/5/3/2) and `OK`;
`run.sh` exit 0 with `ok    test_release (Ran 12 tests)` and `all checks passed`; `./install.sh --check`
→ `in sync`. L7: pasted poll lines judged; `checks --pr 2` re-observed → one `pass` on run
33857348579, exit 0 (the `wait` exit itself is the run's observation, corroborated not re-run).
L8: re-observed live — `OPEN`, stderr `not authorized: merge-on-green`, exit 1, `OPEN`.
No DoD item edited, nothing merged, no evals, no trust-file write.

## Final report

**Mission.** `/ship` no longer ends at the open PR. `release.py` turns CI state into exit codes
(`checks`, `wait`, `failed-logs`) and holds the only merge path (`merge`, gated by the
`merge-on-green` grant, the repo's own identity, the PR's state and green checks). `ship.md` §8
`--through ci|preview|merge` describes the lane, Iterate continues into it when `push` and
`open-pr` were granted, and this repository has its first CI workflow: the hook harness on every
push. Watched live: the workflow commit went from push to green in 67 s at a 21 s poll, and the
merge on PR #2 was refused because this repository grants nothing.

**DoD: 8 of 8 proven.** Zero rungs spent; 13 of 13 iteration points remain. Twelve new tests in
`test_release.py` over a fake `gh`, three in `ReleaseLane`; the harness holds 50 + 12 + the
earlier suites and stays under the 150 ms hook budget.

**What closing taught** (brain): the first real CI run needed no fix, so the two-fix rule is
untested live and stays proven only by `test_wait_*`; the decisions table drifted from the spec
between Interview and Masterprompt (3.11/`pull_request` vs 3.12/`push`+`workflow_dispatch`) and
was corrected at close — the masterprompt is the record, the decisions table a summary of it.

**Spent.** 0 USD: no eval runs; CI on GitHub's hosted runner.

**Unconfirmed defaults** (`user — delegated`): the helper's home in `lib/release.py` and its four
modes; `--merge` with the branch kept; preview described, not implemented; read-only modes
ungated and `merge`/preview gated; at most two rung-1 CI fixes per ship; poll 21 s, timeout
1597 s, 89 log lines; Python 3.12 on `ubuntu-latest`; no `pull_request` trigger.

**Deliberately not done.** No preview deploy (nothing in this repo deploys); no merge of PR #2
(no grant, and closing or merging it is the user's); no branch protection, badge, matrix,
caching or CI eval runs; no `gentic-release` skill.

**Next.** `gentic-epic` (the decomposition orchestrator), then `orchestrator-mesh`, `gardener`,
`adjective-compiler-and-retro`. If autonomous pushes and merges are wanted, the user writes
`~/.claude/gentic/trusted-projects` and the grants in `CLAUDE.md`; nothing in gentic will.
