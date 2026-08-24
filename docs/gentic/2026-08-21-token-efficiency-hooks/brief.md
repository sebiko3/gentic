# Brief: token-efficiency-hooks

## Mission (as understood)
Build hooks that reduce context-token waste in Claude Code sessions. The waste is the model's,
not the user's: re-reading files already in context, dumping large files into context via bare
`cat`, and repeating identical read-only commands. The hooks should prevent the expensive cases
where a mechanism exists to reach the model, measure what they cannot prevent, and stay inside
this setup's established discipline: stdlib only, sub-150ms, never break a session, artifacts of
waste reported once rather than nagged about.

## Facts
- Hook events registered on this machine (`~/.claude/settings.json`): SessionStart fires only on
  `startup|resume` (not `clear|compact`), PreToolUse matches
  `Bash|Read|Edit|Write|MultiEdit|NotebookEdit|NotebookRead`, PostToolUse matches
  `Bash|Edit|Write|MultiEdit|NotebookEdit|Task|Agent` — **PostToolUse does not see Read**.
  Any accounting of Read traffic must therefore happen in `pre_tool_use.py`, which does see it.
- `install.sh` never writes `settings.json` (install.sh:36-38: "settings.json and
  settings.local.json are never installed"). Changing matchers is machine state, out of scope for
  a repo deliverable — the design must work within the matchers already registered.
- On PreToolUse there are exactly two channels: allow silently, or deny (exit 2) with a reason
  the **model** sees. A non-blocking `systemMessage` reaches only the user
  (lib/common.py:113-116) — an "advisory" PreToolUse hook cannot steer the model at all.
- Stop can emit advisory messages to the user; the repo already runs two such nudges, combined
  into a single message, once per session each (stop.py `advisory_nudges`).
- Per-session state survives turns via `state["session"]` (lib/common.py:29-40: "facts like 'a
  review ran' … describe the session, not the turn"); the turn ledger is discarded each prompt
  by `begin_turn`. A read-ledger keyed by path belongs in the session dict.
- Session id changes on resume (new forked session) → a fresh ledger; but **compaction keeps the
  session id and empties the model's context** while SessionStart does not fire for `compact` on
  this machine. Any "you already read this" guard can therefore be *stale*: the ledger says the
  content is in context, the context no longer holds it. The guard needs a pressure valve.
- The Read tool itself caps unparameterised reads at 2000 lines, so the oversized-read hole is
  not Read — it is Bash: a bare `cat`/`head` of a large file prints the whole thing into context.
- The verification-gate precedent for bounded blocking: `stop.py` records `stop_block_fired`
  before blocking so "a false positive costs one extra turn and can never trap the user in a
  loop" (stop.py:14-16). The same at-most-once property is the template for any new deny.
- PreToolUse already denies — `.agentignore` violations and destructive commands
  (pre_tool_use.py:1-15). The single-hard-block rule (stop.py:4-7) governs *routine adversarial
  gates on the Stop path*, not PreToolUse guards; guards are the established place where a deny
  is legitimate.
- Latency: `run.sh` holds PreToolUse to a 150 ms median with `.agentignore` present (currently
  ~25 ms). `os.stat` per Read is cheap; reading file *contents* in a hook is not an option.
- Hooks cannot see real token counts. Estimation: `bytes / 4`. For Bash results, PostToolUse's
  `tool_output` payload can be sized via its serialised length regardless of shape
  (post_tool_use.py `exit_code_of` shows the shape varies).
- House preference (~/.claude/CLAUDE.md): Fibonacci-derived values for thresholds and budgets.

## Patterns to follow
- Guard structure and tone of `pre_tool_use.py`: narrow triggers, "everything not covered passes
  through with no decision at all" (pre_tool_use.py:14-15).
- Ledger recording in `post_tool_use.py` (writes state only, never blocks); Stop consumes.
- Advisory messages: combined, once per session, threshold-gated — `advisory_nudges` in stop.py.
- Contract tests: a new unittest suite in `.claude/hooks/tests/`, registered in `run.sh:14`,
  following `test_tdd.py`'s helper shape (run hook as subprocess with `CLAUDE_HOOK_STATE_DIR`).
- Per the new spine: every DoD item gets a test contract naming its expected RED.

## Constraints discovered
- Stdlib only, no subprocesses, no network, exit 0 on hostile input, ≤150 ms medians.
- No `settings.json` changes — the deliverable must work with the matchers listed above.
- Existing suites (`test_gate`, `test_tdd`, `test_review_nudge`, …) must stay green; the state
  schema is shared, so new session keys must not break `_fresh_turn` round-trips.
- Denies must carry the at-most-once (per subject) safety property from the gate precedent.
- This repo's own hooks run *while this repo is being developed* — a guard that misfires on the
  session building it will be noticed immediately (dogfooding is the test bench).

## Open decisions (ranked by leverage)
1. **Duplicate-read guard: deny-with-valve, or don't build it** — options: (A) PreToolUse denies
   a repeat `Read` of a file unchanged since its last read this session (same mtime+size), with
   the valve that a retry passes (at most one deny per path per session) and the deny text tells
   the model the content is already in context, or to re-read with `offset`/`limit` if it is
   genuinely gone (post-compaction); (B) don't build — an advisory can't reach the model, so
   only measurement remains. Recommended default: **A** — it is the single biggest avoidable
   waste (a re-read of a 2000-line file is thousands of tokens; a deny message is ~60), the
   valve caps the false-positive cost at one round-trip, and the stale-ledger case
   (compaction) is exactly what the valve exists for.
2. **Bare-cat guard** — options: (A) deny a Bash command whose sole effect is printing a file
   larger than 89 KB straight into context (bare `cat`/`head`/`tail` on one big file, no pipe,
   no redirect), message suggesting a ranged read; (B) leave Bash output alone. Recommended
   default: **A**, drawn deliberately narrow — any pipe or redirect passes, multiple files pass,
   small files pass; the false-positive surface is near zero and the worst case is again one
   valve retry (at most one deny per path per session, shared ledger with decision 1).
3. **Spend report at Stop** — options: (A) accumulate per-session estimated context spend from
   tool traffic (Read estimates at PreToolUse since PostToolUse is blind to Read; Bash result
   sizes at PostToolUse) and emit one advisory line when the session crosses ~55k estimated
   tokens, joining the existing combined nudge; (B) report every stop; (C) no reporting.
   Recommended default: **A** — same once-per-session, threshold-gated shape as the existing
   nudges; (B) is the noise the repo's own design notes warn about.
4. **Repeated identical Bash commands** — options: (A) count exact repeats of read-only commands
   with no intervening edit and include the count in the spend report; (B) deny them like
   duplicate reads. Recommended default: **A** — re-running greps/tests is often legitimate
   (post-edit, flaky output), the ledger can't always see why, so measurement belongs in the
   report and enforcement would misfire.
5. **Threshold values** — options: Fibonacci-derived (89 KB cat guard, 55k-token report
   threshold, 2000-line Read default already fixed by the tool) vs round numbers. Recommended
   default: Fibonacci-derived, per the house rule; constants in the hook, no env plumbing.
