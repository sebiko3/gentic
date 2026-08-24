# Decisions: token-efficiency-hooks

One question asked (the enforcement-strength call, where the user's confirmed advisory-first
philosophy and this request pulled in opposite directions); the rest defaulted under the standing
delegation of 2026-08-11 and flagged.

| Decision | Chosen | Alternatives considered | Why | Source |
|----------|--------|------------------------|-----|--------|
| Duplicate-read guard | Deny with valve: repeat `Read` of a file unchanged (mtime+size) since its last read this session is denied once per path per session; any retry passes; deny text explains the post-compaction escape | Measure-only (reaches only the user, saves nothing); also denying repeated Bash | Only a deny reaches the model on PreToolUse; the valve caps a false positive at one ~60-token round-trip, mirroring the verification gate's at-most-once property | user |
| Bare-cat guard | Deny a Bash command that only prints one file > 89 KB into context (bare `cat`/`head`/`tail`, no pipe, no redirect, single file); same once-per-path ledger and valve | Leave Bash output alone | The Read tool self-caps at 2000 lines; bare cat is the remaining unbounded funnel. Drawn narrow: any pipe, redirect, or multi-file form passes | default — unconfirmed |
| Spend report | Accumulate estimated context spend (Read estimates at PreToolUse — PostToolUse cannot see Read; Bash result sizes at PostToolUse) and emit one advisory line at Stop when the session crosses ~55k estimated tokens, joined into the existing combined nudge | Report every stop; no reporting | Same once-per-session threshold-gated shape as the existing nudges; per-stop reporting is the documented noise failure | default — unconfirmed |
| Repeated identical Bash | Count read-only exact repeats with no intervening edit; surface the count inside the spend report; never deny | Deny like duplicate reads | Re-running tests/greps is often legitimate and the ledger cannot see why; measurement belongs in the report, enforcement would misfire | user (chose against harder variant) |
| Thresholds | Fibonacci-derived constants in the hook: 89 KB cat guard, 55k-token report threshold; estimate = bytes/4 | Round numbers; env-var plumbing | House rule prefers Fibonacci values; no configuration surface until someone needs one | default — unconfirmed |
| State placement | Read-ledger and spend counters live in `state["session"]` so they survive turns; turn ledger untouched | New state file | `session` is the documented home for session-scoped facts (lib/common.py:29-40); a second file would double the atomic-write surface | default — unconfirmed |
