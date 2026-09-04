---
description: Verify, review, commit, push and open a PR for the current work — and, under the project's grants, watch CI, preview and merge — the one place git automation runs
---

# /ship

This command is the **only** place in this setup where git and GitHub work happens without being
asked step by step. Nothing here fires on its own; the user typing `/ship` is the authorisation
— or a gentic run in a project that grants `push` and `open-pr` under `## gentic authorizations`
*and* is listed in `~/.claude/gentic/trusted-projects`, which the run checks with
`project_conventions.py authorized` before following these steps at the end of Iterate.
Everything below then runs unattended until it either opens a PR — or, with `--through`, goes as
far as the project's grants allow — or stops with a clear reason.

Arguments (optional): `$ARGUMENTS` may carry a PR title or a short description of the change.

**Stop and report rather than improvising** if any precondition fails. Never work around a failed
gate — a failing test is the answer, not an obstacle.

## 1. Preconditions

Run these first and abort with the specific reason if any fails:

```bash
git rev-parse --is-inside-work-tree
git remote -v
gh auth status
git status --porcelain
```

- Not a git repo → stop: "not a git repository".
- No remote → stop, and offer to create one rather than doing it silently.
- `gh` not authenticated → stop and tell the user to run `gh auth login` themselves. Never handle
  credentials.
- Nothing to commit and no unpushed commits → stop: "nothing to ship".

## 2. Branch guard

```bash
git rev-parse --abbrev-ref HEAD
```

If the branch is `main`, `master`, `develop`, or the repo's default branch, **do not commit to it**.
Create and switch to a work branch first, named from the change:

```bash
BRANCH=$(python3 "$HOME/.claude/hooks/lib/project_conventions.py" branch "<slug>")
git checkout -b "$BRANCH"
```

The helper names the branch the way *this project* does: `gentic/<slug>` only in an adopted
repo, the project's own dominant prefix otherwise, and a bare slug when it has none. If it errors or is absent, fall back to the bare slug — never impose `gentic/`.

If a gentic run directory exists for this work, reuse its slug so branch and artifacts match.

## 3. Verify before committing

Detect the project's own verification command — read `package.json` scripts, `Makefile`,
`pyproject.toml`, `Cargo.toml`, `go.mod`, or the project's CLAUDE.md. Do **not** invent one.

Run the narrowest relevant check first (tests for the touched area), then typecheck/lint/build if
the change affects them.

- **Any failure stops the ship.** Report the actual output. Do not commit, do not push.
- If the project genuinely has no verification layer, say so explicitly in the final report rather
  than silently skipping this step.

## 4. Review

Run `/review` over the diff. It dispatches `code-reviewer`, and `dod-auditor` as well when a
gentic run directory backs this work.

Two optional extras, neither required — the first-party agents are the review:
`silent-failure-hunter` and `pr-test-analyzer`, if the `pr-review-toolkit` plugin is installed;
and `superpowers:requesting-code-review`, if that plugin is available.

Act on findings before continuing. Findings you deliberately decline must appear in the PR body —
never drop them silently.

## 5. Commit

Stage **only** files belonging to this change — never `git add -A` over unrelated edits:

```bash
git add <specific paths>
git commit -m "<imperative subject>"
```

- Short imperative subject, no AI attribution, no trailer.
- If the work spans several logical changes, make several commits rather than one mixed one.
- Re-check `git status` afterwards and report anything intentionally left uncommitted.

## 6. Push and open the PR

```bash
git push -u origin <branch>
```

Build the PR body from evidence, not adjectives:

- **What changed** and why, in a few sentences.
- **Verification**: the exact commands run and their real results.
- **Review**: what the review agents flagged, and what was done about each.
- If a gentic run backs this work, take the checklist from its `masterprompt.md` Definition of Done
  and mark each item with the evidence that proves it.
- **Unconfirmed defaults**: list every decision marked `default — unconfirmed` in `decisions.md`, so
  the reviewer sees what was assumed rather than chosen.

```bash
gh pr create --title "<title>" --body "<body>"
```

Report the PR URL.

## 8. Through CI, preview and merge (`--through`)

`/ship --through ci` continues after the PR: `python3 "$HOME/.claude/hooks/lib/release.py" wait --pr <n>`
watches the checks (21 s polls, 1597 s ceiling). Green → report. Red →
`release.py failed-logs --pr <n>`, then one rung-1 fix: a failing test first, the smallest change
that makes it pass, one commit, push, `wait` again. At most two such fixes per ship; a third
failure stops with the logs in the report.

`--through preview` (needs `authorized deploy-preview` → `yes`): deploy with the project's own
mechanism — the Railway MCP `deploy` when a Railway service is linked, otherwise the preview
command the project's README documents — and hand the URL to `ui-tester` with the flow the PR
changes; its report block goes in the PR body.

`--through merge` (needs `authorized merge-on-green` → `yes`): `release.py merge --pr <n>`, which
refuses on its own when the grant, the mergeability, or the green is missing.

Without a grant, each of these steps writes what it would have done into the report and stops
there.

## 7. Never

- Never force-push. Never `git reset --hard`. Never rewrite published history.
  (The `PreToolUse` guard denies these anyway.)
- Never merge the PR yourself — `release.py merge` under an explicit `merge-on-green` grant is the
  only path (§8); otherwise opening it is where this command ends.
- Never edit a Definition of Done item to make it pass.
- Never claim a check passed without its output in front of you.
