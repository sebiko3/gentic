# Decisions: project-scoped-conventions

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Artifact location in an unadopted project | **In-repo `docs/gentic/<date>-<slug>/`, everywhere.** | Outside the repo at `~/.claude/gentic-runs/<repo>/`, in-repo only on opt-in | User's explicit choice, overriding the scouted recommendation. The artifacts are documentation of real work and travel with the code they describe. Consequence accepted: an unadopted project still gets a committed `docs/gentic/` directory. | user |
| Branch and commit naming in an unadopted project | **Follow the project's own convention** — dominant prefix detected from existing branches, plain imperative commit subjects with no `gentic(...)` wrapper. | Create no branch at all and leave git to the user; keep `gentic/` everywhere | The workflow should be invisible in someone else's repository. Keeping per-task checkpoint commits preserves resumability, which the no-branch option would cost. | user |
| Existing `~/code/docEyes` leak | **Leave it alone.** | Rename the branch; rename and relocate artifacts | The branch carries real delivered work. Rewriting another project's branches during an unrelated task is not a call to make unprompted. | user |
| What marks a project as adopted | **A marker in the project's `CLAUDE.md`** — the `gentic/<slug>` branch rule in a Conventions section. | Presence of `docs/gentic/`; a dedicated dotfile | `CLAUDE.md` is the file the install instructions already tell users to edit. `docs/gentic/` is ruled out by decision 1, which puts it in unadopted projects too. | default — unconfirmed |
| Fallback when a project has no prefixed branches | **No prefix — bare `<slug>`.** | Default to `feat/` | Inventing a convention for a project that has none is the exact behaviour being removed. | default — unconfirmed |
| Mechanism | **A deterministic helper, `.claude/hooks/lib/project_conventions.py`, with a CLI**, referenced by the skills and `/ship` instead of a hardcoded string. | Prose rules in ROUTING.md and the skills | A rule the model must remember gets forgotten under context pressure; a script that prints the branch name does not. Matches the hooks layer's existing deterministic-first style and makes the behaviour unit-testable. | default — unconfirmed |


## Settled during the Masterprompt critique

| Decision | Chosen | Why | Source |
|----------|--------|-----|--------|
| Adoption detection precedence | **Runs first and never depends on git.** Marker found -> adopted, even if every git call fails. | Fail-open to a bare slug would silently change *this* repo's behaviour whenever git hiccups - the fail-open rule and the "behaviour unchanged here" constraint contradicted each other until ordered. | default - unconfirmed |
| Census rule | Local heads only; prefix is the text before the first `/`; the default branch is excluded; winner is the highest count; a tie or a winning count below 2 yields a bare slug. | "Dominant" was defined only by one worked example, leaving plurality, ties, denominators and nesting to the executor. | default - unconfirmed |
| Branch-name validation | A computed prefix must match `^[A-Za-z0-9._-]+$` or it is discarded and the slug used bare. | The helper's output is fed to `git checkout -b`; an unvalidated census result is an injection surface. | default - unconfirmed |
| Subprocess exemption | The helper may call `git` via `subprocess`. The no-subprocess rule in `lib/common.py:1-9` governs hot-path hooks; this CLI is not on a hot path and no hook invokes it. | The spec cited that docstring as house style while requiring git reads - a direct contradiction. | default - unconfirmed |
