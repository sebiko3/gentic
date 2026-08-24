#!/usr/bin/env python3
"""Contract tests for the token-efficiency guards and the spend ledger.

Two guards (duplicate Read, bare cat of a large file) may deny — each at most once per path
per session, with a valve so a false positive costs exactly one retry and can never loop.
Everything else here measures: estimated spend accumulates in session state and is reported
to the user once, at a threshold, never to the model.
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
PRE = HOOKS / "pre_tool_use.py"
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


class EfficiencyTestCase(unittest.TestCase):
    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.work = tempfile.mkdtemp()
        self.session = f"s-{uuid.uuid4().hex[:8]}"

    def tmpfile(self, content, name="file.py"):
        path = Path(self.work) / name
        path.write_text(content)
        return str(path)

    def read(self, path, **params):
        return run(PRE, {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": path, **params},
            "session_id": self.session,
            "cwd": self.work,
        }, self.state)

    def read_state(self):
        path = Path(self.state) / f"{self.session}.json"
        return json.loads(path.read_text()) if path.exists() else {}


class DuplicateReadGuard(EfficiencyTestCase):
    def test_duplicate_read_is_denied_once(self):
        f = self.tmpfile("x = 1\n" * 20)
        code, _, err = self.read(f)
        self.assertEqual(code, 0, f"first read must pass: {err}")
        code, _, err = self.read(f)
        self.assertEqual(code, 2, "duplicate read was not denied")
        lowered = err.lower()
        self.assertIn("already", lowered, "deny must say the content is already in context")
        self.assertIn("offset", lowered, "deny must name the offset/limit escape")
        self.assertIn("once", lowered, "deny must state the once-per-file bound")

    def test_valve_never_denies_twice_per_path(self):
        f = self.tmpfile("x = 1\n" * 20)
        self.read(f)
        code, _, _ = self.read(f)
        self.assertEqual(code, 2, "precondition: second read denied")
        code, _, err = self.read(f)
        self.assertEqual(code, 0, f"valve failed — second deny on same path: {err}")

    def test_read_with_offset_or_limit_always_passes(self):
        f = self.tmpfile("x = 1\n" * 20)
        self.read(f)
        for params in ({"offset": 5}, {"limit": 10}, {"offset": 1, "limit": 5}):
            with self.subTest(params=params):
                code, _, err = self.read(f, **params)
                self.assertEqual(code, 0, f"parameterised read must pass: {err}")

    def test_modified_file_passes_and_refreshes_the_ledger(self):
        f = self.tmpfile("x = 1\n" * 20)
        self.read(f)
        Path(f).write_text("y = 2\n" * 30)  # different size — unambiguous identity change
        code, _, err = self.read(f)
        self.assertEqual(code, 0, f"read of a modified file must pass: {err}")
        code, _, _ = self.read(f)
        self.assertEqual(code, 2, "ledger was not refreshed by the modified-file read")

    def test_legacy_state_upgrades_in_place(self):
        legacy = {
            "turn": 3, "prompt_id": "p-old", "evidence": [], "touched": [],
            "code_changed": False, "session": {"reviewed": True},
        }
        (Path(self.state) / f"{self.session}.json").write_text(json.dumps(legacy))
        f = self.tmpfile("x = 1\n" * 20)
        code, _, err = self.read(f)
        self.assertEqual(code, 0, f"first read on legacy state must pass: {err}")
        self.assertNotIn("Traceback", err)
        code, _, err = self.read(f)
        self.assertEqual(code, 2, "no deny on legacy state")
        self.assertNotIn("Traceback", err)
        # The legacy session facts must survive the upgrade.
        self.assertTrue(self.read_state()["session"].get("reviewed"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
