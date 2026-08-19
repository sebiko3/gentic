#!/usr/bin/env python3
"""SessionStart — prune stale state and surface unfinished spec-driven work.

A gentic run outlives the session that started it. Without this, resuming means the user
has to remember the run exists. Silent when there is nothing outstanding.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import common  # noqa: E402

PHASES = ("Scout", "Interview", "Masterprompt", "Execute", "Iterate")


def current_phase(text):
    """First unchecked phase name, or None when the run is finished."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            for phase in PHASES:
                if phase.lower() in stripped.lower():
                    return phase
            return stripped[5:].strip() or None
    return None


def unfinished(root):
    found = []
    for progress in sorted(Path(root).glob("docs/gentic/*/progress.md")):
        try:
            text = progress.read_text()
        except Exception:
            continue
        phase = current_phase(text)
        if phase:
            found.append((progress.parent.name, phase))
    return found


def main():
    payload = common.read_payload()
    common.prune_state(days=7)

    root = common.git_root(payload.get("cwd"))
    if not root:
        return

    runs = unfinished(root)
    if not runs:
        return

    lines = ["Unfinished gentic run(s) in this repo:"]
    lines += [f"  • {name} — next phase: {phase}" for name, phase in runs[-3:]]
    lines.append("Invoke the `gentic` skill to resume; its progress.md carries the state.")
    common.emit_message("\n".join(lines))


if __name__ == "__main__":
    common.safe_main(main)
