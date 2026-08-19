# Universal automation layer

Machine-wide Claude Code automation: intent routing, a verification gate, a destructive-git guard,
and resume notices. Applies in every project.

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
| `SessionStart` | `session_start.py` | Prunes stale state; reports unfinished gentic runs |
| `UserPromptSubmit` | `user_prompt_submit.py` | Classifies intent; injects a task frame + routing directive for non-trivial work |
| `PreToolUse` (file tools + Bash) | `pre_tool_use.py` | Denies destructive git/rm commands, and enforces `.agentignore` |
| `PostToolUse` (Bash\|Edit\|Write) | `post_tool_use.py` | Records verification evidence and touched files |
| `Stop` | `stop.py` | Blocks a "done" claim after a code edit when nothing was verified |

Session state lives in `~/.claude/state/<session_id>.json` and is pruned after 7 days.

## The Stop gate cannot trap you

The gate fires **at most once per user prompt**. It sets `stop_block_fired` before exiting 2, so the
immediately following stop always passes. A false positive costs one extra turn, never a deadlock.

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
`rm -rf ~/.claude/hooks ~/.claude/state`.
