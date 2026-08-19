---
description: Review the current change with the first-party review agents, and report findings without touching the code
---

# /review

Review work in progress. This command reports; it does not commit, push, or fix. Use `/ship`
when the change is ready to become a PR — `/ship` runs this same review as one of its steps.

Arguments (optional): `$ARGUMENTS` may name a scope — files, a commit range, a branch, or a PR.
With no argument the scope is worked out below.

## 1. Establish scope

In order, take the first that is non-empty:

```bash
git diff --stat
git diff --staged --stat
git diff --stat "$(git merge-base HEAD "$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||' || echo main)")"...HEAD
```

State the scope in one line before reviewing. If every one is empty, stop with "nothing to
review" — never widen to the whole repository because the diff was empty.

## 2. Dispatch the reviewers

Invoke `code-reviewer` with: the scope you established, and the path to the project's
`CLAUDE.md` or `AGENTS.md` if one exists. It reports only findings at confidence 80 or above.

When a gentic run directory applies to this work — `docs/gentic/<date>-<slug>/` with a
`masterprompt.md` — also invoke `dod-auditor` with that path, so the review covers whether the
change actually satisfies what was specified, not only whether the code is sound. Skip it when
no run directory exists; this command must work in a repo that has never used gentic.

Both may run at once; they do not share state.

If a change is large or touches several unrelated areas, dispatch one `code-reviewer` per area
rather than one over everything — a reviewer given too much reports less, not more.

The `pr-review-toolkit` plugin's specialists are an optional extra when that plugin is
installed; nothing here depends on them.

## 3. Report

Present findings worst-first, grouped by file, each with its confidence and the one-line fix
the reviewer proposed. Then state plainly, in one sentence, whether you consider the change
safe to merge — and if you disagree with a finding, say so with your reasoning rather than
passing it along unexamined or silently dropping it.

End with what you did **not** review and why (out of scope, unchanged, generated).

## 4. Do not

- Do not apply fixes as part of this command. Report, then let the user decide. If they ask for
  the fixes, that is a new instruction and the review findings are your brief.
- Do not commit, stage, push, or open a PR. `/ship` owns all of that.
- Do not report findings below the confidence threshold to look thorough. The count of
  discarded candidates is enough.
