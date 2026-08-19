#!/usr/bin/env python3
"""PostToolUse — maintain the evidence ledger backing the verification gate.

Records two things per turn: whether code (as opposed to prose) was edited, and whether a
recognised verification command ran and succeeded. `stop.py` reads the result.

Writes state only. Never injects context, never blocks.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import common  # noqa: E402

VERIFICATION = re.compile(
    r"\b("
    r"pytest|python -m pytest|unittest|tox|nox"
    r"|jest|vitest|mocha|ava"
    r"|npm (run )?(test|lint|typecheck|build)|yarn (test|lint|build)|pnpm (test|lint|build)"
    r"|go (test|build|vet)|cargo (test|build|check|clippy)"
    r"|make (test|check|lint|build)"
    r"|tsc|mypy|ruff|flake8|eslint|biome|pyright"
    r"|swift test|xcodebuild|gradle test|mvn (test|verify)|dotnet test|rspec|phpunit"
    r")\b",
    re.I,
)

PROSE_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".adoc"}


def exit_code_of(payload):
    """Best-effort exit code for a Bash call. ``None`` when the payload does not carry one."""
    output = payload.get("tool_output")
    if isinstance(output, dict):
        for key in ("exit_code", "exitCode", "returncode", "status"):
            if isinstance(output.get(key), int):
                return output[key]
    for key in ("exit_code", "exitCode"):
        if isinstance(payload.get(key), int):
            return payload[key]
    return None


def main():
    payload = common.read_payload()
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return

    state = common.load_turn_state(payload)
    changed = False

    if tool == "Bash":
        command = str(tool_input.get("command") or "")
        if VERIFICATION.search(command):
            code = exit_code_of(payload)
            # An unknown exit code counts as evidence; a known failure does not.
            if code is None or code == 0:
                state["evidence"].append({"command": command[:300], "exit_code": code, "ts": time.time()})
                changed = True

    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        if path:
            if path not in state["touched"]:
                state["touched"].append(path)
            if Path(path).suffix.lower() not in PROSE_SUFFIXES:
                state["code_changed"] = True
            changed = True

    if changed:
        common.save_state(payload.get("session_id"), state)


if __name__ == "__main__":
    common.safe_main(main)
