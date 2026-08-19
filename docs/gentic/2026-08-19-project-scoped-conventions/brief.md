# Brief: project-scoped-conventions

## Mission (as understood)

gentic imposes its own branch and commit conventions on every repository it runs in. A project
with its own `feat/` · `fix/` convention gets a `gentic/<slug>` branch and `gentic(<slug>):`
commit subjects anyway. Make the conventions project-scoped: keep them in repositories that
have adopted gentic, follow the local convention everywhere else.

## Facts

- The prefix is hardcoded in four places, all installed machine-wide:
  `skills/gentic/ROUTING.md:38`, `skills/gentic-execute/SKILL.md:19`,
  `skills/gentic/SKILL.md:16`, `commands/ship.md:43`.
- `ROUTING.md:1-4` states the cause outright: "The gentic repo carries these rules in its
  project `CLAUDE.md`. That file does not exist in other projects, so the rules live here
  instead and **apply everywhere**." Project-specific conventions were promoted to machine-wide
  rules; `install.sh` (this month's work) propagates them further.
- **Observed blast radius is 1 of 45 repositories**, not all: `~/code/docEyes` carries
  `gentic/doceyes-notebook-memory`, a committed `docs/gentic/2026-08-19-doceyes-notebook-memory/`,
  and five `gentic(doceyes-notebook-memory): …` commit subjects. Every other repo under
  `~/code` is clean. The design defect is real regardless; the urgency is lower than "all
  projects".
- The user's repositories do have their own conventions: `feat/`, `fix/`, `integration/`,
  `no-ticket/`, plus unprefixed names (`android-port`, `websockets`, `itsocks`).
- docEyes' own branches skew `feat/` (3 of 6 prefixed branches), so a dominant-prefix rule
  would have produced `feat/notebook-memory` there.
- docEyes has no `CLAUDE.md`; this repo's `CLAUDE.md` carries a `## Conventions` section naming
  the `gentic/<slug>` branch rule. That asymmetry is a usable adoption marker.
- The hooks layer establishes the house style for this kind of rule: deterministic Python in
  `.claude/hooks/lib/`, standard library only, unit-tested (`user_prompt_submit.py:4-6`).

## Patterns to follow

- Deterministic over prose. A rule the model must remember gets forgotten; a script that prints
  the right branch name does not. Same reasoning as `user_prompt_submit.py`'s regex classifier.
- Fail open and stay quiet (`lib/common.py:1-9`) — a detection helper must never break a run.
- Narrow rules, silent otherwise (`pre_tool_use.py:13-14`).

## Constraints discovered

- Python 3 standard library only; no new dependencies.
- `install.sh` ships only tracked files under `.claude/`, so anything new must be committed
  before it reaches `~/.claude`.
- Must not alter the behaviour of the gentic repo itself, which is adopted and keeps `gentic/`.
- Must not touch other repositories.

## Open decisions (ranked by leverage)

1. **Artifact location in an unadopted project** — options: outside the repo
   (`~/.claude/gentic-runs/`) vs in-repo `docs/gentic/`. Recommended default was *outside*;
   **the user chose in-repo**, so artifacts remain committed everywhere. Settled.
2. **Naming in an unadopted project** — options: follow the project's convention / create no
   branch at all / keep `gentic/`. Recommended and chosen: **follow the project's convention**.
3. **What marks a project as adopted** — options: a marker string in the project's `CLAUDE.md`;
   presence of `docs/gentic/`; an explicit dotfile. Recommended default: **a marker in
   `CLAUDE.md`**, because it is the file the routing rules already tell users to edit on
   install, and because `docs/gentic/` will now exist in unadopted projects too (decision 1),
   which rules it out as a signal.
4. **Fallback when a project has no prefixed branches** — options: no prefix (bare slug) vs a
   generic `feat/`. Recommended default: **no prefix**, since inventing a convention is the
   behaviour being removed.
5. **Existing docEyes leak** — options: leave / rename branch / rename and relocate.
   **User chose leave it alone.** Settled.


## Corrections (2026-08-19, during the Masterprompt gate)

- **`~/code/docEyes` has no `gentic/` branch.** The brief's Facts say it "carries
  `gentic/doceyes-notebook-memory`". Re-verified: that repository has exactly one branch,
  `main`; `git show-ref` finds the ref in no repository under `~/code`. The first scan printed
  it, and the same queries re-run minutes later did not. The discrepancy is unexplained and is
  recorded as unexplained rather than given an invented cause.
- **The docEyes branch census (`feat/`x3, `fix/`x2, `integration/`x1) is therefore
  unreproducible** and must not be encoded in a test as that project's census. It survives only
  as a synthetic fixture shape.
- **What remains verified in docEyes**: `docs/gentic/2026-08-19-doceyes-notebook-memory/` is
  tracked in `HEAD`, and six commits on `main` carry `gentic(doceyes-notebook-memory): ...`
  subjects. The leak is real; its branch half is no longer evidenced there.
- **The mission is unaffected.** The prefix and commit-subject forms are hardcoded in
  machine-wide files, so any run in any project imposes them. That is structural and does not
  depend on finding a surviving branch.
- **A fifth hardcoded form was found** that the brief missed entirely: `gentic(<slug>)` commit
  subjects at `.claude/skills/gentic-execute/SKILL.md:27`,
  `.claude/skills/gentic-iterate/SKILL.md:42`, `.claude/skills/gentic/ROUTING.md:40`,
  `.claude/skills/gentic/SKILL.md:34`, and `CLAUDE.md:22`.
