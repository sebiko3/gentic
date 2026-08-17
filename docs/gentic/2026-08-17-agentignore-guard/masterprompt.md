# Masterprompt: agentignore-guard

## Mission

A `.agentignore` file anywhere in a project declares which paths Claude may read and which it may
modify, and the `PreToolUse` hook enforces that before the tool runs — so a protected file is never
opened-then-regretted. The declaration is gitignore-shaped, so it can be written from memory, and it
carries a read/write axis so a path can be readable-but-immutable. Enforcement covers the file tools
and a heuristic scan of `Bash` commands, and its real limits are documented rather than oversold.

## Context

- Extends `~/.claude/hooks/pre_tool_use.py`, which already implements the deny path
  (`hookSpecificOutput.permissionDecision: "deny"` + `permissionDecisionReason`) and is proven by
  `~/.claude/hooks/tests/test_guard_and_session.py::Guard`.
- Currently wired as `PreToolUse` matcher `"Bash"` in `~/.claude/settings.json`; the matcher must
  widen to `Bash|Read|Edit|Write|NotebookEdit`.
- The user's existing `.cursorignore` files (`~/code/shapeKingz`, `~/code/circles`) establish the
  authoring style: `#` comments, `dir/` entries, one pattern per line.
- Standard library only; no gitignore matcher exists there, so pattern semantics are hand-written.
- Runs on a hot path — `PreToolUse` fires before every file tool call.

## Decisions

From `decisions.md` — user-confirmed unless marked:

- Scope: `Read`/`Edit`/`Write`/`NotebookEdit` + `Bash` path scan; `Grep`/`Glob` unguarded.
- Format: bare = deny read+write; `[read-only]` = read yes, write no; `[no-read]` = read no,
  write yes; `!pattern` re-allows; last matching rule wins.
- Response: hard deny, naming the rule and the `.agentignore` that produced it.
- *(default)* Discovery cascades from the target's directory to the repo root, inner rules winning.
- *(default)* Fail open on a malformed file, with a `systemMessage` warning.
- *(default)* No off-switch; the user edits `.agentignore`.
- *(default)* Documented as an accident-preventer, not a security boundary.

## Specification

### File format

```
# comment
secrets/              # bare: no read, no write
*.pem

[read-only]           # readable, never modified
vendor/
migrations/

[no-read]             # writable, never read
.env.production

!secrets/README.md    # re-allow both
```

Section headers are case-insensitive and may be `[deny]`, `[read-only]`, `[no-read]`. A file with no
header starts in `[deny]`. Blank lines and `#` comments are ignored. Trailing `#` comments are
**not** stripped from patterns (a `#` inside a pattern is legal in gitignore); only lines whose first
non-space character is `#` are comments.

### Pattern semantics (gitignore subset)

- `dir/` matches that directory and everything beneath it.
- A pattern containing no `/` matches the **basename** at any depth (`*.pem`).
- A pattern containing `/` is anchored to the directory of the `.agentignore` that declared it.
- `*` matches within a path segment; `**` matches across segments; `?` matches one character.
- A leading `/` anchors to the declaring directory.
- Last matching rule across the combined rule list wins.

### Resolution

`permissions_for(path)` → `{"read": bool, "write": bool}`. Collect `.agentignore` files from the
repo root (or filesystem root) down to the target's directory, so nearer files append later and
therefore win. Cache parsed files per process.

### Tool → operation mapping

| Tool | Requires |
|------|----------|
| `Read`, `NotebookRead` | read |
| `Write`, `NotebookEdit` | write |
| `Edit`, `MultiEdit` | read **and** write (an edit reads first) |
| `Bash` | see below |

For `Bash`: extract candidate path tokens from the command. Deny if any token resolves to a path
with `read: false`. Additionally, if the command matches a mutating shape
(`rm|mv|cp|sed -i|tee|truncate|chmod|chown|>|>>`), deny if any token has `write: false`.

### Denial message

Names the tool, the path, the rule that matched, and the `.agentignore` that declared it, and states
that the user can edit that file to change access.

## Non-goals

- **Not a security boundary.** `Grep`/`Glob` are unguarded, the `Bash` scan is heuristic, and paths
  built dynamically at runtime will not be caught. The README must say this plainly.
- No filtering or rewriting of `Grep`/`Glob` results.
- No `.gitignore` interoperability, no `.cursorignore` reading, no negated-directory re-inclusion
  edge cases beyond simple `!pattern`.
- No off-switch, no per-session override, no global `~/.agentignore`.
- No changes to the verification gate, classifier, or `/ship`.

## Definition of Done

- [ ] Parser handles all four rule kinds and last-match-wins — verify: `python3 tests/test_agentignore.py Parser` passes.
- [ ] Pattern matching covers `dir/`, basename globs, anchored paths, `**`, and `!` — verify: `python3 tests/test_agentignore.py Patterns` passes.
- [ ] Rules cascade, with the nearest `.agentignore` winning — verify: `python3 tests/test_agentignore.py Cascade` passes.
- [ ] `Read` on a deny-read path is denied — verify: `tests/test_agentignore.py Enforcement.test_read_denied` asserts `permissionDecision == "deny"`.
- [ ] `Edit`/`Write` on a deny-write path are denied — verify: `Enforcement.test_write_denied` passes.
- [ ] A `[read-only]` path allows `Read` and denies `Edit` — verify: `Enforcement.test_read_only_path` passes.
- [ ] `Bash` reading a protected path (`cat secrets/key.pem`) is denied — verify: `Enforcement.test_bash_read_denied` passes.
- [ ] `Bash` mutating a `[read-only]` path is denied while reading it is allowed — verify: `Enforcement.test_bash_write_vs_read` passes.
- [ ] Ordinary commands and unprotected paths are never denied — verify: `Enforcement.test_no_false_positives` covers ≥ 8 cases and passes.
- [ ] With no `.agentignore` present, nothing is ever denied — verify: `Enforcement.test_inert_without_agentignore` passes.
- [ ] A malformed `.agentignore` fails open and does not raise — verify: `Enforcement.test_malformed_fails_open` asserts exit 0 and no deny.
- [ ] The pre-existing destructive-git guard still works — verify: `python3 tests/test_guard_and_session.py` passes unchanged.
- [ ] `PreToolUse` stays under 150 ms with a `.agentignore` present — verify: harness prints a measured median and asserts `< 150`.
- [ ] `settings.json` matcher covers all guarded tools — verify: `jq -r '.hooks.PreToolUse[0].matcher' ~/.claude/settings.json` prints a value containing `Read`, `Edit`, `Write` and `Bash`.
- [ ] The whole harness is green — verify: `bash ~/.claude/hooks/tests/run.sh` exits 0 with no `FAIL`.
- [ ] The security limitation is documented — verify: `grep -ci 'not a security boundary' ~/.claude/hooks/README.md` ≥ 1.
- [ ] A commented example `.agentignore` ships — verify: `~/.claude/hooks/agentignore.example` exists and its own parse produces the expected verdicts (`Docs.test_example_file_parses`).

## Risks & early signals

- **False positives on `Bash` are the biggest risk** — a token that merely looks like a protected
  path would block unrelated commands. Early signal: `test_no_false_positives` failing. Mitigation:
  tokens are only treated as paths when they resolve under the repo, and the case list is broad.
- **Hot-path cost**: cascading file reads per tool call. Early signal: the latency assertion.
  Mitigation: per-process cache; the walk stops at the repo root.
- **Over-trust**: the user may believe this secures secrets. Mitigation: the non-goal is documented
  in the README and stated in the final report.

## Iteration budget

13 (initial allocation — the live balance is `progress.md`'s)
