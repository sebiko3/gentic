# Masterprompt: bootstrap-gentic

## Mission
Ship gentic: a self-contained, resumable, five-phase deep workflow (Scout → Interview → Masterprompt → Execute → Iterate) for Claude Code, delivered as six project skills plus a routing CLAUDE.md and a README, and demonstrated end-to-end by this bootstrap run's own artifacts.

## Context
- Empty MIT-licensed repo `gentic`; deliverable is the workflow system itself (brief.md: Facts).
- Skill mechanics: `.claude/skills/<name>/SKILL.md`; description = triggers only, ≤1024 chars; AskUserQuestion ≤4 questions/call (brief.md: Facts).
- Baseline probe established the failure modes to close: unasked questions, in-head plans, unmeasured adjectives (brief.md: Baseline probe).

## Decisions
See decisions.md — all `default — unconfirmed` (autonomous run). Headlines: five phases; orchestrator + phase-skill packaging; committed `docs/gentic/` artifacts; fibonacci as real mechanics (sizes, rungs, budget 13); never-block interview stance.

## Constraints
- Markdown only, zero dependencies; install = copy files.
- Works standalone; composes with superpowers skills only at marked, optional points.
- Frontmatter rules from superpowers:writing-skills (triggers-only descriptions, name = directory).
- Commits on branch `gentic/bootstrap-gentic`, `main` untouched.

## Non-goals
- No multi-agent orchestration requirement (optional inside Execute only).
- No CI, eval harness, or plugin/marketplace packaging.
- No automation hooks (settings.json) — routing stays instruction-level in CLAUDE.md.
- No performance claims about the workflow itself; only the process discipline is asserted.

## Definition of Done
- [ ] Six skills exist — verify: `ls .claude/skills/*/SKILL.md` lists gentic, gentic-scout, gentic-interview, gentic-masterprompt, gentic-execute, gentic-iterate.
- [ ] Frontmatter valid — verify: script checks each `name:` equals its directory name and each `description:` is ≤1024 chars and starts with "Use when".
- [ ] Descriptions contain triggers only, no workflow summaries — verify: inspection of each description against the writing-skills rule.
- [ ] Cross-references resolve — verify: every `gentic-*` skill name mentioned in any SKILL.md, CLAUDE.md, or README exists as a directory.
- [ ] Constants consistent everywhere — verify: `grep` shows budget "13", rungs/sizes "1/2/3/5/8", and run-dir pattern `docs/gentic/` agree across all files.
- [ ] CLAUDE.md stays lean — verify: `wc -l CLAUDE.md` ≤ 60 lines.
- [ ] Fresh-agent walkthrough passes — verify: a subagent reading only the six skills narrates a correct full run for a novel ambiguous task (artifacts, gates, question choice, away-user handling, twice-failed-rung handling) without inventing missing pieces.
- [ ] Adversarial review passes — verify: a subagent hunting contradictions, undefined terms, and responsibility overlaps across the six skills + CLAUDE.md reports no blocking finding; majors fixed and logged.
- [ ] README install/use steps accurate — verify: paths and commands in README match the repository layout.

## Risks & early signals
- Description triggering too broad (gentic fires on trivial tasks) or too narrow — signal: routing rule ambiguity in adversarial review; mitigation: consequence-based triviality test in CLAUDE.md.
- Consistency drift between seven markdown files — signal: grep disagreement; mitigation: constants DoD item.
- Over-ceremony for small tasks — signal: walkthrough agent applies gentic where routing says skip; mitigation: "diff size does not decide" rule plus explicit skip lane.

## Iteration budget
13 points (see gentic-iterate ladder).
