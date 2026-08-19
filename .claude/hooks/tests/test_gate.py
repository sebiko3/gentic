#!/usr/bin/env python3
"""Contract tests for the verification gate: PostToolUse ledger + Stop block.

The two are one mechanism. PostToolUse records what was edited and what was verified;
Stop refuses a "done" claim when the ledger shows edits but no verification.

The escape-hatch test is the safety-critical one: a false positive must cost exactly one
extra turn, never a deadlock.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
POST = HOOKS / "post_tool_use.py"
STOP = HOOKS / "stop.py"


def run(script, payload, state_dir):
    env = dict(os.environ, CLAUDE_HOOK_STATE_DIR=state_dir)
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


class GateTestCase(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.session = f"s-{uuid.uuid4().hex[:8]}"
        self.prompt_id = f"p-{uuid.uuid4().hex[:8]}"

    def edit(self, path="src/app.py"):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": path},
            "session_id": self.session,
            "prompt_id": self.prompt_id,
        }, self.state)

    def bash(self, command, output=None):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "session_id": self.session,
            "prompt_id": self.prompt_id,
        }
        if output is not None:
            payload["tool_output"] = output
        return run(POST, payload, self.state)

    def read_state(self):
        """Recorded state for this session; ``{}`` when the hook wrote nothing."""
        path = Path(self.state) / f"{self.session}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def stop(self, message):
        return run(STOP, {
            "hook_event_name": "Stop",
            "last_assistant_message": message,
            "session_id": self.session,
            "prompt_id": self.prompt_id,
        }, self.state)


class Ledger(GateTestCase):
    def test_records_a_code_edit(self):
        code, _, err = self.edit()
        self.assertEqual(code, 0, err)
        state = self.read_state()
        self.assertTrue(state["code_changed"])

    def test_documentation_edit_is_not_a_code_change(self):
        self.edit("docs/README.md")
        state = self.read_state()
        self.assertFalse(state.get("code_changed"))

    def test_records_a_verification_command(self):
        self.bash("pytest tests/", output={"exit_code": 0})
        state = self.read_state()
        self.assertEqual(len(state["evidence"]), 1)

    def test_ignores_a_non_verification_command(self):
        self.bash("git status")
        state = self.read_state()
        self.assertEqual(state.get("evidence", []), [])

    def test_records_evidence_when_exit_code_is_unavailable(self):
        self.bash("npm test", output="all suites passed")
        state = self.read_state()
        self.assertEqual(len(state["evidence"]), 1)
        self.assertIsNone(state["evidence"][0]["exit_code"])

    def test_failing_verification_is_not_counted_as_evidence(self):
        self.bash("pytest tests/", output={"exit_code": 1})
        state = self.read_state()
        self.assertEqual(state.get("evidence", []), [])

    def test_never_blocks(self):
        self.assertEqual(self.edit()[0], 0)
        self.assertEqual(self.bash("pytest")[0], 0)


class Gate(GateTestCase):
    def test_blocks_unverified_done_claim_after_code_edit(self):
        self.edit()
        code, _, err = self.stop("All set — the retry logic is fixed and working now.")
        self.assertEqual(code, 2)
        self.assertTrue(err.strip())

    def test_allows_done_claim_once_verification_ran(self):
        self.edit()
        self.bash("pytest tests/", output={"exit_code": 0})
        self.assertEqual(self.stop("All set — the retry logic is fixed and working now.")[0], 0)

    def test_allows_a_conversational_turn(self):
        self.assertEqual(self.stop("OAuth works by exchanging an authorization code for a token.")[0], 0)

    def test_allows_an_edit_with_no_done_claim(self):
        self.edit()
        self.assertEqual(self.stop("I've drafted the change; want me to run the suite?")[0], 0)

    def test_escape_hatch_blocks_at_most_once_per_prompt(self):
        self.edit()
        claim = "Done — everything is passing."
        self.assertEqual(self.stop(claim)[0], 2, "first stop should block")
        self.assertEqual(self.stop(claim)[0], 0, "second stop must pass — no deadlock")

    def test_a_new_prompt_re_arms_the_gate(self):
        self.edit()
        claim = "Done — everything is passing."
        self.assertEqual(self.stop(claim)[0], 2)
        self.assertEqual(self.stop(claim)[0], 0)
        self.prompt_id = "p-next"
        self.edit()
        self.assertEqual(self.stop(claim)[0], 2, "gate should re-arm for a new user prompt")


class RealPayloadShape(GateTestCase):
    """Live sessions do not send `prompt_id` (verified 2026-08-17, Claude Code 2.1.193).

    Turn boundaries therefore come from UserPromptSubmit, which fires exactly once per prompt.
    Without this, per-turn state would accumulate for a whole session and the gate would fire
    at most once per session instead of once per prompt.
    """

    def setUp(self):
        super().setUp()
        self.prompt_id = None  # match the real payload

    def new_prompt(self, text="add retry handling to the client"):
        return run(HOOKS / "user_prompt_submit.py", {
            "hook_event_name": "UserPromptSubmit",
            "prompt": text,
            "session_id": self.session,
            "cwd": tempfile.gettempdir(),
        }, self.state)

    def payload_without_prompt_id(self, base):
        return {k: v for k, v in base.items() if k != "prompt_id"}

    def edit(self, path="src/app.py"):
        return run(POST, self.payload_without_prompt_id({
            "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": path}, "session_id": self.session,
        }), self.state)

    def stop(self, message):
        return run(STOP, self.payload_without_prompt_id({
            "hook_event_name": "Stop", "last_assistant_message": message,
            "session_id": self.session,
        }), self.state)

    def test_gate_blocks_without_a_prompt_id(self):
        self.new_prompt()
        self.edit()
        self.assertEqual(self.stop("Done — everything is passing.")[0], 2)

    def test_gate_re_arms_on_the_next_user_prompt(self):
        claim = "Done — everything is passing."
        self.new_prompt()
        self.edit()
        self.assertEqual(self.stop(claim)[0], 2, "first turn should block")
        self.assertEqual(self.stop(claim)[0], 0, "escape hatch")

        self.new_prompt("now add backoff to the same client")
        self.edit()
        self.assertEqual(self.stop(claim)[0], 2, "second turn must re-arm the gate")

    def test_evidence_does_not_leak_across_turns(self):
        self.new_prompt()
        self.edit()
        self.bash("pytest tests/", output={"exit_code": 0})
        self.assertEqual(self.stop("All fixed and passing.")[0], 0)

        self.new_prompt("now change the timeout default")
        self.edit()
        self.assertEqual(
            self.stop("All fixed and passing.")[0], 2,
            "last turn's passing tests must not vouch for this turn's edit",
        )


class Degradation(GateTestCase):
    def test_hooks_survive_empty_stdin(self):
        for script in (POST, STOP):
            with self.subTest(script=script.name):
                proc = subprocess.run(
                    [sys.executable, str(script)], input="", capture_output=True, text=True, timeout=15
                )
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn("Traceback", proc.stderr)

    def test_hooks_survive_malformed_json(self):
        for script in (POST, STOP):
            with self.subTest(script=script.name):
                proc = subprocess.run(
                    [sys.executable, str(script)], input="{nope", capture_output=True, text=True, timeout=15
                )
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn("Traceback", proc.stderr)

    def test_stop_survives_missing_message(self):
        code, _, err = run(STOP, {"hook_event_name": "Stop", "session_id": self.session}, self.state)
        self.assertEqual(code, 0)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main(verbosity=1)
