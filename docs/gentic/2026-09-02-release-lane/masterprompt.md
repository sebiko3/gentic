# Masterprompt: release-lane

## Mission
`/ship` no longer ends at "PR opened" when the project allows more. A helper over `gh` answers
what a PR's checks say, waits for them, prints the failing jobs' logs, and merges — the last
only when the project grants `merge-on-green`, the PR is open and mergeable, every check is
green, and the target repository is the checkout's own. `ship.md` gains a `--through
ci|preview|merge` section that uses it: watch; feed a failure back as a rung-1 fix (at most
two); deploy a preview and smoke it with `ui-tester` (described in §8, **not implemented in this
run**); merge when granted. Every gated step reports what it would have done when the grant is
absent. This repository gets its first CI workflow — the offline harness, never `evals/run.py` —
so the lane has a real run to watch. The live proof watches PR #2 (`gentic/self-improving-gentic`
→ `main`, OPEN, verified) to green and is refused a merge.

"Deterministic" here means: the same inputs produce the same `gh` argv, nothing is cached or
retried, and the only clock in the output is the elapsed-seconds prefix.

This file is self-sufficient for execution. `decisions.md` holds the rationale only.

## Context
### `gh` facts (2.74.0, logged in as sebiko3)
`gh pr checks <n> --json name,state,bucket,link,workflow` prints a JSON array; `bucket` ∈
`pass|fail|pending|skipping|cancel`; when no checks exist it prints
`no checks reported on the '<branch>' branch` on **stderr** and exits 1. A check's `link` is
`https://github.com/<owner>/<repo>/actions/runs/<run>/job/<job>`. `gh run view <run> --job <job> --log-failed`
prints the failed steps' logs. `gh pr view <n> --json state,isDraft,mergeable,headRefName`
reports `state` ∈ `OPEN|MERGED|CLOSED`, `mergeable` ∈ `MERGEABLE|CONFLICTING|UNKNOWN`.
`gh repo view --json nameWithOwner` names the checkout's repository. `gh pr merge <n> --merge`
merges with a merge commit. Pushing a commit that adds `.github/workflows/*.yml` requires the
`workflow` scope on `gh`'s token (or an SSH remote); `gh auth status` lists scopes.

### Helper `.claude/hooks/lib/release.py`
Stdlib plus `subprocess` to `gh` (found with `shutil.which("gh")`; absent → `gh not found` on
stderr, exit 5). It inserts its own directory into `sys.path` and imports the sibling
`project_conventions`. No quoted `.claude` path literal anywhere in the file (the harness's
isolation grep covers `lib/*.py`). **Exactly four modes**, polling implemented in Python (never
`gh --watch`), no retries, no caching, no colour, no other output modes. Common options:
`--pr N` (required), `--repo OWNER/NAME` (optional; passed to every `gh pr` and `gh run` call).
- `checks` — one line per check `<bucket>  <name>  <link>`, then
  `pass: a  fail: b  pending: c  skipping: d  cancel: e`. Exit **0** only when there is at least
  one check and every check is `pass` or `skipping`; **1** when any is `fail` or `cancel`;
  **2** when any is `pending` and none failed; **3** when `gh` says no checks (stderr matches
  `no checks reported on the`) **or the array is empty**; **6** on any other `gh` failure, with
  `gh`'s stderr echoed. Stdout carries only these lines.
- `wait [--timeout 1597] [--interval 21]` — repeats `checks` until it exits 0 or 1; 3 counts as
  "not started yet" and keeps waiting; 6 stops immediately with 6. Each poll prints
  `f"{elapsed:4d}s  " + summary` (e.g. `  21s  pass: 0  fail: 0  pending: 1  …`). Exit = the
  final `checks` code, or **4** on timeout.
- `failed-logs [--lines 89]` — for every check with bucket `fail` or `cancel`: parse `<run>` and
  `<job>` from `link`; a link that does not parse prints `no link for <name>` on stderr and is
  skipped; otherwise run `gh run view <run> --job <job> --log-failed`, print a header
  `== <name> (run <run>, job <job>)` and that job's last `--lines` lines. Exit 0 when at least
  one log was printed, 1 otherwise (`nothing failed` or `no parsable links` on stderr).
- `merge` — gates in this order, each refusal on stderr with exit 1 and **no `gh pr merge` call**:
  1. `project_conventions.authorized("merge-on-green", root)` with `root =
     project_conventions.project_root(cwd)`, called with its stdout and stderr captured and
     discarded (it prints `yes`/`no` itself and returns 0/1); non-zero → `not authorized: merge-on-green`.
  2. `--repo`, when given, must equal `gh repo view --json nameWithOwner` of the checkout; else
     `foreign repository: <repo>`.
  3. `gh pr view N --json state,isDraft,mergeable`: `state` must be `OPEN`, `isDraft` false,
     `mergeable` not `CONFLICTING`; else `pr not mergeable: <reason>`.
  4. `checks` must exit 0; else `checks not green`.
  Then `gh pr merge N --merge` (branch kept); exit `gh`'s code; print `merged` on 0.

### Fake `gh` for tests
`tests/test_release.py` writes an executable `gh` into a temp `PATH` dir. Behaviour by argv:
`pr checks …` prints the file `$FAKE_GH_CHECKS` (when that path is a directory it prints
`checks.<k>.json` for the k-th call, counted in `$FAKE_GH_COUNTER`; a file whose content is the
word `none` makes it print `no checks reported on the 'x' branch` to stderr and exit 1; content
`broken` makes it print `HTTP 502` to stderr and exit 1); `pr view …` prints `$FAKE_GH_VIEW`
(default `{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE","headRefName":"b"}`);
`repo view …` prints `{"nameWithOwner":"$FAKE_GH_REPO"}` (default `owner/repo`);
`run view …` prints `$FAKE_GH_LOG`; `pr merge …` exits `$FAKE_GH_MERGE_EXIT` (default 0);
`auth status` prints `Token scopes: 'repo', 'workflow'`. Every invocation appends its argv as
one JSON line to `$FAKE_GH_ARGV`. Merge tests build a temp repo with a `CLAUDE.md` and a temp
trust file (`GENTIC_TRUST`, set in the subprocess env), the `Authorizations` fixtures of
`test_project_conventions.py` being the pattern; the helper is run with `cwd` = that repo.

### Tests — `tests/test_release.py` holds exactly these twelve
| test | asserts |
|---|---|
| `test_checks_reports_buckets_and_exit_codes` | pass→0, fail→1, pending→2, `none`→3, `[]`→3, `broken`→6 with `HTTP 502` on stderr; the summary line present |
| `test_wait_polls_until_settled` | pending, pending, pass → exit 0; three `pr checks` argv lines; each poll line starts with a right-aligned seconds value and `s  ` |
| `test_wait_times_out` | pending forever, `--timeout 1 --interval 1` → exit 4 |
| `test_wait_stops_on_a_hard_error` | `broken` → exit 6 after one poll |
| `test_failed_logs_prints_the_failing_job` | fail bucket with a run/job link → header with both ids, the log's last lines, argv contains `run view <run> --job <job> --log-failed`; an unparsable link → `no link for` on stderr |
| `test_merge_refuses_without_a_grant` | untrusted → exit 1, stderr `not authorized: merge-on-green`, no `pr merge` in argv |
| `test_merge_refuses_a_foreign_repo` | granted + trusted, `--repo other/place` → exit 1, `foreign repository`, no `pr merge` |
| `test_merge_refuses_a_non_open_pr` | granted + trusted, view says `MERGED` → exit 1, `pr not mergeable`, no `pr merge` |
| `test_merge_refuses_when_checks_are_not_green` | granted + trusted, checks fail → exit 1, `checks not green`, no `pr merge` |
| `test_merge_merges_when_granted_and_green` | argv has `pr merge 2 --merge`; stdout is exactly `merged` (no stray `yes`) |
| `test_harness_registers_release_suite` | `run.sh`'s suite loop contains `test_release` |
| `test_workflow_runs_the_harness_and_no_evals` | `.github/workflows/gentic.yml` exists; contains `.claude/hooks/tests/run.sh`, `ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5`; does not contain `evals/run.py`, `permissions:`, `concurrency:`, `timeout-minutes`, `paths` |
Extra tests are not added in this run; the counts in the verify lines are exact.

### Structure tests — `test_structure.py`, class `ReleaseLane`, lowered text, three tests
`test_ship_has_a_through_section`: `ship.md` contains `'--through'`, `'release.py'`,
`'merge-on-green'`, `'deploy-preview'`, `'at most two'`, `'what it would have done'`,
`'never merge the pr yourself'`, and `index('## 8.') < index('## 7.')`.
`test_iterate_ships_through_grants`: `gentic-iterate` contains `'--through'`.
`test_readme_documents_the_release_lane`: README contains `'## the release lane'` and `'release.py'`.

### Wording — exact old → new
- `ship.md` frontmatter `description: Verify, review, commit, push and open a PR for the current
  work — the one place git automation runs` → `description: Verify, review, commit, push and open
  a PR for the current work — and, under the project's grants, watch CI, preview and merge — the
  one place git automation runs`.
- `ship.md` preamble sentence `Everything below then runs unattended until it either opens a PR
  or stops with a clear reason.` → `Everything below then runs unattended until it either opens
  a PR — or, with \`--through\`, goes as far as the project's grants allow — or stops with a
  clear reason.`
- `ship.md`: a new section inserted **before** `## 7. Never`, headed
  `## 8. Through CI, preview and merge (\`--through\`)` (numbered 8 and placed before 7 on
  purpose, so §7's list stays where readers know it): "`/ship --through ci` continues after the
  PR: `python3 "$HOME/.claude/hooks/lib/release.py" wait --pr <n>` watches the checks (21 s
  polls, 1597 s ceiling). Green → report. Red → `release.py failed-logs --pr <n>`, then one
  rung-1 fix: a failing test first, the smallest change that makes it pass, one commit, push,
  `wait` again. At most two such fixes per ship; a third failure stops with the logs in the
  report. `--through preview` (needs `authorized deploy-preview` → `yes`): deploy with the
  project's own mechanism — the Railway MCP `deploy` when a Railway service is linked, otherwise
  the preview command the project's README documents — and hand the URL to `ui-tester` with the
  flow the PR changes; its report block goes in the PR body. `--through merge` (needs
  `authorized merge-on-green` → `yes`): `release.py merge --pr <n>`, which refuses on its own
  when the grant, the mergeability, or the green is missing. Without a grant, each of these
  steps writes what it would have done into the report and stops there."
- `ship.md` §7: `- Never merge the PR — opening it is where this command ends.` →
  `- Never merge the PR yourself — \`release.py merge\` under an explicit \`merge-on-green\`
  grant is the only path (§8); otherwise opening it is where this command ends.`
- `gentic-iterate/SKILL.md`: after the sentence ending `…invoke it to close out the branch.`
  (the end of the final-report paragraph), append: `When \`push\` and \`open-pr\` were granted
  and the PR is open, continue with \`ship.md\` §8 as far as the grants allow: \`--through ci\`
  always, \`preview\` and \`merge\` only when \`authorized deploy-preview\` / \`authorized
  merge-on-green\` print \`yes\`.`
- `README.md`: a section `## The release lane` before `## Standing authorizations`: the helper's
  four modes with their exit codes, the two-fix rule, the four merge gates, that this repo's own
  CI is the harness on GitHub Actions, and that `merge` under a grant is the only exception to
  `/ship`'s never-merge. `CLAUDE.md` and the hooks README do not change.
- `run.sh`: the suite loop gains `test_release`.

### Workflow `.github/workflows/gentic.yml` (new)
Exactly these keys: `name: gentic`; `on: [push, workflow_dispatch]`; `jobs.harness.runs-on:
ubuntu-latest`; `jobs.harness.steps`: `actions/checkout@v4`, `actions/setup-python@v5` with
`python-version: "3.12"`, `run: bash .claude/hooks/tests/run.sh`. No `permissions`,
`concurrency`, `timeout-minutes`, path filters or `pull_request` trigger. "No evals" means the
workflow never invokes `evals/run.py`; the harness's offline `test_evals` suite runs as part of
`run.sh`, unmodified. `jq` is preinstalled on `ubuntu-latest`; the Configuration section skips
without a settings file; the conventions tests supply their own git identity. This is the
first Linux run of the harness; a Linux-only failure is L7's rung-1 territory (a code fix,
test-first). **A latency-budget miss on the runner is not**: it is recorded as a finding with
the medians, L7 fails, and whether to raise the budget is the user's decision.

### Install and live proof
- `./install.sh` runs at the end of task 4, as every run does, so the installed setup stays in
  sync (`install.sh --check` exit 0 is part of L6); the live proof invokes the repo copy
  `python3 .claude/hooks/lib/release.py`.
- Preconditions before task 5's push, both checked and pasted: `gh auth status` lists the
  `workflow` scope (if not, the run stops and the user runs `gh auth refresh -s workflow`
  themselves); `gh pr view 2 --json state,headRefName` → `OPEN`, `gentic/self-improving-gentic`.
- Live watch: `nohup python3 .claude/hooks/lib/release.py wait --pr 2 --timeout 1597 --interval 21 > <scratch>/wait.log 2>&1 &`
  with a `Monitor` that echoes each poll line and ends on the process's exit (the Bash tool's
  600 s limit is below the ceiling). Red → `failed-logs`, one rung-1 fix (test-first, commit,
  push), `wait` again; at most two.
- Live refusal: `gh pr view 2 --json state --jq .state` (expect `OPEN`), then
  `python3 .claude/hooks/lib/release.py merge --pr 2` (expect stderr `not authorized:
  merge-on-green`, exit 1), then `gh pr view 2 --json state --jq .state` again (expect `OPEN`).
- Lessons carried: `-k` patterns are substrings of contract test names; commit from the repo
  root with absolute paths; needles on one line; the local `python3` is 3.13 and CI is 3.12 —
  the helper targets 3.9+.

## Decisions (inlined; all `user — delegated` except CI-for-this-repo, which "go ahead" requested)
Helper with four modes and fixed exit codes, empty checks never green, hard `gh` errors surface;
merge gated four ways; `ship.md` §8 plus the frontmatter, preamble and §7 sentences; merge
commit, branch kept; preview described not implemented; two CI-driven fixes per ship;
`on: push` workflow with exactly the listed keys; install at task 4; live proof on PR #2.

## Constraints
- Stdlib only in `lib/release.py`; `subprocess` allowed; no hook scripts change; no quoted
  `.claude` literal in the helper.
- Wording sites are exactly those in Context; `/ship` §1–§6 bodies unchanged.
- Every task test-first; observed RED in `progress.md`; every `-k` verify names its count and
  the test file holds exactly the twelve tests named.

## Non-goals
- No preview implementation; no Railway calls; no `ui-tester` dispatch.
- No merge of PR #2; no trust entry or grant written; no `gh auth refresh` by the run.
- No eval suite run (the changed Iterate sentence sits behind the `push`/`open-pr` gate the
  workflow case never passes).
- No `pull_request` trigger, matrix, caching, badge, branch protection, `concurrency`,
  `permissions`, `timeout-minutes` or path filters in the workflow.
- No latency-budget change in the harness; no `--through` for `gentic-execute`.
- No Linux container run before the push; the first CI run is the first Linux run.

## Definition of Done
- [ ] L1 `checks`. pass→0, fail→1, pending→2, none or `[]`→3, other `gh` failure→6.
      verify: `python3 .claude/hooks/tests/test_release.py -k checks_reports` prints `Ran 1 test` and `OK`
      contract: tests/test_release.py · test_checks_reports_buckets_and_exit_codes · expected
      RED: `AssertionError: 2 != 0 : checks did not run` (python cannot open the helper)
- [ ] L2 `wait`. Polls until settled; times out with 4; stops on a hard error with 6.
      verify: `python3 .claude/hooks/tests/test_release.py -k wait_` prints `Ran 3 tests` and `OK`
      contract: tests/test_release.py · test_wait_polls_until_settled, test_wait_times_out,
      test_wait_stops_on_a_hard_error · expected RED: `AssertionError: 2 != 0 : wait did not run`
- [ ] L3 `failed-logs`. Header with both ids, the job's last lines, the unparsable-link path.
      verify: `python3 .claude/hooks/tests/test_release.py -k failed_logs` prints `Ran 1 test` and `OK`
      contract: tests/test_release.py · test_failed_logs_prints_the_failing_job · expected RED:
      `AssertionError: 2 != 0 : failed-logs did not run`
- [ ] L4 `merge` is gated four ways and prints only `merged`.
      verify: `python3 .claude/hooks/tests/test_release.py -k merge_` prints `Ran 5 tests` and `OK`
      contract: tests/test_release.py · the five `test_merge_*` tests · expected RED:
      `AssertionError: 2 != 1 : merge did not refuse`
- [ ] L5 Wording. The `ReleaseLane` needles, §8 before §7, the §7 sentence, the Iterate sentence, the README section.
      verify: `python3 .claude/hooks/tests/test_structure.py -k ReleaseLane` prints `Ran 3 tests` and `OK`
      contract: tests/test_structure.py · ReleaseLane (three tests) · expected RED:
      `AssertionError: '--through' not found in …`
- [ ] L6 Workflow, registration, harness, install. The workflow file as specified; `run.sh` runs
      `test_release`; `bash .claude/hooks/tests/run.sh` exits 0 and prints `ok    test_release (Ran`;
      `./install.sh --check` exits 0 after the install.
      verify: `python3 .claude/hooks/tests/test_release.py -k workflow -k registers` prints `Ran 2 tests` and `OK`; `bash .claude/hooks/tests/run.sh` exits 0 and prints `ok    test_release (Ran`; `./install.sh --check` exits 0
      contract: tests/test_release.py · test_workflow_runs_the_harness_and_no_evals,
      test_harness_registers_release_suite · expected RED: `AssertionError: False is not true :
      .github/workflows/gentic.yml missing` and `AssertionError: 'test_release' not found in …`
- [ ] L7 Live watch is green. Preconditions pasted (scope, PR state); after the push,
      `release.py wait --pr 2 --timeout 1597 --interval 21` **exits 0**, possibly after at most
      two rung-1 fixes each with `failed-logs` output pasted. Still red after two fixes, or red
      only on a latency line, → L7 FAILED and the run hands off with the logs.
      verify: run it; paste the poll lines, the final summary and the exit code
      contract: n/a — a live observation of GitHub Actions; the pasted summary is the evidence.
- [ ] L8 Live refusal. `gh pr view 2 --json state --jq .state` → `OPEN`; `release.py merge --pr 2`
      → stderr `not authorized: merge-on-green`, exit 1; the state query again → `OPEN`. (That no
      `gh pr merge` was issued is proven by L4, not observed here.)
      verify: run the three commands; paste
      contract: n/a — a live observation; the pasted outputs are the evidence.

## Risks & early signals
- The token may lack the `workflow` scope; the precondition catches it before any push.
- Ubuntu runners may miss the 150 ms latency medians; by the rule above that fails L7 and is
  handed to the user rather than patched.
- `gh pr checks` on a fresh push may return nothing for a minute; exit 3 keeps `wait` polling.

## Task order (for Execute)
1. Fake `gh` harness; `checks` and `wait` — L1, L2.
2. `failed-logs`; `merge` with the four gates — L3, L4.
3. Wording in `ship.md` (four sites), `gentic-iterate`, README; structure tests — L5.
4. Workflow file, `run.sh` registration, harness, install — L6 (workflow committed with this task).
5. Preconditions; push; live watch; live refusal — L7, L8.

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)

## Critique record
`masterprompt-critic` (cold read): 4 blocking, 14 serious, 11 minor. All fixed inline: the
authorization call's real return type and captured output; exit 3 only on the no-checks message
and 6 on other `gh` failures, propagated by `wait`; an empty list is never green; defaults for
`--timeout`, `--interval`, `--lines`; "no evals" defined; `--repo` on every call and a
foreign-repo refusal with its test; per-job log lines and the unparsable-link path; the elapsed
prefix format; the frontmatter and preamble sentences added as sites; the latency remedy
withdrawn in favour of a finding; the workflow committed with task 4; preview marked as not
implemented in the Mission; L7 falsifiable; L8's third clause attributed to L4; L5 needles for
the two-fix rule, the would-have-done rule, the §7 sentence and §8's position; exactly twelve
tests; L6's harness pass condition; workflow keys frozen; four modes only; install stated; the
`workflow`-scope and PR-state preconditions; no Linux pre-run; the isolation grep; the import
shim; Python versions; literal background commands; "deterministic" defined; mergeability
gate with its test; the Iterate insertion point.
