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

    def bash_pre(self, command):
        return run(PRE, {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "session_id": self.session,
            "cwd": self.work,
        }, self.state)

    def bash_post(self, command, output="", exit_code=0):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_output": {"stdout": output, "exit_code": exit_code},
            "session_id": self.session,
            "cwd": self.work,
        }, self.state)

    def edit_post(self, path="src/app.py"):
        return run(POST, {
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": path},
            "session_id": self.session,
        }, self.state)

    def begin_turn(self):
        """A user prompt boundary, via the hook that owns it."""
        return run(HOOKS / "user_prompt_submit.py", {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "continue",
            "session_id": self.session,
            "cwd": self.work,
        }, self.state)

    def stop(self, message="Here is the summary."):
        return run(STOP, {
            "hook_event_name": "Stop",
            "last_assistant_message": message,
            "session_id": self.session,
        }, self.state)

    def seed_session(self, **session):
        """Write a state file with the given session facts, bypassing the hooks."""
        state = {"turn": 1, "evidence": [], "touched": [], "code_changed": False,
                 "test_touched": False, "red": [], "session": session}
        (Path(self.state) / f"{self.session}.json").write_text(json.dumps(state))

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


class BareCatGuard(EfficiencyTestCase):
    def big(self, name="big.log"):
        return self.tmpfile("line of log text padded out to something real\n" * 2600, name)  # ~112 KB

    def test_bare_cat_of_large_file_is_denied_once(self):
        f = self.big()
        code, _, err = self.bash_pre(f"cat {f}")
        self.assertEqual(code, 2, "bare cat passed")
        lowered = err.lower()
        self.assertTrue("sed -n" in lowered or "range" in lowered,
                        f"deny must suggest a ranged read: {err}")
        code, _, err = self.bash_pre(f"cat {f}")
        self.assertEqual(code, 0, f"valve failed — second cat deny on same path: {err}")

    def test_bounded_and_composed_forms_pass(self):
        f = self.big()
        small = self.tmpfile("tiny\n", "small.txt")
        for command in (f"cat {f} | wc -l", f"cat {f} > /dev/null", f"cat {small}",
                        f"head {f}", f"tail {f}", f"cat {f} {small}", "cat missing.log"):
            with self.subTest(command=command):
                code, _, err = self.bash_pre(command)
                self.assertEqual(code, 0, f"must pass: {command}: {err}")

    def test_relative_path_resolves_against_cwd(self):
        self.big("rel.log")
        code, _, _ = self.bash_pre("cat rel.log")
        self.assertEqual(code, 2, "relative bare cat was not resolved against cwd")


class SpendLedger(EfficiencyTestCase):
    def session_state(self):
        return self.read_state().get("session", {})

    def test_spend_accumulates_across_turns(self):
        f = self.tmpfile("x = 1\n" * 200)
        self.read(f)
        after_read = self.session_state().get("spend_est", 0)
        self.assertGreater(after_read, 0, "no spend recorded")
        self.bash_post("grep -rn foo src", output="hit\n" * 500)
        after_bash = self.session_state().get("spend_est", 0)
        self.assertGreater(after_bash, after_read, "Bash result added no spend")
        self.begin_turn()
        f2 = self.tmpfile("y = 2\n" * 200, "other.py")
        self.read(f2)
        final = self.session_state().get("spend_est", 0)
        self.assertGreater(final, after_bash, "spend did not survive the turn boundary")

    def test_repeat_readonly_bash_counted_not_denied(self):
        code, _, _ = self.bash_post("grep -rn foo src", output="hit\n")
        self.assertEqual(code, 0)
        code, _, _ = self.bash_post("grep -rn foo src", output="hit\n")
        self.assertEqual(code, 0, "repeats must never be denied")
        self.assertEqual(self.session_state().get("bash_repeats", 0), 1, "repeat not counted")

    def test_intervening_edit_resets_repeat_eligibility(self):
        self.bash_post("grep -rn foo src", output="hit\n")
        self.edit_post()
        self.bash_post("grep -rn foo src", output="hit\n")
        self.assertEqual(self.session_state().get("bash_repeats", 0), 0,
                         "an edited tree makes a re-run legitimate")

    def test_mutating_commands_are_not_repeat_tracked(self):
        self.bash_post("python3 setup.py build", output="ok\n")
        self.bash_post("python3 setup.py build", output="ok\n")
        self.assertEqual(self.session_state().get("bash_repeats", 0), 0)


class SpendReport(EfficiencyTestCase):
    def test_spend_report_threshold_and_once(self):
        self.seed_session(spend_est=60_000, spend_saved=4_000, reads_n=21, bash_n=34,
                          bash_repeats=3)
        code, out, _ = self.stop()
        self.assertEqual(code, 0, "the report path must never block")
        self.assertIn("tokens", out.lower(), "no spend report")
        self.assertIn("estimated", out.lower(), "the report must declare itself an estimate")
        code, out, _ = self.stop()
        self.assertNotIn("tokens", out.lower(), "spend reported twice in one session")

    def test_below_threshold_stays_silent(self):
        self.seed_session(spend_est=20_000, reads_n=8, bash_n=13)
        _, out, _ = self.stop()
        self.assertNotIn("estimated", out.lower(), "report fired below the 55k threshold")


class Documentation(unittest.TestCase):
    def test_docs_document_the_guards(self):
        body = (HOOKS / "README.md").read_text(encoding="utf-8")
        lowered = body.lower()
        self.assertIn("duplicate", lowered, "hooks README does not document the read guard")
        self.assertIn("89", body, "hooks README does not name the cat-guard threshold")
        self.assertIn("valve", lowered, "hooks README does not document the guards")
        self.assertIn("estimate", lowered, "hooks README does not declare estimates heuristic")
        self.assertIn("once per", lowered, "hooks README does not state the once-per bound")


if __name__ == "__main__":
    unittest.main(verbosity=1)
