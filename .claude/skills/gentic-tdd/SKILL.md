---
name: gentic-tdd
description: Use when a gentic task is about to change behaviour — before writing any implementation code. Also use when a fix must be proven to fix something, when a task's RED cell is empty, or when it is tempting to write the test after the code "just this once".
---

# Gentic TDD — The Failure Comes First

## Overview

Every task in a gentic run passes through here. The spec already named the test that proves each
Definition of Done item; this skill turns that contract into a test that has actually been watched
to fail, then into code that makes it pass.

**Core principle: a test you never saw fail proves nothing. It may test the wrong thing, test the
mock instead of the code, or pass for a reason you never checked.**

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Wrote the code first? Delete it and start from the test. Not "keep it as reference", not "adapt it
while writing the test" — adapting is testing-after wearing a disguise, and it is how you end up
testing what you built instead of what was required.

The one legal exception is exploration: throw the spike away, then start from the test.

If superpowers:test-driven-development is available, invoke it here — it carries the same law in
more depth. When it is unavailable this skill is complete on its own.

## The cycle

**RED — write one failing test.**
Take the test contract from the masterprompt's DoD item: its file, its name, the behaviour it
asserts. One behaviour per test; if the name needs an "and", split it. Test real code — a mock you
assert against tests the mock.

**Verify RED — run it and read the failure.** Mandatory, never skipped.
- It must *fail*, not *error*. An import error or a typo is not a RED; fix it and re-run.
- The failure must be the one the contract predicted. A different message means the test, the
  contract, or your understanding is wrong — find out which before writing any code.
- It must fail because the behaviour is missing. A test that passes immediately is testing
  something that already exists; rewrite it until it fails.

**GREEN — the smallest code that passes.**
No extra options, no anticipated requirements, no neighbouring cleanup. If the test does not
demand it, it is not in scope. Then run the test *and* the suite around it: a green test beside a
broken neighbour is not green.

**REFACTOR — only once green.**
Remove duplication, improve names. Behaviour must not change, so the tests must not change.

## Evidence

The observed RED is the task's evidence, and it belongs in the run artifact, not in your memory:
paste the actual failure — assertion message or first failing line, trimmed — into the task's
`RED` cell in `progress.md`. Then the GREEN command's real output goes in the checkpoint commit or
the task note.

**A task whose `RED` cell is empty is not done, whatever the code looks like.** That cell is the
only place a resumed session can learn the test was ever seen to fail.

## Tasks with no executable behaviour

Documentation, prompts, and specs still change behaviour — of a reader or an agent — so they still
get a test. The test is a contract test: an assertion about the file, in the project's existing
suite, that fails before the change and passes after (this repo's `.claude/hooks/tests/test_structure.py`
is the pattern).

Only a task that changes **nothing observable** may write `n/a` in the `Test` cell, and it must say
why in the same cell. "Hard to test" is not a reason; it is a design signal.

## UI tasks

A `ui` contract is RED when the e2e spec fails against the running app with the failure the
contract predicted (a missing locator, a wrong text), and GREEN when it passes; paste the RED
like any other. When the item is flagged `not reproducible in CI`, the RED and the GREEN are two
`ui-tester` reports with screenshots in `docs/gentic/<run>/evidence/`, and the task note says so.

## When the test is hard to write

| Symptom | What it means |
|---------|---------------|
| You cannot name the test | The behaviour is not decided yet — return to the spec, not to the code |
| The test needs enormous setup | The unit is too coupled; simplify the interface |
| You must mock everything | The dependencies are wired in, not injected |
| The test asserts on internals | You are testing implementation; assert on behaviour instead |

## Red flags — stop and restart from the test

| Thought | Reality |
|---------|---------|
| "I'll add the test right after" | A test written after passes immediately and proves nothing |
| "Too simple to break" | Simple code breaks; the test costs less than the incident |
| "I already checked it by hand" | Manual checks leave no record and never run again |
| "Deleting this working code is wasteful" | Sunk cost. Code you cannot trust is the debt |
| "The test failed, close enough" | A failure for the wrong reason is a false RED |
| "Just this once, it's a tiny fix" | Tiny fixes are the ones that ship undetected regressions |
| "It's only docs" | Docs change agent behaviour; use a contract test |
| "The RED cell is bookkeeping" | It is the evidence; without it the claim is memory, not proof |

## Bug fixes

A bug means a missing test. Write the test that reproduces it, watch it fail *with the bug's own
symptom*, then fix. The test is what stops it coming back.
If superpowers:systematic-debugging is available, find the root cause with it first — then still
come back here and start from the test.
