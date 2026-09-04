# Run: release-lane
Goal: After the PR opens, the run watches CI, feeds failures back as rung-1 fixes, deploys a preview and smokes it, and merges on green — each step gated by the project's grants — with a deterministic helper over `gh` and, for this repository, its first CI workflow.
Iteration budget: 13 remaining (rungs spend it; task sizes never do)

## Phases
- [x] 1 Scout
- [x] 2 Interview (user delegated; the request itself is the "on request" for CI in this repo)
- [x] 3 Masterprompt (critic: 4 blocking / 14 serious / 11 minor, all fixed inline)
- [x] 4 Execute
- [ ] 5 Iterate

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
