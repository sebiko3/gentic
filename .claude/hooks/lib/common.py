"""Shared helpers for the machine-wide Claude Code hooks.

Two rules govern everything here:

1. A hook must never break a session. Anything unexpected exits 0 with the problem
   reported as ``systemMessage``; only ``block()`` deliberately exits 2.
2. These run on hot paths (every prompt, every tool call). Standard library only,
   no subprocesses, no network.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("CLAUDE_HOOK_STATE_DIR") or Path.home() / ".claude" / "state")

_UNSAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


def _fresh_turn(turn, prompt_id=None, session=None):
    """A clean per-turn ledger.

    ``session`` is deliberately carried across turns: facts like "a review ran" and "the nudge
    was already shown" describe the session, not the turn, and would be erased every prompt if
    they lived alongside the ledger.
    """
    return {
        "turn": turn,
        "prompt_id": prompt_id,
        "evidence": [],
        "touched": [],
        "code_changed": False,
        "session": dict(session or {}),
    }


def begin_turn(payload):
    """Open a new user turn, discarding the previous turn's ledger.

    Called only by the ``UserPromptSubmit`` hook, which fires exactly once per user prompt.
    Live sessions do not populate ``prompt_id`` (verified against Claude Code 2.1.193), so
    this — not the payload — is what makes the verification gate re-arm each turn.
    """
    session_id = payload.get("session_id")
    previous = load_state(session_id)
    state = _fresh_turn(
        int(previous.get("turn") or 0) + 1,
        payload.get("prompt_id"),
        previous.get("session"),
    )
    save_state(session_id, state)
    return state


def load_turn_state(payload):
    """State for the turn in progress.

    Boundaries come from :func:`begin_turn`. When a build does supply ``prompt_id``, a change
    in it is honoured too, so this stays correct if that field starts being populated.
    """
    state = load_state(payload.get("session_id"))
    prompt_id = payload.get("prompt_id")
    if prompt_id and state.get("prompt_id") and str(state["prompt_id"]) != str(prompt_id):
        return _fresh_turn(int(state.get("turn") or 0) + 1, prompt_id, state.get("session"))
    if prompt_id:
        state.setdefault("prompt_id", prompt_id)
    state.setdefault("turn", 0)
    state.setdefault("evidence", [])
    state.setdefault("touched", [])
    state.setdefault("code_changed", False)
    state.setdefault("session", {})
    return state


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


def block(reason):
    """Deliberately block the pending action. The only path that exits non-zero."""
    sys.stderr.write(reason)
    sys.stderr.flush()
    sys.exit(2)


def safe_main(fn):
    """Run a hook body, guaranteeing exit 0 unless the body called ``block()``."""
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


def _state_file(session_id):
    safe = _UNSAFE_ID.sub("_", str(session_id or "unknown"))[:128] or "unknown"
    return STATE_DIR / f"{safe}.json"


def load_state(session_id):
    """Return this session's state, or ``{}`` if absent or unreadable."""
    try:
        return json.loads(_state_file(session_id).read_text())
    except Exception:
        return {}


def save_state(session_id, state):
    """Persist session state atomically. Failures are swallowed by design."""
    path = _state_file(session_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state))
        tmp.replace(path)
    except Exception:
        pass


def prune_state(days=7):
    """Delete session state untouched for ``days``."""
    cutoff = time.time() - days * 86400
    try:
        for path in STATE_DIR.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except Exception:
                continue
    except Exception:
        pass


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
