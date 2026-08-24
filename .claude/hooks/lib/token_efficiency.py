"""Guards and ledger for context-token efficiency.

The model's context is the budget being protected: a re-read of an unchanged file or a bare
`cat` of a large one spends thousands of tokens to add nothing. Each guard denies at most once
per path per session — the valve property: a false positive (a stale ledger after compaction,
a file the model truly needs again) costs exactly one retry and can never loop.

Pure logic over the state dict; callers own loading, saving, and the deny mechanics. Stdlib
only, `os.stat` at most — file contents are never read here (hot path, 150 ms budget).
"""

import os
from pathlib import Path

# Fibonacci-derived constants (house rule): thresholds are balancing values, not magic numbers.
TOKEN_BYTES = 4          # rough bytes-per-token divisor for all estimates
CAT_LIMIT = 89 * 1024    # bare `cat` of a file above this is denied
REPORT_AT = 55_000       # estimated tokens before the one per-session spend report
LINE_BYTES = 55          # assumed bytes per line when a Read carries a `limit`

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
