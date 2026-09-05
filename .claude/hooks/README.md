# Universal automation layer

Machine-wide Claude Code automation: intent routing, a destructive-git guard, `.agentignore`, a
concurrency valve, a RED/GREEN ledger in the brain, and resume notices. Applies in every project.
No hook ever ends a turn.

Built by the gentic run `2026-08-17-universal-claude-setup`
(spec: `~/code/gentic/docs/gentic/2026-08-17-universal-claude-setup/masterprompt.md`).

## Design rules

1. **A hook may never break a session.** Every script exits 0 on its own errors, surfacing the
   problem as `systemMessage`. Only deliberate policy decisions use exit 2.
2. **No LLM calls on hot paths.** `UserPromptSubmit`, `PostToolUse` and `Stop` fire constantly;
   they are pure Python, standard library only.
3. **Silence is the default branch.** Hooks emit nothing unless a rule actually fires.
4. **Never interpolate payload fields into a shell string.** JSON is parsed in Python.

## Components

| Event | Script | Does |
|-------|--------|------|
| `SessionStart` | `session_start.py` | Prunes the brain's old events and idle sessions; reports unfinished gentic runs |
| `UserPromptSubmit` | `user_prompt_submit.py` | Classifies intent; injects a routing directive for non-trivial work; resets the valve's counter |
| `PreToolUse` (file tools, Bash, subagents) | `pre_tool_use.py` | Denies destructive git/rm commands, enforces `.agentignore`, caps concurrent subagents |
| `PostToolUse` (Bash, subagents) | `post_tool_use.py` | Records each verification run as `red` or `verification` in the brain; frees a valve slot |

The hooks keep no state of their own: the concurrency valve's counter lives in the brain's
`sessions` table, keyed by session id, and `brain.py prune` (run silently at every session
start) deletes idle sessions after 8 days and events after 89.

## `.agentignore`

Drop a `.agentignore` in a repo root — or in any subfolder that wants to protect itself — to declare
what Claude may read and what it may modify. The check runs *before* the tool does, so a protected
file is never opened and then regretted. Copy `agentignore.example` to start.

```
secrets/              # bare pattern: no read, no write
*.pem

[read-only]           # readable, never modified
vendor/
migrations/

[no-read]             # writable, never read
tmp/scratch/

!secrets/README.md    # re-allow a path an earlier rule caught
```

- Gitignore-style patterns: `dir/`, `*.ext`, `**`, `?`, leading `/` to anchor.
- A pattern with no `/` matches that basename at any depth.
- Files cascade from the repo root down to the target; **the nearest file wins**, and the last
  matching rule within the combined set decides.
- Covers `Read`, `Edit`, `Write`, `NotebookEdit`, and `Bash` commands that name a protected path.
  `Edit` needs both read and write permission, because an edit reads the file first.

### This is an accident-preventer, not a security boundary

Do not use it to contain secrets from a determined or malfunctioning agent. Specifically:

- **`Grep` and `Glob` are not guarded** — a search can still surface matching lines and paths.
- The `Bash` scan is **heuristic**: it inspects tokens that look like paths. A path built at runtime,
  assembled from variables, or reached through a symlink will not be caught.
- It **fails open**. An unreadable or malformed `.agentignore` warns and allows the call, because a
  typo must not block every file operation in a repo.
- Anything already in the model's context stays there; this gates access, not memory.

For real secrecy, keep the material out of the working tree.

## Testing

Run the harness — it needs no Claude Code restart:

```bash
bash ~/.claude/hooks/tests/run.sh
```

Exit 0 with no `FAIL` lines means every hook is behaving.

## Rollback

Two backups exist, one per change to `settings.json`. Restore the most recent one to undo the
last change only:

```bash
cp ~/.claude/settings.json.bak-2026-08-19 ~/.claude/settings.json
```

That reverts the 2026-08-19 changes — the widened `PostToolUse` matcher
(`…|Task|Agent`, which lets `post_tool_use.py` see review subagents) and the removal of an
`enabledPlugins` entry for the optional `pr-review-toolkit@claude-plugins-official`, which was
enabled but whose recorded `installPath` did not exist, so its agents never resolved.

To remove the whole hooks layer instead, restore the backup from before it existed:

```bash
cp ~/.claude/settings.json.bak-2026-08-17 ~/.claude/settings.json
```

That removes the `hooks` key entirely; the scripts become inert. To also remove them:
`rm -rf ~/.claude/hooks`.

## Verification vocabulary

The ledger recognises a verification command by name: pytest, unittest, tox, nox, jest, vitest,
mocha, ava, the npm/yarn/pnpm test, lint, typecheck and build scripts, go test/build/vet, cargo
test/build/check/clippy, make test/check/lint/build, tsc, mypy, ruff, flake8, eslint, biome,
pyright, swift test, xcodebuild, gradle test, mvn test/verify, dotnet test, rspec, phpunit —
and the UI test runners and audits: **playwright, cypress, lighthouse, axe**. A green run is a
`verification` event; a red one is the RED of a test-first task, UI contracts included.

## The concurrency valve

`pre_tool_use.py` counts foreground subagent spawns (`Task`/`Agent` tool calls) per session and
denies a spawn while five are in flight, with a reason that says so; `post_tool_use.py` frees a
slot when a subagent returns. Background spawns (`run_in_background: true`) return immediately
and are not counted, on spawn or on return. The counter is one row in the brain's `sessions`
table, changed by a single atomic `UPDATE` under SQLite's own lock, so five spawns issued in one
message are all seen; it resets to 0 at every user prompt so a leaked count cannot wedge a
session. A brain that cannot be opened fails **open**: every spawn is allowed and nothing is
printed — an uncapped fan-out is preferred to a blocked session. The PreToolUse matcher must
include `Task|Agent` for the valve to run — the installer's printed settings block does.

## The brain

`post_tool_use.py` appends events to gentic's brain, `~/.claude/gentic/brain.sqlite`
(`GENTIC_BRAIN` overrides the path; the harness always sets it to a throwaway file). The kinds
it writes, and nothing else:

| kind | written by | detail |
|------|-----------|--------|
| `red` | `post_tool_use` | a recognised verification command that exited non-zero |
| `verification` | `post_tool_use` | one that exited 0 (or with no exit code available) |

Each event carries `run`, the slug of the project's open gentic run at the time (NULL when
none), so `select kind, detail from events where run = '<slug>'` is a run's whole RED/GREEN
history. `detail` is the first 300 characters of the command, with credential values
(`Authorization:`, `--password`, `token=`, `password=`, `secret=`, `AWS_…=`) replaced by `***`.
Every write is best-effort and **silent on failure**: `lib/brain.py` opens the file with a 34 ms
lock timeout, and a brain that is missing, locked, or under a path that cannot be created costs
the hook nothing — no message, no stderr, no exit code change. `session_start.py` reads the
brain (never creates it) to mention how many lessons and learned preferences exist for the
project, and prunes it quietly when it already exists. The schema is versioned
(`PRAGMA user_version`) and an older brain is upgraded in place on first open. Everything else
in the brain — notes, decisions, lessons, runs, stamps, free SQL — is written by the phase
skills through the same CLI; see `skills/gentic-brain/SKILL.md`.
