---
name: gentic-iterate
description: Use when a gentic run's tasks are all checked and done-ness must be proven, when the same failure recurs after a fix, or when it is unclear whether to patch, rework, or re-open the spec. Also use when an iteration budget or escalation question arises.
---

# Gentic Iterate — Verify, Then Escalate Deliberately

## Overview

Iterate proves the run against its Definition of Done and, when items fail, chooses how far back to go — deliberately, on a ladder, instead of patching in circles. All spending is logged in `progress.md`.

**Core principle: evidence before "done"; escalation before repetition.**

## Verification

1. Run **every** DoD check literally — the exact command or inspection the masterprompt names. No sampling, no "the others will pass too". Dispatch `dod-auditor` with the masterprompt path to do this adversarially: it runs each named check and returns PROVEN / FAILED / UNVERIFIABLE with the real output, and it treats UNVERIFIABLE as a non-pass rather than rounding it up. Where that agent is unavailable, run the checks yourself under the same rule.
2. Record each result in the iteration log with a one-line evidence summary (command + outcome). Passing checks log Rung `—`, Points 0.
3. Editing a DoD item to make it pass is forbidden. DoD changes happen only via rung 5.
4. All items pass → if superpowers:verification-before-completion is available, invoke it as the final gate (otherwise re-run every DoD check once more, fresh, quoting outputs); then write the final report (below).

## On failure: diagnose, then pick a rung

Direct rung-5 entry: when gentic-execute's drift rule sends the run here mid-Execute, skip Verification and start at rung 5.

Root cause first — if superpowers:systematic-debugging is available, you MUST invoke it before choosing a rung; otherwise the inline rule holds: reproduce, isolate, and name the root cause before any fix. Then take the **lowest rung sufficient for the root cause**:

| Rung | Cost | Action |
|------|------|--------|
| 1 | 1 pt | Micro-fix the specific defect |
| 2 | 2 pts | Rework the failing component's implementation |
| 3 | 3 pts | Redesign the approach for that area, within the current spec |
| 5 | 5 pts | Re-open `masterprompt.md` — a Decision or DoD item was wrong (invoke gentic-masterprompt to amend, then gentic-execute for affected tasks) |
| 8 | 8 pts | Re-open the Interview — the framing itself was wrong (invoke gentic-interview, then gentic-masterprompt and gentic-execute as the new answers require) |

Costs are fibonacci because each rung discards more prior work; the default budget of 13 affords many small fixes, a few reworks, or one spec re-opening — never endless fiddling.

## Hard rules

- **The initial verification failure is not an attempt; fixes are.** Each fix attempt starts a rung and deducts that rung's points anew from the budget line in `progress.md`, logged: item, rung, points, result.
- **Same DoD item fails two fix attempts at the same rung → the next rung is mandatory.** No third attempt at a level — and "next" is a floor: the diagnosis may justify jumping higher, never staying. "One more quick try" is the loop this skill exists to break.
- A mandated rung costing more than the remaining budget = budget exhausted: stop and hand off.
- Commit rung work like tasks, with the subject from `project_conventions.py commit` — `gentic(<slug>): rung-<n> <DoD item>` in an adopted repo, `rung-<n> <DoD item>` in any other project.
- Rungs 5 and 8 are user check-ins. If the session is autonomous, do not silently rewrite the spec — stop and hand off instead. (A rung you stop at instead of starting deducts nothing and gets the same handoff as budget exhaustion.)
- Budget exhausted → stop. Write an honest handoff in `progress.md` (what passes, what fails, root-cause state, recommended next rung) and report to the user. A stopped run with a clean handoff beats a thrashed one.

## Final report (all DoD green)

Append the report to `progress.md` (Notes / handoff) and tick phase 5, then report to the user: mission, each DoD item with its evidence, unconfirmed defaults awaiting confirmation, points spent, and anything deliberately not done (non-goals). If superpowers:finishing-a-development-branch is available, invoke it to close out the branch.

## Red flags — stop and re-read this skill

- "One more quick try at this rung" after two failures — climb.
- Rewording a DoD item so the current behavior passes — that is rung 5 wearing a disguise.
- "It obviously works, running the checks is ceremony" — the check IS the work; run it.
- Spending below the failure ("it's just a typo") twice in a row on the same item — the diagnosis is wrong; climb anyway.
