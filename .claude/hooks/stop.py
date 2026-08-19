#!/usr/bin/env python3
"""Stop — refuse a success claim that nothing backs up.

This is the only routine hard block in the setup. It fires when all of the following hold:

  1. code (not prose) was edited during this turn, and
  2. the final message claims the work is done/fixed/passing, and
  3. no verification command succeeded during this turn, and
  4. the gate has not already fired for this user prompt.

Condition 4 is the safety property: the gate blocks at most once per prompt, so a false
positive costs one extra turn and can never trap the user in a loop.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import common  # noqa: E402

DONE_CLAIM = re.compile(
    r"\b("
    r"all set|done|complete|completed"
    r"|fixed|works now|working now|now works"
    r"|passing|passes|all green"
    r"|verified|confirmed working"
    r"|ready to (merge|ship|go)"
    r")\b",
    re.I,
)

# Hedged or negated statements are not success claims — "not done yet" must not block.
NOT_A_CLAIM = re.compile(
    r"\b("
    r"not (yet )?(done|complete|completed|fixed|passing|verified)"
    r"|isn'?t (done|complete|fixed|passing)"
    r"|still (need|needs|needed|failing|broken|to do)"
    r"|before (i|we) (can|could)"
    r"|want me to|shall i|should i|let me know"
    r"|haven'?t (run|tested|verified)"
    r")\b",
    re.I,
)

REASON = """Verification gate: this turn edited {n} file(s) — {files} — and the response claims the
work is done, but no verification command succeeded during this turn.

Run the project's actual check (its test, typecheck, lint or build command) and report the
real output, or restate the result without claiming it is done/fixed/passing.

This gate blocks at most once per prompt; if it is wrong here, simply continue."""


def main():
    payload = common.read_payload()
    message = str(payload.get("last_assistant_message") or "")
    if not message:
        return

    state = common.load_turn_state(payload)

    if not state.get("code_changed"):
        return
    if state.get("evidence"):
        return
    if not DONE_CLAIM.search(message) or NOT_A_CLAIM.search(message):
        return
    if state.get("stop_block_fired"):
        return

    # Record before blocking so the next stop passes unconditionally.
    state["stop_block_fired"] = True
    common.save_state(payload.get("session_id"), state)

    touched = state.get("touched", [])
    shown = ", ".join(Path(p).name for p in touched[:4]) or "unknown"
    common.block(REASON.format(n=len(touched), files=shown))


if __name__ == "__main__":
    common.safe_main(main)
