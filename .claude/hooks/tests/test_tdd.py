#!/usr/bin/env python3
"""Contract tests for the RED/GREEN ledger the hooks keep in the brain.

The hooks record, they never block: a recognised verification command that fails is a ``red``
event, one that passes is a ``verification`` event, and nothing else is written. There is no
per-turn state, no test-file classification and no nudge — the Iterate phase and the auditor are
the only judges of done-ness.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
POST = HOOKS / "post_tool_use.py"

sys.path.insert(0, str(HOOKS / "lib"))
import brain  # noqa: E402


def run(script, payload, brain_path):
    env = dict(os.environ, GENTIC_BRAIN=str(brain_path))
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
        self.tmp = Path(tempfile.mkdtemp())
        self.brain = self.tmp / "brain.sqlite"
        self.repo = self.tmp / "proj"
        (self.repo / ".git").mkdir(parents=True)
        self.session = f"s-{uuid.uuid4().hex[:8]}"

    def new_session(self):
        return f"s-{uuid.uuid4().hex[:8]}"

    def edit(self, path):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": path},
            "session_id": self.session,
            "cwd": str(self.repo),
        }, self.brain)

    def bash(self, command, exit_code=None, session=None):
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "session_id": session or self.session,
            "cwd": str(self.repo),
        }
        if exit_code is not None:
            payload["tool_output"] = {"exit_code": exit_code}
        return run(POST, payload, self.brain)

    def rows(self, sql, *params):
        if not self.brain.exists():
            return []
        with sqlite3.connect(self.brain) as conn:
            return conn.execute(sql, params).fetchall()

    def kinds(self, session=None):
        return [k for (k,) in self.rows("select kind from events where session = ? order by id",
                                        session or self.session)]


class RedLedger(TddTestCase):
    """A failing verification run is the RED signal; a passing one is GREEN. Both live in the brain."""

    def test_event_kinds_are_exactly_red_and_verification(self):
        self.assertEqual(brain.EVENT_KINDS, ("red", "verification"))

    def test_failing_verification_is_recorded_as_red(self):
        self.bash("pytest tests/test_x.py", exit_code=1)
        self.assertEqual(self.kinds(), ["red"])

    def test_successful_verification_is_green(self):
        self.bash("pytest tests/test_x.py", exit_code=0)
        self.assertEqual(self.kinds(), ["verification"])

    def test_unknown_exit_code_is_green(self):
        """Unknown means assume it passed — the pre-existing rule."""
        self.bash("pytest tests/test_x.py")
        self.assertEqual(self.kinds(), ["verification"])

    def test_non_verification_and_edits_write_nothing(self):
        self.bash("ls /nonexistent", exit_code=2)
        self.edit(str(self.repo / "src" / "app.py"))
        self.assertEqual(self.kinds(), [], "only recognised verification commands are events")
        self.assertFalse(self.rows("select 1 from sessions where id = ?", self.session),
                         "an Edit must not touch session state")


class UiTestRunners(TddTestCase):
    """Playwright, Cypress, Lighthouse and axe runs are verification like any other: a green
    run is GREEN evidence and a red one is the RED of a UI test contract."""

    def test_ui_test_runners_are_verification_commands(self):
        for command in ("npx playwright test", "cypress run --e2e", "lighthouse http://localhost:3000 --quiet",
                        "npx @axe-core/cli http://localhost:3000"):
            with self.subTest(command=command):
                session = self.new_session()
                self.bash(command, exit_code=0, session=session)
                self.assertEqual(self.kinds(session), ["verification"],
                                 f"{command.split()[0]} run was not recorded as evidence")
        session = self.new_session()
        self.bash("npx playwright test", exit_code=1, session=session)
        self.assertEqual(self.kinds(session), ["red"], "a failing playwright run was not recorded as RED")


if __name__ == "__main__":
    unittest.main(verbosity=1)
