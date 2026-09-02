---
name: gentic-interview
description: Use when a gentic run has a brief.md with unresolved open decisions, or when requirements could each be read two ways and building on the wrong reading would be expensive.
---

# Gentic Interview — Ask Only What Changes the Build

## Overview

The Interview converts the brief's open decisions into settled ones, using as few of the user's answers as possible. Write the result to `decisions.md` in the run directory.

**Core principle: a question earns its place only if the answer changes what gets built AND the default is genuinely uncertain.**

## Choosing questions

Before scoring, ask the brain (`gentic-brain`) `preference <topic>` for each open decision: a
learned answer is adopted with Source `learned` and never asked. After the user answers, record
each choice with `decide <topic> <chosen> --source user`, so the next run can learn it.

Score each open decision from the brief: leverage (how much the answer changes the work) × uncertainty (how likely the recommended default is wrong). Ask the top scorers; adopt defaults for the rest silently, recording them with Source `default — unconfirmed`. (Blockers discovered mid-Execute are owned by gentic-execute's blocker rule, not this skill.)

**Automatic top rank, regardless of score: decisions touching other people's data, security, money, or anything irreversible.** These are precisely the calls an agent will otherwise make unilaterally "on its own authority" — they belong to the user.

Question types worth asking, in rough priority:
1. **Scope boundary** — what is explicitly out?
2. **Success shape** — what does "done" look like to the user, concretely?
3. **Constraints** — stack, compatibility, style, hard limits the repo didn't reveal.
4. **Trade-off priority** — speed vs completeness vs polish, pick the ranking.
5. **Risk appetite** — may adjacent code be refactored, or minimal-touch only?

## Asking

- Use the AskUserQuestion tool: up to 4 questions per call, multiple-choice, your recommended option **first** and labeled "(Recommended)".
- One round (= one AskUserQuestion call) is the default. A second round only if the answers opened *new* load-bearing decisions. Hard cap: three rounds.
- Prefer enumerable choices over open-ended; the user can always pick "Other".

## Non-interactive rule

If `AskUserQuestion` is unavailable, the session is autonomous — whatever it looks like. Adopt
the brief's recommended default for every open decision, set Source to `default — unconfirmed`,
write `decisions.md`, and **do not end the turn: return to the orchestrator, which crosses the
gate and invokes `gentic-masterprompt` in the same session. Never end the turn to ask, to flag,
or to wait for an objection**: the flags belong in the final report, which lists every
unconfirmed default prominently. Data, security and money decisions are adopted the same way,
with their flag — the report is where the user reverses them.

## decisions.md template

```markdown
# Decisions: <slug>

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| <topic> | <choice> | <A, B> | <reason> | user \| default — unconfirmed |
```

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Asking what the Scout brief already answers | Re-read the brief; delete the question |
| Polling preferences on settled conventions | Conventions from the repo or user config are facts, not questions |
| Open-ended question with enumerable answers | Offer the enumeration; "Other" covers the rest |
| Blocking an autonomous run on a question | Default + flag `unconfirmed`; surface it in the final report |
| Ten questions to feel thorough | Each question spends user attention; only high leverage × high uncertainty earns it |
