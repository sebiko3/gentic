# Brief: agentignore-guard

## Mission (as understood)

A `PreToolUse` hook that consults a `.agentignore` file before any file-touching tool runs, and
refuses the call when that file says the path is off-limits. The file distinguishes *read* from
*write*, so a path can be readable-but-immutable as well as wholly invisible. The check happens
before the tool executes — nothing is read or modified and then regretted.

## Facts

- The `PreToolUse` deny path is already built and proven in this setup: `pre_tool_use.py` returns
  `hookSpecificOutput.permissionDecision: "deny"` with a reason, and the harness asserts it
  (`~/.claude/hooks/tests/test_guard_and_session.py::Guard`). Extending that file is a smaller,
  safer change than adding a second `PreToolUse` hook.
- Tool names confirmed present in the 2.1.193 binary: `Read` (27), `Write` (20), `Edit` (16),
  `Grep` (11), `Glob` (10), `NotebookEdit` (6). **`MultiEdit` appears once** — it is likely not a
  live tool in this build, so guarding it is harmless but not load-bearing.
- `PreToolUse` matchers match on tool name and accept regex or `A|B` lists, so one hook entry can
  cover every file-touching tool.
- **The user already uses this kind of file**: `~/code/shapeKingz/.cursorignore` and
  `~/code/circles/.cursorignore` are identical, and use gitignore syntax — `#` comments, bare
  directory names with a trailing `/`, e.g. `node_modules/`, `supabase/.temp/`, `build/`.
- No `.agentignore`, `.aiignore`, or `.aiexclude` exists anywhere under `~/code` — the format is
  ours to define, but the user's existing `.cursorignore` style is the obvious precedent to match.
- Python's standard library has no gitignore matcher. `fnmatch` handles `*` and `?` but not `**`
  or the anchoring rules; correct behaviour must be written by hand. No pip installs are allowed
  by the existing constraints.
- Existing hook constraints still bind: standard library only, exit 0 on internal error, and this
  runs on a hot path — `PreToolUse` fires before every file tool call.

## Patterns to follow

- Deny with a *reason string* the model can act on, as the destructive-git guard already does
  (`pre_tool_use.py`, `deny()`), rather than a bare refusal.
- Narrow rules, silent otherwise: a guard that fires on ordinary work gets trained away.
- Contract tests that run the hook as a real subprocess and assert on `permissionDecision`
  (`test_guard_and_session.py::guard`).
- The user's `.cursorignore` files show the expected authoring style: terse, commented, directory-
  oriented.

## Constraints discovered

- **A read-guard is porous by construction.** `Read` can be denied, but `cat`, `sed`, `head`,
  `grep` and friends run under `Bash`, and `Grep`/`Glob` return file contents and paths directly.
  Guarding only `Read` yields a rule that looks enforced but is not. Any honest design must either
  cover `Bash` and `Grep` too, or state plainly that it is an accident-preventer, not a
  security boundary.
- Cascading lookup costs file I/O on a hot path; results must be cached per hook invocation, and
  the walk must stop at the repo root or filesystem root.
- Patterns arriving from a file in the working tree are untrusted input — a malicious or careless
  `.agentignore` must not be able to crash the hook (which would fail open) or hang it.
- Relative vs absolute paths: tools may pass either, so paths must be normalised against `cwd`
  before matching.
- `.agentignore` cannot protect against a path outside any repo, and must no-op there.

## Open decisions (ranked by leverage)

1. **Scope of enforcement** — options: (A) file tools only (`Read`/`Edit`/`Write`/`NotebookEdit`);
   (B) file tools **plus** `Grep`/`Glob` result filtering and a `Bash` command-path scan;
   (C) file tools plus a `Bash` scan, leaving `Grep`/`Glob` alone. **Recommended default: C** —
   it closes the obvious `cat .env` hole that makes (A) illusory, without the complexity and false
   positives of parsing `Grep` output. The residual gap gets stated honestly in the docs.

2. **Read/write syntax** — options: (A) section headers (`[no-read]` / `[read-only]`) with bare
   patterns defaulting to deny-both; (B) per-line prefixes (`no-write: vendor/`); (C) two separate
   files. **Recommended default: A** — bare patterns keep `.cursorignore` muscle memory and the
   strictest-by-default reading, while sections add the read/write axis the request needs.
   Per-line prefixes make the common case noisier for no gain.

3. **Deny vs escalate** — options: (A) hard `deny`; (B) `escalate` to a permission prompt;
   (C) deny writes, escalate reads. **Recommended default: A** — the user's phrasing is "not
   allowed", and a prompt on every hit turns the guard into a nuisance that gets click-approved.
   `.agentignore` is editable by the user, which is the escape hatch.

4. **Discovery** — options: (A) nearest `.agentignore` walking up from the target file to the repo
   root, all of them combined (gitignore-like); (B) repo root only; (C) cwd only.
   **Recommended default: A** — it matches how the user already thinks about ignore files and lets
   a subfolder protect itself, which is exactly the "files in a specific folder" framing.

5. **Negation** — options: (A) support `!pattern` re-allows, gitignore-style; (B) no negation.
   **Recommended default: A** — without it, protecting `secrets/` while allowing
   `secrets/README.md` is impossible, and the syntax is already familiar.

6. **Bypass posture for the user's own edits** — options: (A) the guard applies to Claude only,
   always; (B) an env var (`AGENTIGNORE_OFF=1`) disables it for a session.
   **Recommended default: A** — a documented off-switch that the model can read is not a guard.
   The user edits `.agentignore` itself to change what is allowed.
