# Decisions: release-lane

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Where the lane lives | `ship.md` §8 `--through ci\|preview\|merge` plus `lib/release.py` (`checks`, `wait`, `failed-logs`, `merge`). | A `gentic-release` skill; prose only | `/ship` is already the only git/GitHub automation; a helper makes CI state a script's answer, not memory. | user — delegated |
| CI for this repository | `.github/workflows/gentic.yml`: harness on `push` and `workflow_dispatch`, ubuntu-latest, Python 3.12, no evals (as the masterprompt fixed it; this row first said 3.11 and `pull_request` and was corrected at close). | Keep "no CI"; a `pull_request` trigger | The lane needs something to watch; the harness is offline and free; the user's "go ahead" is the per-project request R5 required. | user (request) / delegated (shape) |
| Merge strategy | `gh pr merge --merge`, branch kept. | Squash; rebase | Per-task checkpoint history is the audit trail. | user — delegated |
| Preview | Described, not implemented: Railway via the MCP when a service is linked, else the project's preview command; `ui-tester` smokes the URL. | Implement Railway deploy now | Nothing in this repo deploys; an unexercised implementation would be a claim. | user — delegated |
| Gating | `wait`/`checks`/`failed-logs` are ungated (read-only); `merge` requires `authorized merge-on-green`; preview requires `authorized deploy-preview`. | Gate everything | Watching is harmless; acting is consent. | user — delegated |
| CI-driven fixes | At most 2 rung-1 fixes per ship, each test-first with its own commit, then stop and report. | Unbounded | Budget discipline; a third failure is a finding. | user — delegated |
| Live proof | Push the workflow to the branch; watch PR #2's checks with the helper; `merge --pr 2` refused. | None | The lane must be seen to watch a real run. | user — delegated |
