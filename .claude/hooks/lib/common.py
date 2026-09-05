"""Shared helpers for the machine-wide Claude Code hooks.

Two rules govern everything here:

1. A hook must never break a session. Anything unexpected exits 0 with the problem
   reported as ``systemMessage``; no hook ever blocks a turn.
2. These run on hot paths (every prompt, every tool call). Standard library only,
   no subprocesses, no network.

Session state lives in the brain (``lib/brain.py``), not here.
"""

import json
import sys
from pathlib import Path


def read_payload():
    """Return the hook payload as a dict; ``{}`` for empty, malformed or non-object input."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def emit(obj):
    """Write one JSON object to stdout. Nothing is written for a falsy object."""
    if obj:
        sys.stdout.write(json.dumps(obj))


def emit_context(text, event=None):
    """Inject context for the model. Silent when there is nothing to say."""
    if not text or not text.strip():
        return
    hook_specific = {"additionalContext": text}
    if event:
        hook_specific["hookEventName"] = event
    emit({"hookSpecificOutput": hook_specific})


def emit_message(text):
    """Show a message to the user only (not to the model)."""
    if text and text.strip():
        emit({"systemMessage": text})


def safe_main(fn):
    """Run a hook body, guaranteeing exit 0."""
    try:
        fn()
    except SystemExit:
        raise
    except Exception as exc:  # never let a hook bug break the session
        try:
            emit_message(f"hook error ({fn.__module__}): {exc}")
        except Exception:
            pass
    sys.exit(0)


def git_root(cwd):
    """Nearest ancestor containing ``.git``, or ``None``. Walks the tree; never shells out."""
    if not cwd:
        return None
    try:
        current = Path(cwd).resolve()
    except Exception:
        return None
    if not current.is_dir():
        return None
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return None
