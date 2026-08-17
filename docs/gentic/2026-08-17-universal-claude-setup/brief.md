# Brief: universal-claude-setup

## Mission (as understood)

Build one setup, living outside any single project, that makes Claude Code behave the same disciplined way in every repo: read the user's prompt, work out what they actually want, shape that into a properly-formed task, produce a spec, implement against it, prove the result, and handle the git/GitHub side — with as much of that chain firing on its own as the platform genuinely allows, rather than depending on the model deciding to be disciplined that turn.

## Facts

- Claude Code **2.1.193**, macOS (arm64), binary at `~/.local/share/claude/versions/2.1.193` (`claude --version`).
- Tooling present: `jq`, `gh`, `git`, `node`, `python3`. `gh` is authenticated as **sebiko3** with an active token (`gh auth status`).
- **The automation layer is entirely empty.** `~/.claude/hooks/`, `~/.claude/agents/`, `~/.claude/commands/` all contain zero files (`ls`). `~/.claude/settings.json` has no `hooks` key at all.
- Enabled plugins (`~/.claude/settings.json` → `enabledPlugins`): `superpowers@claude-plugins-official`, `frontend-design@claude-plugins-official`, `andrej-karpathy-skills@karpathy-skills`. Disabled: `sheldon` (the user's own), `ecc`, `ruflo` (all four ruflo variants).
- **superpowers 5.1.0 registers exactly one hook** — `SessionStart` (matcher `startup|clear|compact`) injecting the `using-superpowers` primer (`~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/hooks/hooks.json`). Its 14 skills (brainstorming, writing-plans, executing-plans, test-driven-development, verification-before-completion, requesting-code-review, finishing-a-development-branch, …) are **advisory**: they fire only when the model elects to invoke them.
- gentic (this repo) is **project-local only** — six skills under `.claude/skills/`, so it does not exist in any other project. Its artifacts convention is `docs/gentic/<date>-<slug>/{brief,decisions,masterprompt,progress}.md`, committed (`CLAUDE.md`).
- The user's global `~/.claude/CLAUDE.md` is already a detailed operating contract covering scope discipline, evidence-based diagnosis, verification, and version control.
- Several **official plugins that cover parts of the request are installed-but-not-enabled**: `feature-dev` (code-explorer / code-architect / code-reviewer agents), `pr-review-toolkit` (6 review agents), `code-review`, `commit-commands` (`commit-push-pr`), `hookify`, `claude-code-setup`, `ralph-loop` (`~/.claude/plugins/marketplaces/claude-plugins-official/plugins/`).
- The user has previously authored and published a plugin + marketplace of their own: `sheldon` (`github.com/sebiko3/sheldon`), with `agents/`, `hooks/hooks.json`, `skills/`, `settings.json` — so plugin packaging is proven territory, not new ground.

### Hook capabilities — verified against the installed binary, not just the docs

Event names confirmed present by string search of the 2.1.193 executable: `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `SubagentStart`, `SubagentStop`, `TaskCompleted`, plus `SessionStart`/`Stop` (in active use by superpowers).

Hook `type` values confirmed present: `command`, `http`, `mcp_tool`, `agent` — so an **LLM-backed hook is available** (`type: "agent"`, default 60s, gets Read/Grep/Glob).

Output fields confirmed present: `hookSpecificOutput` (112 occurrences), `permissionDecision`, `permissionDecisionReason`, `additionalContext`, `updatedInput` (227), `systemMessage`, `stopReason`, `terminalSequence`, `statusMessage`, `asyncRewake`. Blocking path for prompts exists (`getUserPromptSubmitHookBlockingMessage`).

- **`updatedPrompt` and `updatedOutput` return zero matches in the binary**, while `updatedInput` returns 227 in the same scan. The published docs describe prompt rewriting via `hookSpecificOutput.updatedPrompt`; that capability is **not in the installed build**.

## Patterns to follow

- **Hook scripts must never break the session**: read JSON from stdin, print a JSON object to stdout, and `sys.exit(0)` in a `finally:` — including on import failure, where the error is surfaced as `systemMessage` rather than a crash (`.../plugins/hookify/hooks/userpromptsubmit.py`, `stop.py`). This is Anthropic's own reference shape; imitate it exactly.
- **Never interpolate tool input into a shell string.** Pipe stdin through `jq`, then `xargs -0` it as a single argv element — otherwise a `>` inside a tool argument gets re-parsed by the shell and writes stray files (`ruflo/plugin/hooks/hooks.json`, `_security_note`).
- **Matcher + `${CLAUDE_PLUGIN_ROOT}` + explicit `timeout`** on every entry (`sheldon/hooks/hooks.json`).
- gentic's discipline is worth preserving wholesale: durable artifact per phase, an explicit gate before advancing, one checkpoint commit per task, and any decision the user did not personally make flagged `default — unconfirmed` (`CLAUDE.md`).

## Constraints discovered

- **No prompt rewriting.** Intent shaping must be done by *injecting context alongside* the prompt (exit-0 stdout / `additionalContext` on `UserPromptSubmit`), not by replacing the user's words. Any design that depends on literally rewriting the prompt is unbuildable here.
- **`UserPromptSubmit` fires on every single prompt**, so its cost is paid on every turn. A `type: "agent"` or `type: "prompt"` classifier there adds an LLM round-trip to every message the user sends.
- Hooks cannot make the model *want* to follow a skill; they can inject text, block an action, or veto a stop. Enforcement is therefore only as reliable as the condition is objective.
- `SessionEnd` hooks share a 1.5s budget; `MessageDisplay` fires during streaming with a 10s default — neither is a safe place for real work.
- **The request collides with the user's own standing rule.** `~/.claude/CLAUDE.md` states: "Do not commit, push, create pull requests, alter history … unless explicitly asked," and requires approval before substantial or irreversible work. "Manage github … automatically" cannot be delivered without either narrowing it or amending that contract. Per the same file, user instructions outrank everything else, so this must be resolved explicitly rather than assumed.
- Must degrade safely outside a git repo, in an empty directory, and in repos where writing artifact files is unwelcome.
- Ecosystem risk: three parallel systems already overlap (superpowers skills, gentic phases, sheldon missions). Adding a fourth engine would make the problem worse, not better.

## Open decisions (ranked by leverage)

1. **Automation vs. the user's own version-control rule** — options: (A) fully automatic commit/push/PR; (B) automatic checkpoint commits on a work branch, PR/push explicitly requested; (C) nothing automatic, but a single command runs the whole ship sequence end-to-end. **Recommended default: C, plus B's checkpoint commits scoped to the run branch only** — because `~/.claude/CLAUDE.md` explicitly forbids unrequested commits and pushes, and that file outranks this request. Adopting A or B means deliberately amending CLAUDE.md, which should be the user's conscious call, not a side effect.

2. **Which engine owns spec → execute → verify** — options: (A) promote gentic to global and route into it; (B) drive superpowers' brainstorming → writing-plans → executing-plans; (C) write a new engine. **Recommended default: A** — gentic already encodes the phase/gate/artifact/resume discipline the request describes, its `CLAUDE.md` already declares composition points into superpowers skills, and it is the user's own design. C guarantees a fourth competing system.

3. **Packaging** — options: (A) direct in `~/.claude/` (settings.json hooks + `skills/` + `agents/`); (B) a personal plugin in the user's `sheldon` marketplace. **Recommended default: A** — it is global the moment it is written, with no marketplace round-trip or enablement step, and `~/.claude/hooks|agents|commands` are empty and waiting. Packaging as a plugin stays available later once the shape has proven itself.

4. **Enforcement strength** — options: (A) hard-block via exit 2 on `UserPromptSubmit`/`Stop`; (B) advisory context injection only; (C) advisory routing, hard-block reserved for narrow objective conditions. **Recommended default: C** — hard-blocking on a judgement call ("is this task non-trivial?") produces deadlocks the user cannot escape, while blocking on a checkable fact ("progress.md has unchecked Definition-of-Done items") is safe and is exactly the leverage hooks provide.

5. **Intent classification mechanism** — options: (A) `type: "agent"`/`"prompt"` LLM hook on every prompt; (B) deterministic script (keyword/shape heuristics + repo state); (C) no classifier, always inject the routing rule. **Recommended default: B** — it costs no tokens and no latency on a per-prompt hot path, and the routing decision in `CLAUDE.md` is already expressed as checkable conditions. Escalate to A only where B measurably misroutes.

6. **Verification gate mechanism** — options: (A) `Stop` hook runs the project's test command every turn; (B) `Stop` hook blocks only when the response claims done/fixed/passing without a verification command having run; (C) advisory reminder. **Recommended default: B** — (A) is far too slow and fires on conversational turns, while (B) targets precisely the failure the user is trying to eliminate, and matches `verification-before-completion`'s intent with actual teeth.

7. **Artifact location in arbitrary repos** — options: (A) `docs/gentic/<date>-<slug>/` committed, as today; (B) `~/.claude/runs/<project>/` outside the repo; (C) A by default with an opt-out. **Recommended default: C** — keeps the existing committed-documentation convention where it is welcome, without forcing files into repos the user does not own.

8. **Reuse of the already-installed official plugins** — options: (A) enable `feature-dev` + `pr-review-toolkit` + `commit-commands` and orchestrate them; (B) write equivalent agents; (C) enable none. **Recommended default: A for `pr-review-toolkit` only** — its six review agents are directly reusable for the verify stage, whereas `feature-dev` would duplicate gentic's phases and reintroduce the competing-engine problem.
