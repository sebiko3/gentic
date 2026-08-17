# Masterprompt: universal-claude-setup

## Mission

Every Claude Code session, in every project on this machine, should start already knowing the user's working discipline and should be structurally unable to skip the parts that matter: it notices what kind of request came in and routes accordingly, runs ambiguous or multi-step work through a spec-first workflow with durable artifacts, and cannot announce success on a code change without evidence that something was actually run. Git and GitHub work is fully automated but only inside one explicitly typed command. The outcome is a populated `~/.claude/` automation layer — hooks, globally-available skills, one command — that survives a broken hook, a non-git directory, and an unknown toolchain without breaking the session.

## Context

- Claude Code **2.1.193**, macOS arm64. `jq`, `gh` (authed as `sebiko3`), `git`, `node`, `python3` all present. Python 3 is the hook language — it is Anthropic's own choice in `hookify`.
- `~/.claude/hooks/`, `~/.claude/agents/`, `~/.claude/commands/` are **empty**; `~/.claude/settings.json` has **no `hooks` key**. This is greenfield — nothing to migrate, but also no existing safety net.
- superpowers 5.1.0 registers exactly one hook (`SessionStart`, injecting its primer). Its 14 skills are advisory only. That advisory-ness is the gap this run closes.
- gentic currently lives only in this repo at `.claude/skills/{gentic,gentic-scout,gentic-interview,gentic-masterprompt,gentic-execute,gentic-iterate}/SKILL.md`.
- **Verified against the installed binary** (string scan of `~/.local/share/claude/versions/2.1.193`): `hookSpecificOutput` (112), `updatedInput` (227), `permissionDecision`, `additionalContext`, `systemMessage`, `stopReason`, `statusMessage` all present. Hook types `command`, `http`, `mcp_tool`, `agent` all present. **`updatedPrompt` and `updatedOutput`: zero matches.**
- Reference hook shape (`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/hookify/hooks/userpromptsubmit.py`): read `json.load(sys.stdin)`, print one JSON object to stdout, `sys.exit(0)` inside `finally:`, and convert even an ImportError into a `systemMessage` rather than a crash.
- Shell-injection precedent (`ruflo/plugin/hooks/hooks.json`, `_security_note`): tool input must never be interpolated into a shell string.
- `~/.claude/CLAUDE.md` forbids unrequested commits, pushes and PRs, and requires evidence before success claims. It outranks this request.

## Decisions

From `decisions.md` — user-confirmed unless marked:

- **Git autonomy:** nothing git-related fires unprompted; a single `/ship` command runs branch → commits → verify → PR unattended. `~/.claude/CLAUDE.md` is left untouched.
- **Spec engine:** gentic promoted to `~/.claude/skills/`, composing superpowers at its existing marked points.
- **Enforcement:** advisory injection for routing; `exit 2` only on objectively checkable conditions.
- **Packaging:** directly in `~/.claude/`, not a plugin.
- *(default — unconfirmed)* **Intent classification:** deterministic Python, no LLM on the per-prompt path.
- *(default — unconfirmed)* **Verification gate:** `Stop` blocks a done-claim only when no verification command ran that turn.
- *(default — unconfirmed)* **Artifacts:** `docs/gentic/<date>-<slug>/` in-repo, falling back to `~/.claude/gentic-runs/<project>/`.
- *(default — unconfirmed)* **Plugin reuse:** enable `pr-review-toolkit` only.
- *(default — unconfirmed, platform-forced)* **Prompt transformation:** context injection, never rewriting.
- *(default — unconfirmed)* **Failure posture:** hooks always exit 0 on their own errors.

### Interpretation resolved during critique

Globalising gentic imports its rule that runs make checkpoint commits, which appears to contradict "nothing git-related fires unprompted." **Resolved reading:** a gentic run's checkpoint commits are permitted, because entering a run *is* the explicit ask — but they are confined to a `gentic/*` branch and must never land on `main`, `master`, or any branch the user was already on. Creating that branch is itself part of entering Execute. Push and PR remain `/ship`-only. This reading is `unconfirmed` and must appear in the final report.

## Constraints

- **Hook scripts may never fail the session.** Any internal error exits 0 with a `systemMessage`. Only deliberate policy decisions use exit 2.
- **No LLM call in `UserPromptSubmit`, `PostToolUse`, or `Stop`.** These are hot paths.
- **`UserPromptSubmit` must complete in under 150 ms** measured on this machine — it taxes every prompt the user ever types.
- No shell interpolation of any hook payload field; parse JSON in Python, never in a shell string.
- Never write into any project's own `.claude/` directory.
- Must no-op safely with: no git repo, an empty directory, an unrecognised toolchain, and a payload missing any optional field.
- Python 3 standard library only — no pip installs.
- macOS/`bash`+`zsh` only.
- Existing `~/.claude/settings.json` keys must survive untouched.

## Non-goals

This run will **not**:

- Replace, disable or modify superpowers, `frontend-design`, or `andrej-karpathy-skills`; and will not enable `sheldon`, `ecc`, or `ruflo`.
- Write new code-review agents — `pr-review-toolkit`'s six existing agents are reused as-is.
- Commit, push, or open a PR outside an explicit `/ship` invocation.
- Build a general rules DSL, config UI, TUI, telemetry dashboard, or MCP server. `hookify` already occupies the DSL niche.
- Support Windows or PowerShell.
- Touch CI configuration in any repository.
- Guarantee toolchain detection for every language — see the "unknown toolchain" degradation requirement instead.
- Modify `~/.claude/CLAUDE.md`.

## Specification

### Component 1 — `~/.claude/hooks/lib/common.py`

Shared helpers: `read_payload()` (tolerant of empty/malformed stdin, returns `{}`), `emit(obj)` + `emit_context(text)`, `safe_main(fn)` decorator guaranteeing exit 0 on any exception with the error as `systemMessage`, `state_path(session_id)` → `~/.claude/state/<session_id>.json`, `load_state`/`save_state` (atomic write via temp+rename), `git_root(cwd)` → path or `None`, `prune_state(days=7)`.

### Component 2 — `UserPromptSubmit` → `~/.claude/hooks/user_prompt_submit.py`

Deterministic classifier over `payload["prompt"]`. Emits **nothing** unless a rule fires (silence is the common case).

Classify as **non-trivial** — inject the routing directive — when any holds:
- prompt contains an explicit workflow invocation (`/gentic`, "resume", "continue where"), **or**
- prompt length ≥ 240 characters, **or**
- it contains ≥ 2 of: a vague load-bearing adjective (`fast|simple|robust|clean|secure|scalable|better|nice`), a multiplicity marker (`all |every |each |across |refactor|migrate|rewrite`), a consequence marker (`auth|password|token|secret|payment|billing|delete|drop |production|deploy|public api`), or a sequencing marker (`then |after |first |and then`).

Classify as **trivial** — stay silent — when the prompt is a bare question (starts with `what|why|how|where|when|is |are |does |can |should ` and has no imperative verb) or is under 80 characters with no marker above.

When non-trivial, inject a short block (≤ 1200 characters) containing: the detected signals, a restated task frame (goal / ambiguity flags), and the directive to invoke the `gentic` skill before implementing. **Advisory — never `exit 2`.**

Additionally, when `git_root(cwd)` exists and `docs/gentic/*/progress.md` contains an unchecked phase box, append a one-line resumable-run notice naming the run.

### Component 3 — `PostToolUse` → `~/.claude/hooks/post_tool_use.py`

Matcher `Bash|Edit|Write`. Writes to session state; injects no context.

- On `Bash`: if `tool_input.command` matches the verification pattern — `pytest|jest|vitest|npm (test|run test)|yarn test|pnpm test|go test|cargo test|make test|tsc|mypy|ruff|eslint|npm run (build|lint|typecheck)|cargo (build|check|clippy)|go build|swift test|xcodebuild` — record `{command, exit_code, ts}` into `state["evidence"]`. Exit code comes from the payload's tool output where available; when it cannot be determined, record `null` and treat it at Stop time as evidence-present-but-unproven.
- On `Edit|Write`: append `tool_input.file_path` to `state["touched"]`, and set `state["code_changed"] = true` when the path is not `.md`/`.txt`.

### Component 4 — `Stop` → `~/.claude/hooks/stop.py`

The only routine hard block. Blocks (`exit 2`, reason on stderr) when **all** hold:

1. `state["code_changed"]` is true this turn, **and**
2. `last_assistant_message` matches a done-claim: `\b(all set|done|complete[d]?|fixed|works now|working now|passing|verified|ready to (merge|ship))\b`, **and**
3. `state["evidence"]` contains no entry recorded since the last user prompt, **and**
4. `state["stop_block_fired"]` is not already set for this prompt.

**Escape hatch (mandatory):** condition 4 means the block fires at most once per user prompt. Setting the flag before exiting 2 guarantees the next Stop passes unconditionally — the user can never be trapped in a loop, even if the hook is wrong.

The stderr reason names what was edited and asks for the project's verification command to be run, or for the claim to be softened.

### Component 5 — `SessionStart` → `~/.claude/hooks/session_start.py`

Matcher `startup|resume`. Calls `prune_state(7)`. If inside a git repo with unfinished `docs/gentic/*/progress.md` runs, emits a `systemMessage` naming each run, its phase, and how to resume. Silent otherwise.

### Component 6 — `PreToolUse` → `~/.claude/hooks/pre_tool_use.py`

Matcher `Bash`. Emits `permissionDecision: "deny"` with a reason **only** for: `git push --force`/`-f` (without `--force-with-lease`), `git reset --hard` with uncommitted changes present, `git clean -fdx`, `git branch -D` on the current branch, and any `rm -rf` whose target resolves to `$HOME` or `/`. Everything else passes through with no decision. This encodes `~/.claude/CLAUDE.md`'s destructive-action rule.

### Component 7 — Global gentic skills

Copy the six `SKILL.md` trees from this repo's `.claude/skills/` to `~/.claude/skills/`. Add `~/.claude/skills/gentic/ROUTING.md` carrying the routing section of this repo's `CLAUDE.md` plus the artifact-location fallback and the `gentic/*`-branch-only commit rule, since the project `CLAUDE.md` will not be present in other repos.

### Component 8 — `~/.claude/commands/ship.md`

One command, fully automatic inside: verify current branch is not `main`/`master` (create `gentic/<slug>` if it is) → stage only files belonging to the change → checkpoint commit with an imperative subject and no AI attribution → run the detected verification command and abort on failure → dispatch `pr-review-toolkit` review agents → push → open a PR via `gh` with a body generated from the run's `masterprompt.md` Definition of Done. Aborts with a clear message rather than proceeding if `gh` is unauthenticated or no remote exists.

### Component 9 — `~/.claude/settings.json`

Add the `hooks` key wiring components 2–6, each with an explicit `timeout` (5s; 10s for `SessionStart`). Preserve every existing key. Back up to `~/.claude/settings.json.bak-<date>` first.

### Component 10 — `~/.claude/hooks/tests/run.sh`

A standalone harness that pipes representative payloads into each hook and asserts exit codes and JSON validity. It is the verification instrument for most DoD items below and must be runnable without restarting Claude Code.

## Definition of Done

- [ ] Every hook script exits 0 and emits either nothing or valid JSON for a well-formed payload — verify: `bash ~/.claude/hooks/tests/run.sh` exits 0 and prints no `FAIL`.
- [ ] Every hook script exits 0 on empty stdin and on malformed JSON — verify: harness case `degradation/empty-stdin` and `degradation/malformed-json` pass for all five scripts.
- [ ] `~/.claude/settings.json` remains valid JSON and retains all pre-existing keys — verify: `jq -e '.enabledPlugins["superpowers@claude-plugins-official"] and .theme and .hooks' ~/.claude/settings.json`.
- [ ] A backup of the pre-change settings exists — verify: `ls ~/.claude/settings.json.bak-*` returns at least one file and `jq . ` parses it.
- [ ] The classifier routes correctly on a labelled fixture set of ≥ 12 prompts (≥ 5 trivial, ≥ 5 non-trivial, ≥ 2 resume) with **zero** trivial-prompt false positives — verify: harness case `classifier` reports `12/12`.
- [ ] `UserPromptSubmit` completes in under 150 ms — verify: harness prints a measured median over 20 runs and asserts `< 150`.
- [ ] The Stop gate blocks a done-claim after a code edit with no evidence — verify: harness case `stop/blocks-unverified` asserts exit code 2.
- [ ] The Stop gate allows the same claim once a verification command is in the ledger — verify: harness case `stop/allows-verified` asserts exit code 0.
- [ ] The Stop gate never blocks a turn with no code edit — verify: harness case `stop/conversational` asserts exit code 0.
- [ ] The Stop gate cannot block twice for one user prompt — verify: harness case `stop/escape-hatch` runs the identical blocking payload twice and asserts exit 2 then exit 0.
- [ ] All hooks no-op cleanly outside a git repository — verify: harness case `degradation/no-git` runs every script with `cwd` set to a fresh empty temp dir, asserting exit 0 and no traceback on stderr.
- [ ] The destructive-git guard denies `git push --force` and allows `git push --force-with-lease` — verify: harness case `guard/force-push` asserts `permissionDecision == "deny"` then absent.
- [ ] All six gentic skills are globally discoverable — verify: `ls ~/.claude/skills/gentic*/SKILL.md | wc -l` prints `6`.
- [ ] `ROUTING.md` exists and states both the artifact-location fallback and the `gentic/*`-branch-only commit rule — verify: `grep -c 'gentic-runs' ~/.claude/skills/gentic/ROUTING.md` ≥ 1 and `grep -ci 'never .*main' ~/.claude/skills/gentic/ROUTING.md` ≥ 1.
- [ ] `/ship` exists and its git sequence cannot target `main`/`master` — verify: `grep -c 'main' ~/.claude/commands/ship.md` ≥ 1 in a guard clause, confirmed by reading the file.
- [ ] `pr-review-toolkit` is enabled — verify: `jq -e '.enabledPlugins["pr-review-toolkit@claude-plugins-official"]' ~/.claude/settings.json`.
- [ ] No hook writes into any project's `.claude/` directory — verify: `grep -rn "\.claude" ~/.claude/hooks/*.py ~/.claude/hooks/lib/*.py` shows only `~`-anchored or `CLAUDE_*`-derived paths.
- [ ] A documented one-line rollback restores the previous configuration — verify: the command in `~/.claude/hooks/README.md` is run in a scratch copy and `jq -e '.hooks | not'` succeeds afterwards.
- [ ] Nothing in the setup performs an LLM call on a hot path — verify: `grep -rn '"type": *"\(agent\|prompt\)"' ~/.claude/settings.json` returns no matches.

## Risks & early signals

- **A broken hook degrades every session in every project.** Early signal: any harness case failing, or `claude --debug` showing hook stderr. Mitigation: exit-0 posture, backup, tested-before-wired ordering (component 10 runs before component 9).
- **Stop-gate false positives are the most likely user-visible failure.** Early signal: the block firing on a turn where nothing was edited. Mitigation: the once-per-prompt escape hatch makes every false positive cost one extra turn, never a deadlock.
- **Classifier over-fires and injects on every prompt**, making the routing text ambient noise the model learns to ignore. Early signal: fixture false-positive count above zero. Mitigation: silence is the default branch; trivial prompts must produce empty output.
- **Version drift** — `updatedPrompt` may land in a later Claude Code build and make true prompt transformation possible. Early signal: the string appearing in a future binary. This spec's context-injection approach stays valid regardless.
- **Evidence ledger cannot read a Bash exit code** if the payload's tool output shape differs from expectation. Early signal: harness `stop/allows-verified` failing. Mitigation: `null` exit code is treated as evidence present.

## Iteration budget

13 (initial allocation — the live balance is `progress.md`'s; amendments never reset it)
