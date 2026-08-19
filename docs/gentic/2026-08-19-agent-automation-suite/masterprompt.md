# Masterprompt: agent-automation-suite

## Mission

Turn this repository into the single tracked source of truth for a Claude Code automation
setup, and close three named gaps in it with four purpose-built subagents. After this run:
the hooks, commands, skills, and agents all live in the repo and install into `~/.claude/`
by one idempotent script; code review is a first-party capability that is offered
automatically instead of depending on the user remembering `/ship`; gentic's subagent
fan-out has a written dispatch contract instead of a sentence; and the spec and done-ness
phases each name the agent that scrutinises them. The setup's config no longer references a
plugin that was never installed.

## Context

Facts this work depends on (all verified during Scout, 2026-08-19):

- `~/.claude/agents/` exists and is **empty**. The only agent types available are built-ins
  (`claude`, `claude-code-guide`, `Explore`, `general-purpose`, `Plan`, `statusline-setup`).
- `~/.claude/settings.json:11` enables `"pr-review-toolkit@claude-plugins-official"`, but that
  plugin is **absent** from `~/.claude/plugins/installed_plugins.json` and from
  `~/.claude/plugins/cache/claude-plugins-official/` (which contains only `frontend-design`
  and `superpowers`). The genuine plugin ships under the `claude-code-plugins` marketplace —
  a different owner than the enabled entry names.
- `~/.claude/commands/ship.md` §4 therefore invokes three agents that never resolve
  (`code-reviewer`, `silent-failure-hunter`, `pr-test-analyzer`) and silently degrades to its
  written fallback `superpowers:requesting-code-review`.
- The automation layer is five hooks plus `lib/common.py` and `lib/agentignore.py`, 926 LOC,
  with `~/.claude/hooks/tests/run.sh` running five unittest suites and a hostile-input
  degradation matrix over every hook.
- `~/.claude` is **not a git repository** (`git rev-parse --is-inside-work-tree` →
  `fatal: not a git repository`). This repo tracks only `README.md`, `CLAUDE.md`, `LICENSE`,
  `.claude/skills/gentic*`, `docs/gentic/`. The entire automation layer exists in one
  uncommitted copy.
- `hooks/stop.py:5` states: "This is the only routine hard block in the setup," and
  `stop.py:9-13` documents the safety property — the gate fires at most once per user prompt,
  so a false positive costs one turn and can never trap the user.
- `hooks/post_tool_use.py` currently records two things per turn: `code_changed` (a non-prose
  file was edited) and `evidence` (a recognised verification command succeeded). Its
  `settings.json` matcher is `Bash|Edit|Write|MultiEdit|NotebookEdit` — it does **not** see
  subagent invocations.
- `hooks/user_prompt_submit.py:4-6` establishes the cost rule for always-on hooks:
  deterministic regex, no model round-trip.
- `.claude/skills/gentic-execute/SKILL.md:40` is the whole of the orchestration spec:
  "Independent tasks of 3+ points may be dispatched to subagents when available." No agent is
  named, no payload contract, no merge protocol.
- `.claude/skills/gentic-masterprompt/SKILL.md:62` offers an optional "fresh-eyes critic"
  subagent the same undefined way; `.claude/skills/gentic-iterate/SKILL.md:19` closes on
  `superpowers:verification-before-completion` with no adversarial auditor.
- The gentic skills are duplicated between `.claude/skills/` (tracked) and `~/.claude/skills/`
  (global). `ROUTING.md` exists **only** in the global copy.
- `~/.claude/skills/` also contains `cua-driver`, `zcontext`, `use-railway`, and `learned` —
  **none of which belong to this repo.** They must survive installation untouched.
- Agent file convention to imitate
  (`~/.claude/plugins/marketplaces/claude-code-plugins/plugins/pr-review-toolkit/agents/code-reviewer.md:1-8`):
  YAML frontmatter `name` / `description` (with worked `<example>` blocks that teach when to
  invoke) / `model` / `color`, then a prose system prompt. Its confidence rubric
  (`:20-30`) scores findings 0-100 and reports only ≥80.

## Decisions

From `decisions.md`. Four settled by the user in the interview round; three adopted from the
brief's recommended defaults and flagged.

1. **Repo is canonical; an installer syncs it into `~/.claude/`.** Import the hooks, commands,
   and `ROUTING.md` into the repo; add agents there; ship `install.sh`. *(user)*
2. **Four agents, no more**: `code-reviewer`, `dod-auditor`, `masterprompt-critic`,
   `task-executor`. *(user)*
3. **Delete the phantom `pr-review-toolkit` entry** from `settings.json`; `/ship` uses the
   first-party agents; the plugin is named only as an optional composition point. *(user)*
4. **Review trigger is an advisory Stop-hook nudge**, plus a `/review` command. It never
   blocks. *(user)*
5. **Orchestration is a written dispatch contract in `gentic-execute`**, not new machinery and
   not a `Workflow` script — a `Workflow` script would bind gentic to a harness feature that is
   not present everywhere, breaking its portability claim. *(default — unconfirmed)*
6. **Verification is a structural validator** added to the existing harness, plus a
   seeded-defect invocation of `code-reviewer`. *(default — unconfirmed)*
7. **`install.sh` also syncs the skills and `ROUTING.md`**, and the harness checks the repo
   tree and `~/.claude` tree match. *(default — unconfirmed)*

## Constraints

- **The installer must never delete what it does not own.** `~/.claude/skills/` contains
  `cua-driver`, `zcontext`, `use-railway`, `learned`; `~/.claude/` contains sessions, plugins,
  memory, and state. `install.sh` may create and overwrite only the paths the repo ships. No
  `rsync --delete`, no `rm -rf` above a repo-owned directory.
- **Back up `settings.json` before editing it**, with today's date, and document the exact
  restore command — the pattern `settings.json.bak-2026-08-17` already set.
- **Additive hook changes only, and only to three files.** The sanctioned edits are
  `hooks/stop.py` (append the advisory nudge *after* the existing gate's early returns),
  `hooks/post_tool_use.py` (record subagent review invocations), and `settings.json`
  (widen the `PostToolUse` matcher, drop the phantom plugin entry). The existing verification
  gate's behaviour and its once-per-prompt safety property must be unchanged after this run.
- **Deterministic and cheap in always-on paths.** The Stop hook fires every turn; the nudge
  must be regex/state logic, no model call.
- Every hook stays fail-open via `common.safe_main(main)`.
- Python 3 standard library only — the README advertises no dependencies.
- Run commits land only on `gentic/agent-automation-suite`; never push, never open a PR
  (`ROUTING.md`).
- English identifiers and comments; comments only for non-obvious intent (`~/.claude/CLAUDE.md`).

## Non-goals

- **Not installing `pr-review-toolkit`** or any other plugin.
- **Not building a `Workflow`-tool orchestration script**, agent swarm, or parallel-execution
  engine. The orchestration deliverable is a written contract.
- **Not adding a fifth agent**, however tempting a `security-auditor` or `debugger` looks.
- **Not changing gentic's five-phase structure**, its Fibonacci sizing, or its budget.
- **Not rewriting existing hook logic.** `pre_tool_use.py`, `session_start.py`,
  `user_prompt_submit.py`, `lib/agentignore.py` are touched only if a DoD item forces it.
- **Not adding a second hard block.** The nudge is advisory, full stop.
- **Not pushing, opening a PR, or merging anything into `main`.**
- **No CI.** No `.github/workflows`; the harness is run by hand and by `/ship`.
- **No symlink mode, no `uninstall.sh`, no versioning/packaging of the repo as a plugin or
  marketplace.** `install.sh` copies, and that is its whole job.
- **No Windows support.** `install.sh` targets bash on macOS/Linux, matching the existing
  `hooks/tests/run.sh`.
- **No rewrite of `/ship` outside §4**, and no new slash commands beyond `/review`.
- **Not migrating the other `~/.claude/skills/` (`zcontext`, `cua-driver`, `use-railway`,
  `learned`) into this repo.** They are not this project's.
- **Not making the agents depend on this repo.** `code-reviewer` must work in any repo.
  `dod-auditor`, `masterprompt-critic`, and `task-executor` are gentic-shaped by nature — that
  is intended — but they must be given their inputs in the invocation and must degrade with a
  clear message rather than erroring when no `docs/gentic/` run directory exists.

## Definition of Done

Checks run from the repo root on branch `gentic/agent-automation-suite`.

- [ ] **1. Four agent files exist with valid, self-consistent frontmatter.**
      Verify: `python3 .claude/hooks/tests/test_structure.py` passes its agent cases —
      exactly the four named files in `.claude/agents/`, each with parseable YAML frontmatter
      carrying `name`, `description`, `model`, and `name` equal to the filename stem.
- [ ] **2. Every *first-party* cross-reference in the setup resolves.** No skill, agent,
      command, or hook names a repo-shipped skill, agent, or hook path that does not exist —
      the class of defect that produced the `pr-review-toolkit` ghost. References to things
      supplied by optional external plugins (`superpowers:*`, `pr-review-toolkit`) are exempt
      **only** on a line containing the word `optional` or `if available`; an unqualified
      reference to an external agent fails the check.
      Verify: `python3 .claude/hooks/tests/test_structure.py` resolvable-reference cases pass;
      and `grep -rn "pr-review-toolkit" .claude/ README.md` returns only such qualified lines.
- [ ] **3. No `enabledPlugins` entry names an uninstalled plugin.** This checks live machine
      state, not repo state, so on a machine without those files the case must **skip**, not
      fail — a fresh clone must still get a green harness.
      Verify: `python3 .claude/hooks/tests/test_structure.py` cross-checks every
      `"…": true` entry in `~/.claude/settings.json` against
      `~/.claude/plugins/installed_plugins.json`; zero unmatched entries, or a reported skip
      when either file is absent.
- [ ] **4. The repo contains the full automation layer, tracked, without build artefacts.**
      Verify: each of
      `git ls-files .claude/hooks | wc -l`, `git ls-files .claude/commands | wc -l`,
      `git ls-files .claude/agents | wc -l`, `git ls-files .claude/skills | wc -l`
      is non-zero; `git ls-files | grep -c '__pycache__\|\.pyc$'` is `0`; and
      `git status --porcelain` is empty after the final commit.
- [ ] **5. `install.sh` is idempotent.**
      Verify: `bash install.sh && bash install.sh` — the second run exits 0 and reports zero
      changed files.
- [ ] **6. `install.sh --check` detects drift and passes when synced.**
      Verify: `bash install.sh --check` exits 0 immediately after an install; then
      `printf '\n# drift\n' >> ~/.claude/agents/code-reviewer.md && bash install.sh --check`
      exits non-zero naming that file; restore with `bash install.sh`.
- [ ] **7. `install.sh` destroys nothing it does not own.**
      Verify: after `bash install.sh`, all of `~/.claude/skills/zcontext`,
      `~/.claude/skills/cua-driver`, `~/.claude/skills/use-railway`, `~/.claude/skills/learned`
      still exist (`test -d` each); and `grep -nE '(rsync[^|]*--delete|rm -rf)' install.sh`
      returns no line whose target is above a repo-owned directory.
- [ ] **8. The existing hook harness is fully green.**
      Verify: `bash .claude/hooks/tests/run.sh` exits 0 with no `FAIL` line in its output.
- [ ] **9. The review nudge fires exactly when it should.**
      Verify: `python3 .claude/hooks/tests/test_review_nudge.py` passes cases —
      (a) code changed + no review this session → nudge text present;
      (b) code changed + review recorded → silent;
      (c) no code changed → silent;
      (d) nudge already shown this session → silent (once per session, not per turn).
- [ ] **10. The nudge never blocks.**
      Verify: same test asserts the hook exits 0 and its stdout contains no
      `"decision": "block"` on every nudge path.
- [ ] **11. The existing verification gate is behaviourally unchanged.**
      Verify: `python3 .claude/hooks/tests/test_gate.py` passes with the same test count as
      before this run (record the before-count in `progress.md` at task 1).
- [ ] **12. A review invocation is recorded as such.** The nudge's "review ran" signal is real,
      not assumed.
      Verify: `test_review_nudge.py` feeds a `PostToolUse` payload for a subagent invocation
      naming `code-reviewer` (under both `Task` and `Agent` tool names) and asserts
      `reviewed` is set in the turn state.
- [ ] **13. `/review` exists and names only resolvable agents.**
      Verify: `.claude/commands/review.md` present with a `description` frontmatter field, and
      DoD item 2's reference check covers it.
- [ ] **14. `/ship` §4 invokes first-party agents.**
      Verify: `grep -n "code-reviewer\|dod-auditor" .claude/commands/ship.md` matches in §4,
      and `grep -n "silent-failure-hunter\|pr-test-analyzer" .claude/commands/ship.md` returns
      nothing outside an explicitly-optional line.
- [ ] **15. `gentic-execute` carries a real dispatch contract.** The section uses four fixed
      sub-headings so the check is mechanical, not a judgement call.
      Verify: `grep -n "task-executor" .claude/skills/gentic-execute/SKILL.md` matches, and
      all four of `grep -c "^\*\*Receives:\*\*"`, `"^\*\*Returns:\*\*"`,
      `"^\*\*Parent merges by:\*\*"`, `"^\*\*Isolation required when:\*\*"` return `1`
      against that file.
- [ ] **16. The spec and done-ness phases name their scrutinising agent.**
      Verify: `grep -n "masterprompt-critic" .claude/skills/gentic-masterprompt/SKILL.md` and
      `grep -n "dod-auditor" .claude/skills/gentic-iterate/SKILL.md` each match.
- [ ] **17. `code-reviewer` finds planted defects and resists a decoy.**
      Verify: invoke the `code-reviewer` agent on
      `.claude/hooks/tests/fixtures/seeded_defect.py`, which contains two planted defects (a
      swallowed exception, and a documented-convention violation) and one decoy (a cosmetic
      naming quibble). It must report both defects at confidence ≥80 and must **not** report
      the decoy. *This check requires an `Agent` invocation; see Risks.*
- [ ] **18. The nudge costs almost nothing.** The Stop hook runs on every turn, so cost is
      measured against a recorded baseline, not asserted.
      Verify: at task 1, record the median wall time of 20 `stop.py` runs on a
      no-op payload (the pre-change baseline). At Iterate, repeat with 20 runs on a
      nudge-triggering payload. Median total under 150 ms **and** median delta over baseline
      under 50 ms. Both numbers recorded in `progress.md`.
- [ ] **19. Rollback is documented and the backup exists.**
      Verify: `test -f ~/.claude/settings.json.bak-2026-08-19`, and
      `grep -n "bak-2026-08-19" .claude/hooks/README.md` shows the exact restore command.
- [ ] **20. The README documents the agents and the installer, and contradicts nothing.**
      Verify: `grep -c "code-reviewer\|dod-auditor\|masterprompt-critic\|task-executor" README.md`
      returns ≥4; `grep -n "install.sh --check" README.md` matches; and
      `grep -n "cp -R .claude/skills" README.md` returns nothing — the superseded copy-paste
      install instruction is gone, not merely relocated.

## Risks & early signals

- **DoD 17 needs an `Agent` invocation, which this session is told not to make unrequested.**
  Early signal: reaching Iterate with item 17 unchecked. Handling: ask the user for explicit
  go-ahead to run that one invocation; if declined, mark 17 `deferred — user declined`, keep
  the fixture and the documented command in the repo, and say so in the final report. Do not
  quietly drop it and do not weaken the item.
- **Hook payload tool naming.** The subagent tool may appear as `Task` or `Agent` depending on
  harness version. Early signal: item 12's test passing for one name only. Handling: accept
  both, which is what item 12 requires.
- **Widening the `PostToolUse` matcher touches live config.** A malformed `settings.json`
  breaks every hook at once. Early signal: `run.sh` degradation section failing. Handling:
  back up first (item 19), validate with `python3 -m json.tool` before saving.
- **Installing over `~/.claude` is the one destructive-capable step in this run.** Early
  signal: item 7 failing. Handling: write `install.sh --check` and the ownership test *before*
  the first real `install.sh` run.
- **Importing the hooks into the repo could fork them from the live copies.** Early signal: two
  diverging edits during Execute. Handling: import first, as task 1, then edit only the repo
  copy and re-run `install.sh`.
- **Scope pressure toward a fifth agent or a Workflow orchestrator.** Early signal: a task
  appearing that no DoD item checks. Handling: the Non-goals list is the answer.

## Decomposition note (from the critique pass)

This mission is close to two: (a) make the repo canonical and add the installer, (b) build the
four agents and close the three gaps. It stays one run because (a) is the precondition that
makes (b) trackable and testable — splitting would leave the agents untested in a second run's
scope. Execute must therefore order (a) strictly first; a task from (b) landing before the
import would fork the hooks between the repo and `~/.claude`.

## Iteration budget

13 (initial allocation — the live balance is `progress.md`'s; amendments never reset it)
