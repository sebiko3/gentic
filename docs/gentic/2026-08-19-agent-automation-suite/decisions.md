# Decisions: agent-automation-suite

One interview round. Four decisions the user settled; three adopted from the brief's
recommended defaults because leverage × uncertainty did not earn a question.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Home for agents and automation | **Repo canonical + installer.** Import `~/.claude/hooks/`, `~/.claude/commands/`, and the `ROUTING.md` into this repo under `.claude/`; add new agents under `.claude/agents/`; ship an `install.sh` that syncs the tree into `~/.claude/`. | Global-only (`~/.claude`, untracked); repo-only (tracked but inert on other projects) | Only option that is simultaneously tracked, reviewable, testable, and universal. Also repairs the scouted finding that 926 LOC of working automation exists in exactly one uncommitted copy. | user |
| Agent roster | **Four gap-fillers**: `code-reviewer`, `dod-auditor`, `masterprompt-critic`, `task-executor`. | Broader roster (+security-auditor, test-analyzer, debugger, architect); review agents only | Each maps to a gap scouting documented. Invented roles fill no observed gap and risk agents nobody invokes; a narrower set leaves the orchestration and spec gaps open. | user |
| Phantom `pr-review-toolkit` entry | **Remove the false `enabledPlugins` entry**; point `/ship` §4 at the first-party agents; keep the plugin named as an optional composition point only. | Install the real plugin from the `claude-code-plugins` marketplace; install it *and* build first-party agents | The entry is currently false config — it must go either way. First-party matches the repo's advertised no-dependency ethos, and the new agents supersede the plugin's overlap. | user |
| Review trigger | **Advisory Stop-hook nudge**: when a session changed code and no review ran, print a one-line suggestion. Never blocks. Plus a `/review` command as the explicit entry point. | Invocation-only (no hook); hard block on unreviewed done-claims | Closes the "only if you remember" gap without a second adversarial gate. `hooks/stop.py:5` states the verification gate is deliberately the setup's only routine hard block. | user |
| Orchestration approach | **Explicit dispatch contract written into `gentic-execute`**, naming `task-executor`: what the subagent receives, what it must return, how results merge, when worktree isolation is required. | Leave fan-out as prose and improvise; build a `Workflow`-tool orchestration script | The scouted gap (`gentic-execute/SKILL.md:40`) is an undefined contract, not missing machinery. A `Workflow` script would bind the workflow to a harness feature that is not present everywhere, breaking gentic's portability claim. | default — unconfirmed |
| Verification layer for this run | **Extend `hooks/tests/run.sh`** with a structural validator (agent/skill/command frontmatter parses; `name` matches filename; every referenced skill, agent, and hook path resolves) plus one seeded-defect invocation of `code-reviewer`. | Manual walkthrough only | Gentic requires every Definition-of-Done item to name its check; markdown agents are otherwise unverifiable. A resolvable-reference check is precisely what would have caught the `pr-review-toolkit` / `/ship` breakage before it shipped. | default — unconfirmed |
| Repo ↔ `~/.claude` skill duplication | **Repo is canonical; `install.sh` syncs skills, hooks, commands, agents, and `ROUTING.md`**, with a harness check that the two trees match. | Accept drift | Cheap once the installer from decision 1 exists, and it stops this run's own edits from landing in only one of the two copies. | default — unconfirmed |

## Not decided here

- Whether to push or open a PR. Out of scope for a run by ROUTING.md; `/ship` owns that and only
  the user types it.
- Whether `main` should be fast-forwarded to include the hooks-era commits. This run branches
  from `gentic/universal-claude-setup`, which carries them; merging is a separate call.
