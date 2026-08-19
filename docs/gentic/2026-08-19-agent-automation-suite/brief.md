# Brief: agent-automation-suite

## Mission (as understood)

Add a set of purpose-built subagents to this Claude Code setup, and tighten the surrounding
automation in three named areas: **code review** (today it only happens if the user types
`/ship`, and its primary path is broken), **orchestration** (gentic mentions subagent fan-out
twice but defines no agent and no dispatch contract), and **spec-driven development** (the
gentic five-phase workflow, which works but has no fresh-eyes critic and no adversarial
done-ness auditor). The deliverable is configuration and prose — agent definitions, skill
edits, possibly hook code — not application code.

## Facts

- **Zero custom subagents exist.** `~/.claude/agents/` is present but empty (`ls -la` — 0
  entries, created May 18). The agent types offered this session are only the built-ins:
  `claude`, `claude-code-guide`, `Explore`, `general-purpose`, `Plan`, `statusline-setup`.
- **`pr-review-toolkit` is enabled but not installed.** `settings.json:11` sets
  `"pr-review-toolkit@claude-plugins-official": true`, but the plugin is absent from
  `~/.claude/plugins/installed_plugins.json` and from
  `~/.claude/plugins/cache/claude-plugins-official/` (which holds only `frontend-design` and
  `superpowers`). The real plugin ships in the *`claude-code-plugins`* marketplace, a
  different owner than the enabled entry names.
- **Consequence: `/ship`'s review step never runs its primary path.** `~/.claude/commands/ship.md`
  §4 invokes `code-reviewer`, `silent-failure-hunter`, `pr-test-analyzer` — none of which
  resolve. Its written fallback (`superpowers:requesting-code-review`) does exist and works,
  so review degrades rather than vanishing, but silently and less thoroughly than the file
  advertises.
- **Review is never automatic.** Nothing in the five hooks triggers or nags about review;
  `/ship` is the only entry point, and only the user can type it.
- **The hooks layer is real and tested**: 5 hooks + shared `lib/common.py` + `lib/agentignore.py`,
  926 LOC total, with `~/.claude/hooks/tests/run.sh` running 5 unittest suites plus a
  hostile-input degradation matrix over every hook.
- **That entire layer is untracked.** `~/.claude` is not a git repository (`git rev-parse`
  → `fatal: not a git repository`), and this repo contains only `README.md`, `CLAUDE.md`,
  `LICENSE`, `.claude/skills/gentic*`, and `docs/gentic/`. The hooks and `/ship` produced by
  the last two runs exist in exactly one uncommitted copy on this machine.
- **Orchestration is a stub.** `gentic-execute/SKILL.md:40` — "Independent tasks of 3+ points
  may be dispatched to subagents when available" — names no agent, no payload contract beyond
  "the full masterprompt, its single task, and return evidence", and no merge protocol.
  `gentic-masterprompt/SKILL.md:62` offers an optional "fresh-eyes critic" subagent the same way.
- **The gentic skills are duplicated.** Identical trees at `.claude/skills/gentic*` (tracked)
  and `~/.claude/skills/gentic*` (global, untracked). `~/.claude/skills/gentic/ROUTING.md`
  exists only in the global copy — it carries the machine-wide rules this repo keeps in
  `CLAUDE.md`. There is no sync mechanism; drift is unpoliced.
- **This repo has no executable test layer of its own** — no manifest, no runner. The only
  runnable check for this setup lives outside the repo at `~/.claude/hooks/tests/run.sh`.
- Superpowers 5.1.0 *is* genuinely installed and supplies `requesting-code-review`,
  `dispatching-parallel-agents`, `subagent-driven-development`, `test-driven-development`,
  `systematic-debugging`, `verification-before-completion`.

## Patterns to follow

- **Agent file shape** (`~/.claude/plugins/marketplaces/claude-code-plugins/plugins/pr-review-toolkit/agents/code-reviewer.md:1-8`):
  YAML frontmatter `name` / `description` (with worked `<example>` blocks driving invocation)
  / `model` / `color`, then a prose system prompt.
- **Confidence-gated findings** (`code-reviewer.md:20-30`): score each issue 0-100 against a
  published rubric and **report only ≥80**. This is the false-positive discipline worth copying
  — an agent that reports everything gets ignored.
- **Hook design voice** (`hooks/stop.py:1-13`, `post_tool_use.py:1-8`): every hook opens with a
  docstring naming its *design principle* and its safety property. `stop.py` states the
  invariant explicitly — "blocks at most once per prompt, so a false positive costs one extra
  turn and can never trap the user in a loop."
- **One hard block, by deliberate choice** (`stop.py:5`): "This is the only routine hard block
  in the setup." New automation should be advisory unless there is an argument as strong as
  the verification gate's.
- **Deterministic-first** (`user_prompt_submit.py:4-6`): the always-on hook uses regex, not a
  model round-trip, because it fires on every prompt. Cost discipline for anything always-on.
- **Fail-open hooks**: every hook body is wrapped in `common.safe_main(main)`.
- **DoD items name their own check** (`gentic-masterprompt`), and `gentic-iterate:19` closes
  with `verification-before-completion`. Any new agent must return *evidence*, not adjectives.

## Constraints discovered

- Repo is markdown-only and README advertises "no dependencies" as a feature; any new
  executable code needs a justification and a test.
- `~/.claude/CLAUDE.md` forbids unrequested commits/pushes; ROUTING.md narrows run commits to a
  `gentic/<slug>` branch, never push, never PR.
- `main` lacks the hooks-era commits; current branch `gentic/universal-claude-setup` carries
  them. A new run branch must fork from the branch, not `main`, or it loses that context.
- Non-interactive session: per gentic's rule, unanswered interview questions take the scouted
  default and are flagged `default — unconfirmed`.
- The user's blanket delegation (memory: `user-delegates-decisions`, 2026-08-11) says decide on
  best judgment, flag transparently, don't block.
- Agents cannot be unit-tested by running them; verification for markdown agents has to be
  structural (frontmatter validity, resolvable references) plus one real invocation with a
  seeded defect.

## Open decisions (ranked by leverage)

1. **Where new agents and automation live** — options: (A) `~/.claude/` only, universal but
   untracked, repeating the mistake that left 926 LOC in a single uncommitted copy; (B) this
   repo's `.claude/` only, tracked but inert outside this repo; (C) repo is source of truth +
   an `install.sh` that copies/symlinks into `~/.claude/`, and the hooks layer is imported into
   the repo as part of this run. **Recommended default: C** — it is the only option that makes
   the new work both reviewable and universal, and it repairs the untracked-hooks finding,
   which is a precondition for testing anything added here.

2. **Which agents to build** — options: a broad roster (8-12 role agents) versus a small set
   aimed exactly at the three named gaps. **Recommended default: four agents** —
   `code-reviewer` (correctness, security, silent failures; confidence-gated ≥80),
   `dod-auditor` (adversarial: proves each Definition-of-Done item from evidence, or fails it),
   `masterprompt-critic` (zero-context fresh eyes: "what would you get wrong executing this?"),
   `task-executor` (takes masterprompt + one task, TDD, returns evidence) — because each one
   fills a gap this brief *documented*, and a roster of invented roles would fill none.

3. **The phantom `pr-review-toolkit` entry** — options: (A) install the real plugin from the
   `claude-code-plugins` marketplace and keep `/ship` as written; (B) remove the false entry and
   depend on the new first-party agents, keeping the plugin as an optional composition point.
   **Recommended default: B** — matches the repo's stated no-dependency ethos, and the agents
   in decision 2 supersede it; either way the enabled-but-missing entry must go, because it is
   currently a lie in the config.

4. **How review gets triggered** — options: (A) invocation only (`/ship`, `/review`);
   (B) an advisory Stop-hook nudge when a turn changed code and no review ran this session;
   (C) a hard block. **Recommended default: B, advisory** — `stop.py:5` reserves the single
   hard block for the verification gate, and a second one would make the setup adversarial; a
   nudge closes the "review only if the user remembers" gap without that cost.

5. **Orchestration: skill-level protocol vs. new machinery** — options: (A) leave fan-out as
   prose and let the model improvise; (B) write an explicit dispatch contract into
   `gentic-execute` (what the subagent receives, what it must return, how results merge, when
   worktree isolation is required) naming `task-executor`; (C) build a `Workflow`-tool
   orchestration script. **Recommended default: B** — the gap is an undefined contract, not
   missing machinery, and (C) binds the workflow to a harness feature that is not everywhere.

6. **Verification layer for this run** — options: (A) manual walkthrough only; (B) extend
   `hooks/tests/run.sh` with a structural validator for agent/skill files (frontmatter parses,
   `name` matches filename, every referenced skill or agent resolves) plus a seeded-defect
   invocation of `code-reviewer`. **Recommended default: B** — "every DoD item names its check"
   is unsatisfiable for markdown agents otherwise, and the resolvable-reference check is
   exactly what would have caught the `pr-review-toolkit` and `/ship` breakage.

7. **Skill duplication between repo and `~/.claude`** — options: (A) accept drift; (B) make the
   repo canonical and have `install.sh` sync both skills and `ROUTING.md`, with a test that the
   two trees match. **Recommended default: B**, folded into decision 1's installer — cheap once
   the installer exists, and it prevents this run's edits from landing in only one of the copies.


## Corrections (2026-08-19, found during Execute task 3)

- **The `pr-review-toolkit` fact was wrong in its mechanism.** The brief states the plugin is
  "absent from `~/.claude/plugins/installed_plugins.json`". It is **present** there — the
  earlier reading truncated the file at 40 lines and missed the entry. The actual defect is
  one level down: its recorded `installPath`
  (`~/.claude/plugins/cache/claude-plugins-official/pr-review-toolkit/unknown`) **does not
  exist on disk**, so the plugin is registered, enabled, and unloadable.
- **The conclusion drawn from it stands unchanged**, and is independently confirmed by this
  session's available-agent list containing no `code-reviewer`: `/ship` §4 invokes agents that
  never resolve, and review silently degrades. Decision 3 (remove the entry, go first-party) is
  unaffected.
- **The validator was strengthened as a result**: DoD item 3's check now requires each enabled
  plugin's `installPath` to exist, not merely that the registry names it. Checking the key
  alone would have reported this machine as healthy.
