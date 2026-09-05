#!/usr/bin/env python3
"""PostToolUse — maintain the evidence ledger behind the verification and test-first gates.

Records four things per turn: whether code (as opposed to prose) was edited, whether any of
those edits was a test file, whether a recognised verification command succeeded, and whether
one *failed*. `stop.py` reads the result. The verification outcome is also appended to the
brain as a `red` or `verification` event — best-effort, so a missing brain changes nothing.

A failed verification run is the RED signal of test-first work, which is why it is kept rather
than discarded: "the test failed before the code was written" is only observable here.

Classification is deliberately additive. A test file sets ``test_touched`` *and* ``code_changed``
— the verification gate keys off the latter, so a test-only turn must keep arming it.

Writes state only. Never injects context, never blocks.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import brain, common, token_efficiency  # noqa: E402

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

PROSE_SUFFIXES = {".md", ".markdown", ".txt", ".rst", ".adoc"}

# Test files across the ecosystems this setup meets. Pure string matching, no filesystem access:
# this runs after every edit and the suite holds the hook to a 150ms median.
# `_test`/`test_` are anchored to a path boundary so `latest.py`, `contest.go` and `protest.ts`
# stay production code.
TEST_PATH = re.compile(
    r"(^|/)(tests?|specs?|__tests__)/"           # a test directory anywhere in the path
    r"|(^|/)test_[^/]*$"                          # test_app.py
    r"|_test\.[a-z0-9]+$"                         # app_test.go
    r"|\.(test|spec)\.[a-z0-9]+$"                 # app.test.ts, app.spec.js
    r"|(^|/)[^/]*_spec\.[a-z0-9]+$",              # user_spec.rb
    re.I,
)

# Subagents whose completion means this session's code has actually been looked at. The
# harness has named the subagent tool both ``Task`` and ``Agent`` across versions; accept both
# rather than tying the signal to one spelling.
REVIEW_AGENTS = {"code-reviewer", "dod-auditor"}
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

    state = common.load_turn_state(payload)
    changed = False

    if tool in SUBAGENT_TOOLS:
        subagent = str(tool_input.get("subagent_type") or "").strip()
        if subagent in REVIEW_AGENTS:
            state.setdefault("session", {})["reviewed"] = True
            changed = True
        # A foreground subagent returned: free its slot in the concurrency valve (floor 0).
        # Background spawns were never counted, so their return must not decrement either.
        session_id = payload.get("session_id")
        if session_id and not tool_input.get("run_in_background"):
            brain.session_release(session_id)

    elif tool == "Bash":
        command = str(tool_input.get("command") or "")
        token_efficiency.record_bash(state.setdefault("session", {}), command,
                                     payload.get("tool_output"))
        changed = True
        if VERIFICATION.search(command):
            code = exit_code_of(payload)
            entry = {"command": command[:300], "exit_code": code, "ts": time.time()}
            # An unknown exit code counts as success evidence; a known failure is RED instead.
            kind = "verification" if code is None or code == 0 else "red"
            if kind == "verification":
                state["evidence"].append(entry)
            else:
                state.setdefault("red", []).append(entry)
            brain.record_event(payload.get("cwd"), payload.get("session_id"), kind, command)
            changed = True

    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        if path:
            if path not in state["touched"]:
                state["touched"].append(path)
            if Path(path).suffix.lower() not in PROSE_SUFFIXES:
                state["code_changed"] = True
                if TEST_PATH.search(path):
                    state["test_touched"] = True
            token_efficiency.note_edit(state.setdefault("session", {}))
            changed = True

    if changed:
        common.save_state(payload.get("session_id"), state)


if __name__ == "__main__":
    common.safe_main(main)
