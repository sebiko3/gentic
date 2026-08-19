#!/usr/bin/env python3
"""The advisory review nudge.

Code review used to happen only when the user remembered to type /ship. The nudge closes that
gap, but it must stay advisory: `stop.py` documents the verification gate as the setup's only
routine hard block, and a second blocking gate would make the setup adversarial.

Two properties matter more than the nudge itself, and both are tested here: it never blocks,
and it fires at most once per session rather than once per turn.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

from lib import common  # noqa: E402


def run_hook(script, payload, state_dir):
    env = dict(os.environ, CLAUDE_HOOK_STATE_DIR=str(state_dir))
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload), text=True, capture_output=True, env=env,
    )


class NudgeCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="hookstate-"))
        self.session = "sess-nudge"
        os.environ["CLAUDE_HOOK_STATE_DIR"] = str(self.dir)
        common.STATE_DIR = self.dir

    def tearDown(self):
        os.environ.pop("CLAUDE_HOOK_STATE_DIR", None)

    def write_state(self, **overrides):
        state = {
            "turn": 1, "prompt_id": None, "evidence": [], "touched": [],
            "code_changed": False, "session": {},
        }
        state.update(overrides)
        common.save_state(self.session, state)
        return state

    def stop(self, message="Here is what I changed."):
        return run_hook("stop.py", {
            "session_id": self.session, "last_assistant_message": message,
        }, self.dir)


class TheNudgeFires(NudgeCase):
    def test_when_code_changed_and_nothing_reviewed_it(self):
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        result = self.stop()
        self.assertIn("review", result.stdout.lower(), result.stdout)
        self.assertIn("/review", result.stdout)

    def test_it_names_how_many_files_changed(self):
        self.write_state(code_changed=True, touched=["/repo/a.py", "/repo/b.py"])
        self.assertIn("2", self.stop().stdout)


class TheNudgeStaysSilent(NudgeCase):
    def test_when_a_review_already_ran_this_session(self):
        self.write_state(code_changed=True, touched=["/repo/api.py"], session={"reviewed": True})
        self.assertNotIn("/review", self.stop().stdout)

    def test_when_no_code_changed(self):
        self.write_state(code_changed=False, touched=["/repo/notes.md"])
        self.assertNotIn("/review", self.stop().stdout)

    def test_after_it_has_already_been_shown_once_this_session(self):
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        first = self.stop()
        self.assertIn("/review", first.stdout)

        # A later turn in the same session: the ledger resets, the session memory does not.
        common.begin_turn({"session_id": self.session})
        state = common.load_state(self.session)
        state["code_changed"] = True
        state["touched"] = ["/repo/other.py"]
        common.save_state(self.session, state)

        second = self.stop()
        self.assertNotIn("/review", second.stdout, "nudged twice in one session")


class TheNudgeNeverBlocks(NudgeCase):
    def test_exit_zero_and_no_block_decision(self):
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        result = self.stop()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('"decision"', result.stdout)
        self.assertNotIn("block", result.stdout.lower())

    def test_it_does_not_suppress_the_verification_gate(self):
        """A done-claim with no evidence must still be blocked, nudge or no nudge."""
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        result = self.stop("All done — the fix is complete and tests are passing.")
        self.assertEqual(result.returncode, 2, "verification gate stopped firing")
        self.assertIn("Verification gate", result.stderr)


class ReviewIsRecorded(NudgeCase):
    """post_tool_use must observe a real review, not assume one."""

    def invoke_subagent(self, tool_name, subagent):
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        run_hook("post_tool_use.py", {
            "session_id": self.session,
            "tool_name": tool_name,
            "tool_input": {"subagent_type": subagent, "prompt": "review the diff"},
        }, self.dir)
        return common.load_state(self.session).get("session", {})

    def test_under_the_task_tool_name(self):
        self.assertTrue(self.invoke_subagent("Task", "code-reviewer").get("reviewed"))

    def test_under_the_agent_tool_name(self):
        self.assertTrue(self.invoke_subagent("Agent", "code-reviewer").get("reviewed"))

    def test_the_dod_auditor_also_counts_as_review(self):
        self.assertTrue(self.invoke_subagent("Agent", "dod-auditor").get("reviewed"))

    def test_an_unrelated_subagent_does_not(self):
        self.assertFalse(self.invoke_subagent("Agent", "Explore").get("reviewed"))

    def test_recording_a_review_silences_the_nudge_end_to_end(self):
        self.write_state(code_changed=True, touched=["/repo/api.py"])
        run_hook("post_tool_use.py", {
            "session_id": self.session, "tool_name": "Agent",
            "tool_input": {"subagent_type": "code-reviewer", "prompt": "review"},
        }, self.dir)
        self.assertNotIn("/review", self.stop().stdout)


class SessionMemorySurvivesTurns(NudgeCase):
    def test_begin_turn_preserves_the_session_dict(self):
        self.write_state(session={"reviewed": True, "review_nudge_shown": True})
        common.begin_turn({"session_id": self.session})
        carried = common.load_state(self.session).get("session", {})
        self.assertEqual(carried, {"reviewed": True, "review_nudge_shown": True})

    def test_begin_turn_still_clears_the_per_turn_ledger(self):
        self.write_state(code_changed=True, touched=["/repo/a.py"],
                         evidence=[{"command": "pytest"}], session={"reviewed": True})
        common.begin_turn({"session_id": self.session})
        state = common.load_state(self.session)
        self.assertFalse(state["code_changed"])
        self.assertEqual(state["touched"], [])
        self.assertEqual(state["evidence"], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
