#!/usr/bin/env python3
"""Contract tests for the test-first ledger and the advisory TDD nudge.

The verification gate (test_gate.py) answers "was anything verified?". This suite answers the
prior question: "did a test fail before the production code was written?".

Two properties are safety-critical here and each has a test below:

1. Classifying a path as a test file must stay *additive*. The existing verification gate keys
   off ``code_changed``, so a test-only turn must still set it; otherwise a turn that edits only
   tests could claim success unverified.
2. The TDD nudge never blocks. It is advisory by design — a second adversarial gate would make
   the setup something to work around rather than with (see stop.py's module docstring).
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


class TddTestCase(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.session = f"s-{uuid.uuid4().hex[:8]}"
        self.prompt_id = f"p-{uuid.uuid4().hex[:8]}"

    def new_session(self):
        """A separate session sharing this test's state directory."""
        return f"s-{uuid.uuid4().hex[:8]}"

    def edit(self, path, session=None):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": path},
            "session_id": session or self.session,
            "prompt_id": self.prompt_id,
        }, self.state)

    def bash(self, command, exit_code=None, session=None):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "session_id": session or self.session,
            "prompt_id": self.prompt_id,
        }
        if exit_code is not None:
            payload["tool_output"] = {"exit_code": exit_code}
        return run(POST, payload, self.state)

    def stop(self, message="Here is the change.", session=None):
        return run(STOP, {
            "hook_event_name": "Stop",
            "last_assistant_message": message,
            "session_id": session or self.session,
            "prompt_id": self.prompt_id,
        }, self.state)

    def read_state(self, session=None):
        path = Path(self.state) / f"{session or self.session}.json"
        return json.loads(path.read_text()) if path.exists() else {}


class RedLedger(TddTestCase):
    """A failing verification run is the RED signal; it used to be discarded."""

    def test_failing_verification_is_recorded_as_red(self):
        self.bash("pytest tests/test_x.py", exit_code=1)
        state = self.read_state()
        # .get, not [] — a KeyError would be a test *error*, and a RED must be a clean failure.
        self.assertTrue(state.get("red"), "no RED recorded for a failing verification command")

    def test_successful_verification_is_not_red(self):
        self.bash("pytest tests/test_x.py", exit_code=0)
        state = self.read_state()
        self.assertFalse(state.get("red"), "a passing command must not count as RED")
        self.assertTrue(state.get("evidence"), "a passing command is still success evidence")

    def test_unknown_exit_code_still_counts_as_success_evidence(self):
        """Pre-existing behaviour (post_tool_use.py): unknown means assume it passed."""
        self.bash("pytest tests/test_x.py")
        state = self.read_state()
        self.assertTrue(state.get("evidence"))
        self.assertFalse(state.get("red"))

    def test_a_failing_non_verification_command_is_not_red(self):
        self.bash("ls /nonexistent", exit_code=2)
        state = self.read_state()
        self.assertFalse(state.get("red"), "only recognised verification commands can be RED")


class TestFileClassification(TddTestCase):
    TEST_PATHS = [
        "tests/test_app.py",
        "test_app.py",
        "pkg/app_test.go",
        "src/app.test.ts",
        "src/app.spec.js",
        "__tests__/app.jsx",
        "spec/models/user.rb",
        "test/helpers.py",
    ]
    PRODUCTION_PATHS = ["src/app.py", "lib/latest.py", "pkg/contest.go", "src/protest.ts"]

    def test_test_files_are_classified_separately(self):
        self.edit("tests/test_app.py")
        state = self.read_state()
        self.assertTrue(state.get("test_touched"), "test file edit was not recorded")
        # Additive only: the existing verification gate keys off code_changed.
        self.assertTrue(state.get("code_changed"), "test edits must still arm the verification gate")

    def test_production_edit_sets_no_test_marker(self):
        self.edit("src/app.py")
        state = self.read_state()
        self.assertTrue(state.get("code_changed"))
        self.assertFalse(state.get("test_touched"))

    def test_recognised_test_path_shapes(self):
        for path in self.TEST_PATHS:
            with self.subTest(path=path):
                session = self.new_session()
                self.edit(path, session=session)
                self.assertTrue(self.read_state(session).get("test_touched"), path)

    def test_production_paths_are_not_mistaken_for_tests(self):
        for path in self.PRODUCTION_PATHS:
            with self.subTest(path=path):
                session = self.new_session()
                self.edit(path, session=session)
                self.assertFalse(self.read_state(session).get("test_touched"), path)


class TddNudge(TddTestCase):
    def test_tdd_nudge_is_advisory(self):
        self.edit("src/app.py")
        code, out, err = self.stop()
        self.assertEqual(code, 0, f"the TDD path must never block: {err}")
        self.assertIn("failing test", (out + err).lower())

    def test_tdd_nudge_suppressed_and_bounded(self):
        # (a) RED observed this turn — nothing to warn about.
        self.edit("src/app.py")
        self.bash("pytest tests/test_x.py", exit_code=1)
        _, out, _ = self.stop()
        self.assertNotIn("failing test", out.lower(), "RED evidence must suppress the nudge")

        # (b) a test file was touched — test-first behaviour, nothing to warn about.
        b = self.new_session()
        self.edit("tests/test_app.py", session=b)
        self.edit("src/app.py", session=b)
        _, out, _ = self.stop(session=b)
        self.assertNotIn("failing test", out.lower(), "a test edit must suppress the nudge")

        # (c) at most once per session.
        c = self.new_session()
        self.edit("src/app.py", session=c)
        _, first, _ = self.stop(session=c)
        self.edit("src/other.py", session=c)
        _, second, _ = self.stop(session=c)
        fired = sum(1 for o in (first, second) if "failing test" in o.lower())
        self.assertEqual(fired, 1, "nudge fired twice in one session")

    def test_both_nudges_arrive_as_one_message(self):
        """Regression: routing the TDD nudge first once silenced the review nudge entirely.

        Both are once-per-session and both can come due on the same stop, so they are combined
        rather than made to compete.
        """
        self.edit("src/app.py")
        _, out, _ = self.stop()
        lowered = out.lower()
        self.assertIn("failing test", lowered)
        self.assertIn("/review", out)
        self.assertEqual(out.strip().count("\n"), 0, "advisory output must be one JSON object")

    def test_prose_only_turn_is_never_nudged(self):
        self.edit("README.md")
        _, out, _ = self.stop()
        self.assertNotIn("failing test", out.lower())


class UiTestRunners(TddTestCase):
    """Playwright, Cypress, Lighthouse and axe runs are verification like any other: a green
    run is evidence for the Stop gate and a red one is the RED of a UI test contract."""

    def bash(self, command, exit_code, session=None):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_output": {"exit_code": exit_code},
            "session_id": session or self.session,
            "prompt_id": self.prompt_id,
        }, self.state)

    def state_of(self, session):
        path = Path(self.state) / f"{session}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def test_ui_test_runners_are_verification_commands(self):
        for command in ("npx playwright test", "cypress run --e2e", "lighthouse http://localhost:3000 --quiet",
                        "npx @axe-core/cli http://localhost:3000"):
            with self.subTest(command=command):
                session = self.new_session()
                self.bash(command, 0, session=session)
                evidence = self.state_of(session).get("evidence", [])
                self.assertNotEqual(evidence, [], f"{command.split()[0]} run was not recorded as evidence")
        session = self.new_session()
        self.bash("npx playwright test", 1, session=session)
        self.assertNotEqual(self.state_of(session).get("red", []), [], "a failing playwright run was not recorded as RED")


if __name__ == "__main__":
    unittest.main(verbosity=1)
