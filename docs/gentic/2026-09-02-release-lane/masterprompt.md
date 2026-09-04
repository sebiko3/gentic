# Masterprompt: release-lane

## Mission
`/ship` no longer ends at "PR opened" when the project allows more. A deterministic helper
answers what a PR's checks say, waits for them, prints the failing jobs' logs, and merges — the
last only when the project grants `merge-on-green` and every check is green. `ship.md` gains a
`--through ci|preview|merge` section that uses it: watch, feed a failure back as a rung-1 fix
(at most two), deploy a preview when granted, smoke it with `ui-tester`, merge when granted;
every gated step reports what it would do when the grant is absent. This repository gets its
first CI workflow (the offline harness, no evals) so the lane has a real run to watch, and the
live proof watches PR #2 and is refused a merge.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
- **`gh` facts** (2.74.0, logged in as sebiko3): `gh pr checks <n> --json name,state,bucket,link,workflow`
  prints a JSON array; `bucket` ∈ `pass|fail|pending|skipping|cancel`; with no checks it prints
  `no checks reported on the '<branch>' branch` on stderr and exits 1. A check's `link` looks like
  `https://github.com/<owner>/<repo>/actions/runs/<run>/job/<job>`. `gh run view <run> --job <job> --log-failed`
  prints the failed steps' logs. `gh pr merge <n> --merge` merges with a merge commit.
  `gh pr view <n> --json state` reports `OPEN|MERGED|CLOSED`.
- **Helper** `.claude/hooks/lib/release.py` — stdlib plus `subprocess` to `gh` (resolved with
  `shutil.which("gh")`; absent → `gh not found` on stderr, exit 5). Modes, all with `--pr N` and
  optional `--repo OWNER/REPO` passed through to `gh`:
  - `checks`: one line per check `<bucket>  <name>  <link>`, then a summary line
    `pass: a  fail: b  pending: c  skipping: d  cancel: e`. Exit **0** when every check is
    `pass` or `skipping`; **1** when any is `fail` or `cancel`; **2** when any is `pending` (and
    none failed); **3** when `gh` reports no checks.
  - `wait --timeout 1597 --interval 21`: repeats `checks` until it exits 0 or 1, or the timeout
    passes; `3` counts as "not started yet" and keeps waiting. Prints each poll's summary line
    with an elapsed-seconds prefix. Exit = the final `checks` code, or **4** on timeout.
  - `failed-logs --lines 89`: for every check with bucket `fail` or `cancel`, parse `<run>` and
    `<job>` from `link`, run `gh run view <run> --job <job> --log-failed`, print a header
    `== <name> (run <run>, job <job>)` and the last `--lines` lines. Exit 0 when at least one
    log was printed, 1 when nothing failed or no link could be parsed (say which).
  - `merge`: first `project_conventions.authorized("merge-on-green", root)` — imported from
    the sibling module, root = `project_conventions.project_root(cwd)`; when not `yes`, print
    `not authorized: merge-on-green` to stderr and exit **1 without calling `gh`**. Then `checks`
    must exit 0, else print `checks not green` and exit 1. Then `gh pr merge N --merge` (branch
    kept); exit `gh`'s code; print `merged` on 0.
  Every `gh` invocation's argv is what tests inspect; nothing is cached.
- **Fake `gh` for tests** (`tests/test_release.py` writes it to a temp `PATH` dir): `gh pr checks …`
  prints the file named by `$FAKE_GH_CHECKS` (when that path is a directory, it prints
  `checks.<k>.json` for the k-th call, tracked in `$FAKE_GH_COUNTER`; a file containing the word
  `none` makes it print `no checks reported on the 'x' branch` to stderr and exit 1);
  `gh run view …` prints `$FAKE_GH_LOG`; `gh pr merge …` exits `$FAKE_GH_MERGE_EXIT` (default 0);
  every invocation appends its argv as a JSON line to `$FAKE_GH_ARGV`. Tests set `GENTIC_TRUST`
  and build a temp repo with a `CLAUDE.md` for the merge tests (the `Authorizations` fixtures in
  `test_project_conventions.py` are the pattern).
- **Tests** (`tests/test_release.py`, class-level fake `gh`), exact names:
  `test_checks_reports_buckets_and_exit_codes` (pass→0, fail→1, pending→2, none→3, summary
  line present); `test_wait_polls_until_settled` (pending, pending, pass across three calls →
  exit 0, three `pr checks` argv lines, elapsed prefixes) and `test_wait_times_out` (pending
  forever, `--timeout 1 --interval 1` → exit 4); `test_failed_logs_prints_the_failing_job`
  (fail bucket with a run/job link → header with the ids, the log's last lines, argv contains
  `run view <run> --job <job> --log-failed`); `test_merge_refuses_without_a_grant` (untrusted
  → exit 1, stderr `not authorized: merge-on-green`, no `pr merge` in argv);
  `test_merge_refuses_when_checks_are_not_green` (granted, trusted, checks fail → exit 1,
  `checks not green`, no `pr merge`); `test_merge_merges_when_granted_and_green` (argv has
  `pr merge 2 --merge`, stdout `merged`); `test_harness_registers_release_suite` (`run.sh`'s
  suite loop contains `test_release`); `test_workflow_runs_the_harness_and_no_evals`
  (`.github/workflows/gentic.yml` exists, contains `.claude/hooks/tests/run.sh`, `ubuntu-latest`,
  `actions/checkout@v4`, does not contain `evals/run.py`).
- **Structure tests** (`test_structure.py`, class `ReleaseLane`, lowered text):
  `test_ship_has_a_through_section` — `ship.md` contains `'--through'`, `'release.py'`,
  `'merge-on-green'`, `'deploy-preview'`; `test_iterate_ships_through_grants` — `gentic-iterate`
  contains `'--through'`; `test_readme_documents_the_release_lane` — README contains
  `'## the release lane'` and `'release.py'`. Every verify names its `Ran N tests` count.
- **Wording, exact old → new.**
  - `ship.md`: after section `## 6. Push and open the PR` (its last paragraph ends `Report the
    PR URL.`) and before `## 7. Never`, a new section `## 8. Through CI, preview and merge
    (\`--through\`)` — kept as §8 so §7's list stays where readers know it:
    "`/ship --through ci` continues after the PR: `python3 "$HOME/.claude/hooks/lib/release.py" wait --pr <n>`
    watches the checks (21 s polls, 1597 s ceiling). Green → report. Red →
    `release.py failed-logs --pr <n>`, then one rung-1 fix: a failing test first, the smallest
    change, one commit, push, `wait` again. At most two such fixes per ship; a third failure
    stops with the logs in the report. `--through preview` (needs `authorized deploy-preview`
    → `yes`): deploy with the project's own mechanism — the Railway MCP `deploy` when a
    service is linked, otherwise the project's documented preview command — and hand the URL to
    `ui-tester` with the flow the PR changes; its report block goes in the PR body. `--through merge`
    (needs `authorized merge-on-green` → `yes`): `release.py merge --pr <n>`, which refuses on its
    own when the grant or the green is missing. Without a grant, each of these steps writes
    what it would have done into the report and stops there. `merge` is the one exception to §7's
    "never merge": it runs only through this helper, only under the grant." Also, in §7, change
    `- Never merge the PR — opening it is where this command ends.` to `- Never merge the PR
    yourself — \`release.py merge\` under an explicit \`merge-on-green\` grant is the only path
    (§8); otherwise opening it is where this command ends.`
  - `gentic-iterate/SKILL.md`, in the final-report paragraph, after `and put the PR URL in the
    report.` insert: `Then continue with \`ship.md\` §8 as far as the grants allow:
    \`--through ci\` always, \`preview\` and \`merge\` only when \`authorized deploy-preview\` /
    \`authorized merge-on-green\` print \`yes\`.`
  - `README.md`: a section `## The release lane` before `## Standing authorizations`: the
    helper's four modes and exit codes, the two-fix rule, what is gated, that this repo's own
    CI is the harness on GitHub Actions, and that `merge` under a grant is the only exception to
    `/ship`'s never-merge.
  - `.claude/hooks/README.md`: nothing (no hook changes).
  - `run.sh`: the suite loop gains `test_release`.
- **Workflow** `.github/workflows/gentic.yml` (new): name `gentic`; `on: [push, workflow_dispatch]`
  (push covers PR head commits without double runs); one job `harness` on `ubuntu-latest`:
  `actions/checkout@v4`, `actions/setup-python@v5` with `python-version: "3.12"`, then
  `bash .claude/hooks/tests/run.sh`. `jq` is preinstalled on `ubuntu-latest`; the harness's
  Configuration section skips without a settings file; the conventions tests supply their own
  git identity. **No evals.** Latency budgets are 150 ms medians; a runner may miss them — see Risks.
- **Live proof.** Commit the workflow (task 5's checkpoint) and push; then
  `python3 .claude/hooks/lib/release.py wait --pr 2 --timeout 1597 --interval 21` in the
  background with a monitor on its log; paste the final summary and exit code. If red:
  `release.py failed-logs --pr 2`, then a rung-1 fix (test-first), push, `wait` again — at most
  two fixes, per §8. Then `python3 .claude/hooks/lib/release.py merge --pr 2` → expected stderr
  `not authorized: merge-on-green`, exit 1, and `gh pr view 2 --json state --jq .state` → `OPEN`.
  No grant is created, no trust entry is written (they are the user's).
- Lessons carried: `-k` patterns are substrings of contract test names; commit from the repo
  root with absolute paths; a task with a wrapped needle fails its lowered-text test (keep
  needles on one line); wall clock is the binding limit on long runs — the wait ceiling is 1597 s.

## Decisions (inlined; all `user — delegated` except CI-for-this-repo, which the user's "go ahead" requested)
Helper over `gh` with four modes and fixed exit codes; `ship.md` §8 and one §7 sentence;
merge with a merge commit, branch kept; preview described not implemented; two CI-driven fixes
per ship; `on: push` workflow running the harness only; live proof watches PR #2 and is refused
a merge.

## Constraints
- Stdlib only in `lib/release.py`; `subprocess` allowed (not a hook). No hook scripts change.
- Wording sites are exactly those in Context. `/ship` §1–§6 unchanged.
- Every task test-first; observed RED in `progress.md`; every `-k` verify names its count.

## Non-goals
- No preview deployment implementation; no Railway calls; no `ui-tester` dispatch in this run.
- No merge of PR #2 (not granted); no trust entry, no grant written.
- No eval suite run (the wording change in `gentic-iterate` is behind the `push`/`open-pr`
  gate the workflow case never passes; a regression run would exercise nothing new).
- No `pull_request` trigger, no matrix, no caching, no badge, no branch protection rules.
- No `--through` for `gentic-execute`; only the Iterate final report ships.

## Definition of Done
- [ ] L1 `checks`. Buckets and exit codes as in Context.
      verify: `python3 .claude/hooks/tests/test_release.py -k checks_reports` prints `Ran 1 test` and `OK`
      contract: tests/test_release.py · test_checks_reports_buckets_and_exit_codes · expected
      RED: `AssertionError: 2 != 0 : checks did not run` (python cannot open the helper)
- [ ] L2 `wait`. Polls until settled; times out with 4.
      verify: `python3 .claude/hooks/tests/test_release.py -k wait_` prints `Ran 2 tests` and `OK`
      contract: tests/test_release.py · test_wait_polls_until_settled, test_wait_times_out ·
      expected RED: `AssertionError: 2 != 0 : wait did not run`
- [ ] L3 `failed-logs`. Prints the failing job's log with ids in the header.
      verify: `python3 .claude/hooks/tests/test_release.py -k failed_logs` prints `Ran 1 test` and `OK`
      contract: tests/test_release.py · test_failed_logs_prints_the_failing_job · expected RED:
      `AssertionError: 2 != 0 : failed-logs did not run`
- [ ] L4 `merge` is gated twice. Refused without the grant (no `gh` call), refused when not
      green, merges when granted and green.
      verify: `python3 .claude/hooks/tests/test_release.py -k merge_` prints `Ran 3 tests` and `OK`
      contract: tests/test_release.py · test_merge_refuses_without_a_grant,
      test_merge_refuses_when_checks_are_not_green, test_merge_merges_when_granted_and_green ·
      expected RED: `AssertionError: 2 != 1 : merge did not refuse` (python exit 2 for the missing file)
- [ ] L5 Wording. `ship.md` §8 and the §7 sentence; `gentic-iterate`; README.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ReleaseLane` prints `Ran 3 tests` and `OK`
      contract: tests/test_structure.py · ReleaseLane (three tests) · expected RED:
      `AssertionError: '--through' not found in …`
- [ ] L6 Workflow and harness registration. The workflow file as in Context; `run.sh` runs
      `test_release`; `bash .claude/hooks/tests/run.sh` exits 0 with `ok    test_release (Ran`.
      verify: `python3 .claude/hooks/tests/test_release.py -k workflow -k registers` prints `Ran 2 tests` and `OK`; `bash .claude/hooks/tests/run.sh`
      contract: tests/test_release.py · test_workflow_runs_the_harness_and_no_evals,
      test_harness_registers_release_suite · expected RED: `AssertionError: False is not true :
      .github/workflows/gentic.yml missing` and `AssertionError: 'test_release' not found in …`
- [ ] L7 Live watch. After the push, `release.py wait --pr 2 --timeout 1597 --interval 21`
      ends with exit 0 (green) or, after at most two rung-1 fixes, still red → recorded as a
      finding with the `failed-logs` output. Pasted with the elapsed time and the summary line.
      verify: run it; paste
      contract: n/a — a live observation of GitHub Actions; the pasted summary is the evidence.
- [ ] L8 Live refusal. `release.py merge --pr 2` → stderr `not authorized: merge-on-green`, exit 1;
      `gh pr view 2 --json state --jq .state` → `OPEN`; the fake-free `gh` was not asked to merge
      (the helper exits before any `gh` call, per L4).
      verify: run both; paste
      contract: n/a — a live observation; the pasted outputs are the evidence.

## Risks & early signals
- GitHub runners may miss the 150 ms latency medians (`run.sh` measures Python startup ×20). If
  the first CI run fails only on a latency line, that is L7's rung-1 fix: make the harness's
  latency budget overridable (`HOOK_LATENCY_BUDGET_MS`, default 150) and set it in the workflow
  to 377 — a harness change, test-first (`test_lib` or a new assertion in `test_release`),
  recorded as a lesson about CI runners.
- `gh pr checks --json` may return checks from both push and PR events if a `pull_request`
  trigger is ever added; `on: push` only avoids duplicates.
- The wait ceiling (1597 s) exceeds the Bash tool's 600 s limit: run `wait` in the background
  with a monitor, as the eval suites were.

## Task order (for Execute)
1. Fake `gh` harness and the helper: `checks`, `wait` — L1, L2.
2. `failed-logs`, `merge` with both gates — L3, L4.
3. Wording in `ship.md`, `gentic-iterate`, README + structure tests — L5.
4. Workflow file, `run.sh` registration, harness — L6.
5. Push; live watch; live refusal — L7, L8.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
