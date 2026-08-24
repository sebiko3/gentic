"""Guards and ledger for context-token efficiency.

The model's context is the budget being protected: a re-read of an unchanged file or a bare
`cat` of a large one spends thousands of tokens to add nothing. Each guard denies at most once
per path per session — the valve property: a false positive (a stale ledger after compaction,
a file the model truly needs again) costs exactly one retry and can never loop.

Pure logic over the state dict; callers own loading, saving, and the deny mechanics. Stdlib
only, `os.stat` at most — file contents are never read here (hot path, 150 ms budget).
"""

import json
import os
import re
import shlex
from pathlib import Path

# Fibonacci-derived constants (house rule): thresholds are balancing values, not magic numbers.
TOKEN_BYTES = 4          # rough bytes-per-token divisor for all estimates
CAT_LIMIT = 89 * 1024    # bare `cat` of a file above this is denied
REPORT_AT = 55_000       # estimated tokens before the one per-session spend report
LINE_BYTES = 55          # assumed bytes per line when a Read carries a `limit`

BARE_CAT = (
    "`cat {path}` would print ~{kb} KB straight into context. Read the range you need instead "
    "— `sed -n 'START,ENDp' {path}`, or the Read tool with offset/limit. "
    "This guard denies each file at most once per session."
)

DUPLICATE_READ = (
    "You already read `{path}` this session and it has not changed since — its content is in "
    "your context. If it is genuinely absent (e.g. after context compaction), re-read with an "
    "explicit offset/limit. This guard denies each file at most once per session."
)


def _resolve(path, cwd):
    """Absolute form of `path`, or None when it cannot name a real location."""
    if not path:
        return None
    try:
        candidate = Path(path)
        if not candidate.is_absolute() and cwd:
            candidate = Path(cwd) / candidate
        return str(candidate)
    except (ValueError, OSError):
        return None


def _identity(resolved):
    """Cheap change-detection identity for a file, or None when it cannot be statted."""
    try:
        info = os.stat(resolved)
        return [info.st_mtime_ns, info.st_size]
    except OSError:
        return None


def check_read(session, tool_input, cwd):
    """Deny reason for a duplicate parameterless Read, or None. Mutates `session`.

    Only parameterless reads enter the ledger and only parameterless reads are checked
    against it: a Read carrying offset/limit is new content by definition — and it is also
    the documented escape hatch, so it must never be denied.
    """
    if tool_input.get("offset") is not None or tool_input.get("limit") is not None:
        return None
    resolved = _resolve(tool_input.get("file_path"), cwd)
    if not resolved:
        return None
    identity = _identity(resolved)
    if identity is None:
        return None

    reads = session.setdefault("reads", {})
    fired = session.setdefault("guard_fired", [])
    if reads.get(resolved) == identity and resolved not in fired:
        fired.append(resolved)
        return DUPLICATE_READ.format(path=tool_input.get("file_path"))
    reads[resolved] = identity
    return None


def check_cat(session, command, cwd):
    """Deny reason for a bare `cat` of one large file, or None. Mutates `session`.

    Deliberately narrow: any pipe, redirect, separator, substitution, flag-only form, multi-file
    form, small file, or unstatable path passes. The only shape denied is the unbounded funnel —
    one file, printed whole, larger than CAT_LIMIT — and it shares the read guard's
    once-per-path valve.
    """
    if any(ch in command for ch in "|;&<>`$"):
        return None
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv or argv[0] != "cat":
        return None
    files = [a for a in argv[1:] if not a.startswith("-")]
    if len(files) != 1:
        return None
    resolved = _resolve(files[0], cwd)
    if not resolved:
        return None
    identity = _identity(resolved)
    if identity is None or identity[1] <= CAT_LIMIT:
        return None

    fired = session.setdefault("guard_fired", [])
    if resolved in fired:
        return None
    fired.append(resolved)
    return BARE_CAT.format(path=files[0], kb=identity[1] // 1024)


# Commands whose re-run with an unchanged tree returns what the model already has.
READONLY = re.compile(r"^\s*(grep|rg|find|ls|cat|head|tail|wc|git\s+(log|diff|status))\b")


def read_estimate(tool_input, cwd):
    """Estimated context tokens a Read will cost. 0 when nothing can be statted."""
    resolved = _resolve(tool_input.get("file_path"), cwd)
    if not resolved:
        return 0
    identity = _identity(resolved)
    if identity is None:
        return 0
    size = identity[1]
    limit = tool_input.get("limit")
    if isinstance(limit, int) and limit > 0:
        size = min(size, limit * LINE_BYTES)
    return size // TOKEN_BYTES


def note_read(session, tokens):
    session["spend_est"] = session.get("spend_est", 0) + tokens
    session["reads_n"] = session.get("reads_n", 0) + 1


def note_saved(session, tokens):
    """A deny kept this many estimated tokens out of context."""
    session["spend_saved"] = session.get("spend_saved", 0) + tokens


def note_edit(session):
    """Any edit-class tool call: re-running a read-only command is legitimate again."""
    session["edit_seq"] = session.get("edit_seq", 0) + 1


def record_bash(session, command, tool_output):
    """Accumulate a Bash result's estimated cost; count identical read-only re-runs."""
    try:
        raw = tool_output if isinstance(tool_output, str) else json.dumps(tool_output, default=str)
    except (TypeError, ValueError):
        raw = ""
    session["spend_est"] = session.get("spend_est", 0) + len(raw) // TOKEN_BYTES
    session["bash_n"] = session.get("bash_n", 0) + 1

    trimmed = command.strip()
    if not READONLY.match(trimmed):
        return
    seen = session.setdefault("bash_seen", {})
    seq = session.get("edit_seq", 0)
    if seen.get(trimmed) == seq:
        session["bash_repeats"] = session.get("bash_repeats", 0) + 1
    else:
        seen[trimmed] = seq
