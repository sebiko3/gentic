# Masterprompt: project-scoped-conventions

## Mission

Stop gentic imposing its own naming on repositories that never adopted it. A run in an
unadopted project uses that project's branch convention and plain commit subjects; a run in an
adopted project keeps `gentic/<slug>` branches and `gentic(<slug>): …` commit subjects exactly
as today. The decision comes from a deterministic helper the skills call, not from prose an
agent must remember under context pressure.

## The contract (single source of truth)

Everything else in this file defers to this section.

**Location:** `.claude/hooks/lib/project_conventions.py`, installed to
`~/.claude/hooks/lib/project_conventions.py`.

**Signature:**

```
python3 <helper> branch <slug> [--root PATH]
python3 <helper> commit <slug> <message> [--root PATH]
```

`--root` defaults to `$PWD`. The project root is the nearest ancestor of `--root` containing a
`.git` entry (a directory or, in a linked worktree, a file). If there is none, the directory
itself is the root and the project is unadopted.

**Adopted** iff the file `CLAUDE.md` at the repository root contains the literal substring
`gentic/<slug>`. No other file is consulted — not `.claude/`-scoped files, not
`CLAUDE.local.md`, not any parent directory.

**Precedence:** adoption detection runs **first** and never calls git. A project that is
adopted stays adopted even if every git call fails.

**Output, exhaustively:**

| case | `branch <slug>` prints | `commit <slug> <msg>` prints |
|---|---|---|
| adopted | `gentic/<slug>` | `gentic(<slug>): <msg>` |
| unadopted, census yields prefix `P` | `P/<slug>` | `<msg>` |
| unadopted, no usable prefix | `<slug>` | `<msg>` |
| adopted, any internal failure | `gentic/<slug>` | `gentic(<slug>): <msg>` |
| unadopted, any internal failure | `<slug>` | `<msg>` |

Exit code is always 0. Nothing is ever written to stderr on the fallback paths.

**Census rule** (unadopted only): run `git for-each-ref --format=%(refname:short) refs/heads`.
For each branch, the prefix is the text before the **first** `/`; branches with no `/` are
counted as unprefixed and excluded from the tally. Exclude the repository's default branch
(HEAD's target). The winner is the prefix with the highest count. **A tie, or a winning count
below 2, yields no prefix.** Remote-tracking refs are never censused.

**Validation:** a computed prefix must match `^[A-Za-z0-9._-]+$`; otherwise it is discarded and
the bare slug used. The helper's output is fed to `git checkout -b`, so an unvalidated census
result would be an injection surface.

**Subprocess exemption:** the helper may call `git` via `subprocess`. The "no subprocesses"
rule in `lib/common.py:1-9` governs hot-path hooks; this CLI is not on a hot path and no hook
invokes it.

**Invocation line the skills and `/ship` must contain, verbatim:**

```bash
python3 "$HOME/.claude/hooks/lib/project_conventions.py" branch "<slug>"
```

If that command errors or is missing, the agent uses the bare `<slug>` and continues. A missing
helper never stops a run.

## Context

- Branch-prefix sites: `.claude/skills/gentic/ROUTING.md:38`,
  `.claude/skills/gentic-execute/SKILL.md:19`, `.claude/skills/gentic/SKILL.md:16`,
  `.claude/commands/ship.md:43`.
- Commit-subject sites, which the first draft of this spec missed entirely:
  `.claude/skills/gentic-execute/SKILL.md:27`, `.claude/skills/gentic-iterate/SKILL.md:42`,
  `.claude/skills/gentic/ROUTING.md:40`, `.claude/skills/gentic/SKILL.md:34`.
- `CLAUDE.md:21-22` carries both forms and is the **adoption marker itself**.
- `ROUTING.md:1-4` names the root cause: project rules promoted to machine-wide rules.
- **`run.sh:88` fails the build on any quoted string literal containing `.claude` inside
  `hooks/*.py` or `hooks/lib/*.py` unless it is `Path.home()`-anchored or starts `~/`.** The
  helper must therefore never embed a `.claude` path literal; it needs only `"CLAUDE.md"`.
- `run.sh:14` iterates a **hardcoded** suite list. A new test file that is not added there
  never runs in the harness.
- Baseline before this run: **174 tests across 9 suites**, `run.sh` exit 0.
- `install.sh` ships only git-tracked files under `.claude/`.
- Verified state of `~/code/docEyes`: `docs/gentic/…` tracked in HEAD and six
  `gentic(doceyes-notebook-memory): …` commits on `main`. It has **no** `gentic/` branch, and
  its branch census is unreproducible — see `brief.md` Corrections. No test may claim to encode
  that project's census.

## Decisions

1. Artifacts stay in-repo at `docs/gentic/` in every project. *(user — overrides the scouted
   recommendation)*
2. Naming follows the project's own convention when unadopted. *(user)*
3. `~/code/docEyes` is left untouched. *(user)*
4. Adoption marker, census rule, validation, and subprocess exemption are as fixed in **The
   contract** above. *(default — unconfirmed)*

## Constraints

- Python 3 standard library only (`subprocess` included, per the exemption above).
- The helper never raises and never exits non-zero.
- No quoted `.claude` path literal anywhere in the helper (`run.sh:88`).
- Behaviour for **this** repository must be byte-identical to today's — `gentic/<slug>` and
  `gentic(<slug>): <msg>` — **including when git fails**.
- No repository outside this checkout is read or written, except ephemeral fixtures the tests
  create under `tempfile.mkdtemp()` and delete.
- This run does install to `~/.claude` (DoD 12), changing behaviour for every project on this
  machine. That is the point of the change and is sequenced explicitly, not inferred.
- Test fixtures must not depend on ambient git config: create refs with
  `git init -b main` then `git -c user.email=t@t -c user.name=t commit --allow-empty`.

## Non-goals

- **Not changing where artifacts live.** `docs/gentic/` stays, per decision 1.
- **Not touching `~/code/docEyes`** or any repository other than this one.
- **Not renaming existing branches** anywhere, including here.
- **`CLAUDE.md:21-22` must keep the literal `gentic/<slug>` and `gentic(<slug>)` unqualified** —
  it is the adoption marker. Do not edit this repo's `## Conventions` section for consistency.
- **No override surface.** No `--prefix` flag, no environment variable, no config file. "The
  user can override" means they say so in conversation and the agent obeys.
- **The helper is read-only.** No `adopt` subcommand; it never writes a marker or edits any
  `CLAUDE.md`.
- **No hook enforcement.** Nothing in `.claude/hooks/*.py` invokes the helper in this run; no
  `PreToolUse` guard on branch names.
- **No caching or state files.** The census is recomputed per invocation.
- **No commit-message inference** beyond dropping the `gentic(...)` wrapper — no Conventional
  Commits parsing, no scope inference.
- **No remote-ref censusing.**

## Definition of Done

Checks run from the repository root unless stated.

- [ ] **1. The helper is unit-tested and wired into the harness.**
      Verify: `test_project_conventions` appears in the suite list at `.claude/hooks/tests/run.sh:14`,
      and `python3 .claude/hooks/tests/test_project_conventions.py` passes.
- [ ] **2. This repository keeps today's naming, exactly.**
      Verify: `python3 .claude/hooks/lib/project_conventions.py branch demo-slug` prints exactly
      `gentic/demo-slug`; `… commit demo-slug "did a thing"` prints exactly
      `gentic(demo-slug): did a thing`.
- [ ] **3. Adoption survives a git failure.**
      Verify: a test runs the helper against this repo with `PATH` emptied so `git` cannot be
      found; output is still exactly `gentic/demo-slug`. This is the contradiction that the
      fail-open rule would otherwise hide.
- [ ] **4. A prefix-dominant unadopted project gets that prefix.**
      Verify: a fixture repo (no `CLAUDE.md`) with `feat/a`, `feat/b`, `feat/c`, `fix/d`,
      `integration/e` yields exactly `feat/x` for `branch x`, and exactly `did a thing` for
      `commit x "did a thing"`.
- [ ] **5. No usable prefix yields a bare slug.**
      Verify: fixtures for (a) branches `main`, `websockets`; (b) a tie, `feat/a` and `fix/b`;
      (c) a single `feat/a` (count below 2); (d) a repo with no commits. Each yields exactly `x`.
- [ ] **6. The helper fails open, always exit 0.**
      Verify: tests for a non-git directory, a `--root` that does not exist, and an
      unreadable/failing git — each prints `x` for `branch` and the message unchanged for
      `commit`, exit code 0, no traceback.
- [ ] **7. A hostile census result cannot reach `git checkout -b`.**
      Verify: a fixture with branch names such as `a;rm -rf x/b` and `../evil/c` yields exactly
      `x` — the prefix is rejected by validation, not passed through.
- [ ] **8. Neither hardcoded form survives as an unconditional rule.**
      Verify: `test_structure.py` gains a case asserting that every occurrence of the literal
      `gentic/<slug>` **or** `gentic(<slug>)` in `.claude/skills/` and `.claude/commands/` sits
      on a line that also marks it conditional (containing `adopted`, `project_conventions`, or
      `this repo`). `CLAUDE.md` is excluded, being the marker. The case passes.
- [ ] **9. `/ship` actually calls the helper.**
      Verify: `.claude/commands/ship.md` no longer contains the literal
      `git checkout -b gentic/<slug>`, and §2 contains the verbatim invocation line from the
      contract.
- [ ] **10. The skills actually call the helper.**
      Verify: `.claude/skills/gentic-execute/SKILL.md` and `.claude/skills/gentic/ROUTING.md`
      each contain the verbatim invocation line, and each states the adopted/unadopted rule for
      commit subjects.
- [ ] **11. The harness is green and genuinely larger.**
      Verify: `bash .claude/hooks/tests/run.sh` → exit 0, no `FAIL` line, and the summed
      `Ran N tests` total is **≥ 190** (174 baseline + at least 16 new).
- [ ] **12. Installed, in sync, and the machine still works.**
      Verify, in this order: commit, `bash install.sh`, `bash install.sh --check` exits 0,
      `test -f ~/.claude/hooks/lib/project_conventions.py`, then `bash .claude/hooks/tests/run.sh`
      again with its Configuration section **passing** (not skipping).
- [ ] **13. The adoption marker is documented.**
      Verify: `grep -n "gentic/<slug>" README.md` matches inside a section that explains how to
      mark a project as adopted.

## Risks & early signals

- **The marker is a literal substring match.** A user who words their `CLAUDE.md` differently is
  treated as unadopted and gets plain naming. That is the safe direction — it never imposes — so
  it is accepted, and DoD 13 makes it discoverable.
- **The census is a heuristic.** A repo whose branches are mostly stale `fix/` work gets `fix/`
  for a feature. The helper only *prints* a name; it never creates the branch, so a wrong guess
  is visible before it is acted on.
- **Installing changes every project on this machine.** DoD 12 sequences it and re-runs the
  harness afterwards; DoD 3 pins the one case where a regression would be silent.
- **Git edge cases on day one:** linked worktrees (`.git` is a file), zero-commit repos,
  detached HEAD. DoD 5(d) and DoD 6 cover the ones that change output.

## Iteration budget

13 (initial allocation — the live balance is `progress.md`'s)
