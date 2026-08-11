# Brief: bootstrap-gentic

## Mission (as understood)
Build a deep agentic workflow for Claude Code — clarifying questions to narrow context, then a masterprompt, then iteration — improving on that shape where justified. Deliver it as project skills plus a fitting CLAUDE.md, in this repository.

## Facts
- Repository is empty except `LICENSE` (MIT) and one initial commit on `main` (`git log`, `ls`).
- User's global config requests: right tool for the job; fibonacci sequence for formulas and balancing where sensible (`~/.claude/CLAUDE.md`).
- The superpowers plugin is installed globally: brainstorming, writing-skills, test-driven-development, systematic-debugging, verification-before-completion, finishing-a-development-branch are all invocable (session skill list).
- Claude Code project skills live at `.claude/skills/<name>/SKILL.md`; frontmatter requires `name` + `description` (≤1024 chars). A description that summarizes the skill's workflow causes agents to follow the description and skip the body — descriptions must state triggers only (superpowers:writing-skills).
- AskUserQuestion supports ≤4 questions per call, multiple choice, with an automatic "Other" (tool schema).
- This session is autonomous — the user is away and cannot answer questions mid-task (session context).

## Baseline probe (RED)
A subagent given an ambiguous task ("CSV export for the users table, should be fast") and asked to narrate its honest defaults reported: zero clarifying questions (would decide PII column exposure unilaterally), no plan written to disk ("the plan exists in my head"), and "fast" accepted by construction, not measurement. It also rationalized skipping process skills because the task "looked small" and the user was away. These are the exact failure modes the workflow must close.

## Patterns to follow
- Superpowers skill format: frontmatter + overview + core principle + tables + rationalization counters (installed superpowers SKILL.md files).
- Phase-chaining via "invoke X with the Skill tool" works across skills (brainstorming → writing-plans does this).

## Constraints discovered
- Markdown only; skills cannot ship executable dependencies and stay portable.
- Descriptions: third person, "Use when…", triggers only, ≤1024 chars.
- Commits belong on a branch, not `main` (harness git rules).

## Open decisions (ranked by leverage)
1. Workflow shape — options: user's literal 3-phase / hardened 5-phase / multi-agent tournament; recommended: 5-phase, because questions need grounding (Scout) and iteration needs a verification anchor (Iterate), while keeping the user's skeleton.
2. Packaging — options: one mega-skill / orchestrator + phase skills / Workflow-tool orchestration; recommended: orchestrator + phase skills, because phases load one at a time (token-efficient), resume cleanly, and need no per-run opt-in.
3. Artifact home — options: `docs/gentic/<date>-<slug>/` committed / hidden `.gentic/` / gitignored; recommended: committed `docs/gentic/`, because specs are documentation and resume depends on them surviving.
4. Fibonacci placement — options: decorative mention / real mechanics; recommended: real mechanics (task sizes, rung costs, budget), because the preference says "formulas and balancing".
5. Interview stance when user is away — options: block on questions / default + flag; recommended: default + flag `unconfirmed`, because blocking kills autonomous runs and silent defaults (the baseline behavior) hide risk.
