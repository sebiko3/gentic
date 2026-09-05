#!/usr/bin/env python3
"""PostToolUse — record RED and GREEN, and free the concurrency valve's slot.

Two things, both written to the brain and nothing else: a recognised verification command that
exited non-zero is a ``red`` event (the RED of test-first work — "the test failed before the code
was written" is only observable here), one that exited zero, or with no exit code available, is
a ``verification`` event. A foreground subagent's return releases its slot in the concurrency
valve. Every write is best-effort; a missing brain changes nothing.

Never injects context, never blocks.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import brain, common  # noqa: E402

VERIFICATION = re.compile(
    r"\b("
    r"pytest|python -m pytest|unittest|tox|nox"
    r"|jest|vitest|mocha|ava"
    r"|npm (run )?(test|lint|typecheck|build)|yarn (test|lint|build)|pnpm (test|lint|build)"
    r"|go (test|build|vet)|cargo (test|build|check|clippy)"
    r"|make (test|check|lint|build)"
    r"|tsc|mypy|ruff|flake8|eslint|biome|pyright"
    r"|swift test|xcodebuild|gradle test|mvn (test|verify)|dotnet test|rspec|phpunit"
    r"|playwright|cypress|lighthouse|axe"   # UI test runners and audits count too
    r")\b",
    re.I,
)

# The harness has named the subagent tool both ``Task`` and ``Agent`` across versions; accept
# both rather than tying the valve to one spelling.
SUBAGENT_TOOLS = {"Task", "Agent"}


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

    if tool in SUBAGENT_TOOLS:
        # A foreground subagent returned: free its slot in the concurrency valve (floor 0).
        # Background spawns were never counted, so their return must not decrement either.
        session_id = payload.get("session_id")
        if session_id and not tool_input.get("run_in_background"):
            brain.session_release(session_id)
        return

    if tool != "Bash":
        return
    command = str(tool_input.get("command") or "")
    if not VERIFICATION.search(command):
        return
    code = exit_code_of(payload)
    # An unknown exit code counts as success evidence; a known failure is RED instead.
    kind = "verification" if code is None or code == 0 else "red"
    brain.record_event(payload.get("cwd"), payload.get("session_id"), kind, command)


if __name__ == "__main__":
    common.safe_main(main)
