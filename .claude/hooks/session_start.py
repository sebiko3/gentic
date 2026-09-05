#!/usr/bin/env python3
"""SessionStart — surface unfinished spec-driven work, and keep the brain bounded.

A gentic run outlives the session that started it. Without this, resuming means the user
has to remember the run exists. The brain's memory of this project is surfaced the same way,
and its events and idle sessions past their retention are pruned — silently, and only when the
brain already exists: starting a session never creates it.
Silent when there is nothing outstanding and nothing remembered.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import brain, common  # noqa: E402

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
    brain.prune_quietly()

    root = common.git_root(payload.get("cwd"))
    if not root:
        return

    lines = []
    runs = unfinished(root)
    if runs:
        lines.append("Unfinished gentic run(s) in this repo:")
        lines += [f"  • {name} — next phase: {phase}" for name, phase in runs[-3:]]
        lines.append("Invoke the `gentic` skill to resume; its progress.md carries the state.")

    known = brain.summary(Path(root).name)
    if known and any(known):
        lessons, preferences = known
        lines.append(
            f"brain: {lessons} lesson(s) for {Path(root).name}, {preferences} learned preference(s) — "
            'python3 ~/.claude/hooks/lib/brain.py recall <words>'
        )

    if lines:
        common.emit_message("\n".join(lines))


if __name__ == "__main__":
    common.safe_main(main)
