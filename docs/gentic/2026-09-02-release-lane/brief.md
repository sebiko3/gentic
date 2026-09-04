# Brief: release-lane

## Mission (as understood)
`/ship` ends at "PR opened". The release lane continues from there without a human typing each
step: watch the PR's checks, read the failing job's log, feed it back as a rung-1 fix inside the
run's budget, deploy a preview when green and let `ui-tester` smoke it, and merge on green —
every step past "watch" gated by the project's standing authorizations. This repository has no
CI at all, so the lane's first live target is its own harness on GitHub Actions, on PR #2.

## Facts
- `gh` 2.74.0 is logged in; `gh pr checks <n> --json name,state,bucket,link,workflow,startedAt,completedAt`
  is supported; `bucket` is one of `pass|fail|pending|skipping|cancel`; `gh run view <id> --log-failed`
  prints failing steps' logs; `gh pr merge` merges. PR #2 (`gentic/self-improving-gentic` → `main`)
  is OPEN, MERGEABLE, with 0 checks; the repo is PUBLIC with Actions enabled; `.github/` does not exist.
- The harness `bash .claude/hooks/tests/run.sh` is the project's verification: 14 suites, stdlib,
  needs `python3`, `bash`, `jq` (Configuration section skips without a settings file), `git`
  (conventions tests create repos and commit; identity via `-c` in tests — verified below or
  supplied by the workflow), sqlite FTS5 optional (LIKE fallback tested). Latency budgets are 150 ms
  medians; CI runners may be slower than this laptop (≈ 30–45 ms here).
- Standing authorizations (R5): `project_conventions.py authorized <action>` fails closed; words
  `merge-on-green` and `deploy-preview` are reserved with no consumer; this repo grants none and is
  not in the trust file. `/ship` §7: never merge. `gentic-iterate` follows `ship.md` steps 1–4 and 6
  when `push` and `open-pr` are granted.
- Railway MCP tools exist in this session (`mcp__railway__deploy`, `list_services`, …), but this
  repository is a hooks/skills library with nothing to deploy; a preview has no target here.
- Precedents: `lib/project_conventions.py` (deterministic helper over subprocess `git`), the fake
  `claude` in `test_evals.py` (a fake executable on `PATH` replaying canned output).

## Patterns to follow
- Deterministic helper + fake binary tests; wording contract tests; one live exercise on PR #2.
- Gated steps report what they would do when the grant is absent — the R5 shape.
- Fibonacci: poll interval 21 s, wait timeout 1597 s, at most 2 CI-driven rung-1 fixes.

## Constraints discovered
- No grants here, so `merge` and `deploy-preview` are exercised only as refusals; `merge` on a
  real PR never runs in this session. Stated as such.
- CI minutes on a public repo are free; the harness takes ≈ 15 s locally.
- The workflow must not run the eval suite (money).

## Open decisions (all resolved by delegation — see decisions.md)
1. Where the lane lives — `ship.md` gains a `--through ci|preview|merge` section; a helper
   `lib/release.py` (`checks`, `wait`, `failed-logs`, `merge`). Default: as stated.
2. CI for this repo — `.github/workflows/gentic.yml` running the harness on push and PR, Python
   3.11 on ubuntu, no evals. Default: yes (the user's "go ahead" is the request).
3. Merge strategy — `gh pr merge --merge` (a merge commit keeps the per-task history), no branch
   deletion. Default: as stated.
4. Preview — the mechanism is described in `ship.md` (Railway when a service is linked, otherwise
   the project's own preview command), no implementation in this run. Default: as stated.
5. Live proof — push the workflow; `release.py wait --pr 2` watches the real run; `release.py merge --pr 2`
   is refused for lack of a grant. Default: as stated.
