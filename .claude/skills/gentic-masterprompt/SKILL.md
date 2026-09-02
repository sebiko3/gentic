---
name: gentic-masterprompt
description: Use when a gentic run has brief.md and decisions.md but no critiqued masterprompt.md yet, or when an iteration escalation (rung 5 or 8) requires amending the spec. Also use when work must be handed to a fresh agent or session with zero shared context.
---

# Gentic Masterprompt — One File That Could Brief a Stranger

## Overview

The masterprompt compiles everything the run knows into a single spec. Write `masterprompt.md` in the run directory, then attack it with the critique pass.

**The bar: an agent with zero conversation context could deliver the work from this file alone. Write for that agent — it is who you become after compaction.**

## masterprompt.md template

```markdown
# Masterprompt: <slug>

## Mission
<one paragraph: outcome, not activity>

## Context
<facts from the brief that the work depends on, with file:line refs>

## Decisions
<from decisions.md: what was chosen and why; mark unconfirmed defaults>

## Constraints
<hard limits: stack, style, compatibility, user preferences>

## Non-goals
<at least one explicit exclusion — what this run will NOT do>

## Definition of Done
- [ ] <observable claim>
      verify: `<exact command>` or <exact inspection step>
      contract: <test file> · <test name> · <behaviour asserted> · expected RED: <the failure to expect>
- [ ] ...

## Risks & early signals
<what could invalidate the plan, and how to notice early>

## Iteration budget
13 (initial allocation — the live balance is progress.md's; amendments never reset it)
```

## Definition of Done craft

- Each item = an observable claim **plus** the exact check that proves it. "Works correctly" is not a claim; "`pytest tests/test_export.py` passes" is.
- **Each item also names its test contract: the test file, the test name, the behaviour asserted, and the expected RED.** This is what makes the spec *drive* the tests rather than merely check them — Execute writes the test the spec named, not the test that is convenient once the code exists. Naming the expected failure is the load-bearing part: it is how the executing agent knows a RED was the *right* RED and not a typo.
- Write contracts, not code. The test's identity belongs in the spec; the test's body is written test-first during Execute.
- A DoD item whose contract restates its verify command has no contract — name the *test*, not the runner.
- For an item with nothing executable behind it (documentation, prompts, specs), the contract is a contract test in the project's existing suite: an assertion about the file that fails before the change. `n/a` is reserved for items that change nothing observable, and must carry its reason.
- **Every vague adjective in the request — "fast", "simple", "robust", "clean" — must become either a measured DoD item (with a number and a command) or an explicit non-goal.** Vague words silently accepted "by construction" are the most common way runs end wrong.
- Behavior touching other people's data, security, or money gets its own DoD item even if the user never mentioned it.
- Record every unconfirmed default in the brain (`gentic-brain`) with
  `decide <topic> <chosen> --source default` — defaults never teach a preference, but they stay visible.
- If the user never supplied the number behind an adjective (unasked, or an autonomous run), choose a defensible one and flag it `unconfirmed` like any default.

## Critique pass (mandatory)

Re-read the finished file as an adversary:

1. **Two-readings scan** — can any requirement be read two ways? Pick one, state it.
2. **Contradiction scan** — do Decisions, Constraints, and DoD agree with each other?
3. **Unverifiable-DoD scan** — any item without a named check gets one or gets cut.
4. **Test-contract scan** — any item whose contract is missing, restates the verify command, or predicts no specific RED is not yet specified; fix it here, where it costs nothing.
5. **Missing non-goal scan** — what will a diligent agent over-build? Exclude it.
6. **Decomposition check** — if the Mission is really several missions, stop and split into separate runs.

Fix findings inline. Spec amendments after a rung 5 or 8 escalation repeat this pass.

Then dispatch `masterprompt-critic` with **only this file** — not the brief, not the decisions, not the conversation. Withholding the context is the point: it reproduces the position of the agent who will execute this after a compaction. Its question is "what would you get wrong executing this?", and a blocking finding from it is cheaper to fix now than at rung 5. Where that agent is unavailable, run the five scans above a second time yourself, reading only this file.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Spec assumes conversation context ("as discussed") | The stranger test fails; inline the substance |
| DoD items that restate the mission | Items must be independently checkable claims |
| No non-goals | Scope creep is the default; exclusion is a decision |
| DoD item with a verify command but no test contract | The spec is checking work it never designed; name the test |
| Critique pass skipped because "it reads fine" | It always reads fine to its author; run the five scans |
