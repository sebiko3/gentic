#!/usr/bin/env python3
"""Contract tests for the destructive-command guard and the session resume notice."""

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
GUARD = HOOKS / "pre_tool_use.py"
SESSION = HOOKS / "session_start.py"
PRE = HOOKS / "pre_tool_use.py"
POST = HOOKS / "post_tool_use.py"
PROMPT = HOOKS / "user_prompt_submit.py"


def run(script, payload, brain=None):
    env = dict(os.environ)
    if brain:
        env["GENTIC_BRAIN"] = str(brain)
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def guard(command):
    code, out, err = run(GUARD, {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "guard-test",
    })
    decision = None
    if out.strip():
        decision = json.loads(out).get("hookSpecificOutput", {}).get("permissionDecision")
    return code, decision


class Guard(unittest.TestCase):
    def test_denies_force_push(self):
        for command in ("git push --force origin main", "git push -f origin main"):
            with self.subTest(command=command):
                self.assertEqual(guard(command)[1], "deny")

    def test_allows_force_with_lease(self):
        self.assertIsNone(guard("git push --force-with-lease origin feature")[1])

    def test_denies_hard_reset_and_clean(self):
        for command in ("git reset --hard HEAD~3", "git clean -fdx"):
            with self.subTest(command=command):
                self.assertEqual(guard(command)[1], "deny")

    def test_denies_recursive_delete_of_home_or_root(self):
        for command in ("rm -rf /", "rm -rf ~", "rm -rf $HOME/", "rm -rf /Users/sebiko83"):
            with self.subTest(command=command):
                self.assertEqual(guard(command)[1], "deny")

    def test_allows_ordinary_commands(self):
        for command in (
            "git push origin feature",
            "git status",
            "rm -rf ./node_modules",
            "rm -rf build/",
            "npm test",
            "git reset --soft HEAD~1",
            "git commit -m 'clean up'",
        ):
            with self.subTest(command=command):
                self.assertIsNone(guard(command)[1], f"false positive on: {command}")

    def test_ignores_dangerous_commands_quoted_inside_another_command(self):
        """A command that merely *mentions* a dangerous one must not be blocked.

        Found in live use: a test script containing the literal text "git push --force"
        inside a quoted string was refused, which is the false-positive class that gets a
        guard trained away.
        """
        for command in (
            """python3 -c 'print("git push --force")'""",
            'echo "never run git push --force"',
            "grep -r 'git reset --hard' docs/",
            'printf "%s\\n" "rm -rf /"',
        ):
            with self.subTest(command=command):
                self.assertIsNone(guard(command)[1], f"false positive on: {command}")

    def test_still_denies_dangerous_commands_at_command_position(self):
        for command in (
            "git push --force origin main",
            "npm test && git push --force",
            "cd /tmp; git reset --hard HEAD~1",
            "make build | tee log && git clean -fdx",
        ):
            with self.subTest(command=command):
                self.assertEqual(guard(command)[1], "deny", f"missed: {command}")

    def test_never_blocks_by_exit_code(self):
        self.assertEqual(guard("git push --force origin main")[0], 0)

    def test_ignores_non_bash_tools(self):
        code, out, _ = run(GUARD, {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "a.py"},
        })
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")


class ConcurrencyValve(unittest.TestCase):
    """At most five foreground subagents in flight per session; a cap, serialised with a lock,
    reset at every user prompt, blind to background spawns by design."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "brain.sqlite"
        self.session = f"s-{uuid.uuid4().hex[:8]}"

    def spawn_payload(self, background=False):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Task",
                   "tool_input": {"subagent_type": "general-purpose", "prompt": "x"},
                   "session_id": self.session}
        if background:
            payload["tool_input"]["run_in_background"] = True
        return payload

    def decision(self, stdout):
        try:
            return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
        except Exception:
            return None

    def count(self):
        if not self.state.exists():
            return 0
        with sqlite3.connect(self.state) as conn:
            row = conn.execute("select agents_in_flight from sessions where id = ?", (self.session,)).fetchone()
        return row[0] if row else 0

    def test_concurrency_valve_denies_a_sixth_agent(self):
        for _ in range(5):
            code, out, _ = run(PRE, self.spawn_payload(), self.state)
            self.assertIsNone(self.decision(out))
        code, out, _ = run(PRE, self.spawn_payload(), self.state)
        self.assertEqual(self.decision(out), "deny", "sixth spawn was not denied")
        self.assertIn("in flight", out)
        run(POST, {"hook_event_name": "PostToolUse", "tool_name": "Task",
                   "tool_input": {"subagent_type": "general-purpose"}, "session_id": self.session}, self.state)
        code, out, _ = run(PRE, self.spawn_payload(), self.state)
        self.assertIsNone(self.decision(out), "a returned agent did not free a slot")
        code, out, _ = run(PRE, self.spawn_payload(background=True), self.state)
        self.assertIsNone(self.decision(out), "a background spawn must never be denied")

    def test_background_return_frees_no_foreground_slot(self):
        """Background spawns are never counted, so their return must not decrement either —
        otherwise a sixth foreground subagent slips through the cap."""
        for _ in range(5):
            run(PRE, self.spawn_payload(), self.state)
        run(POST, {"hook_event_name": "PostToolUse", "tool_name": "Task",
                   "tool_input": {"subagent_type": "general-purpose", "run_in_background": True},
                   "session_id": self.session}, self.state)
        code, out, _ = run(PRE, self.spawn_payload(), self.state)
        self.assertEqual(self.decision(out), "deny", "a background return freed a foreground slot")

    def test_valve_counts_parallel_spawns(self):
        env = dict(os.environ, GENTIC_BRAIN=str(self.state))
        procs = [subprocess.Popen([sys.executable, str(PRE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=env) for _ in range(5)]
        for proc in procs:
            proc.communicate(json.dumps(self.spawn_payload()), timeout=30)
        self.assertEqual(self.count(), 5, "parallel spawns lost updates")

    def test_valve_resets_on_a_new_prompt(self):
        for _ in range(3):
            run(PRE, self.spawn_payload(), self.state)
        run(PROMPT, {"hook_event_name": "UserPromptSubmit", "prompt": "next", "session_id": self.session}, self.state)
        self.assertEqual(self.count(), 0)

    def test_missing_session_id_writes_no_session_row(self):
        """A payload without a session id (the hostile-input sweep sends them) must not leave a
        NULL-keyed row that no later reset or release can ever match."""
        run(PROMPT, {"hook_event_name": "UserPromptSubmit", "prompt": "next"}, self.state)
        payload = self.spawn_payload()
        del payload["session_id"]
        run(PRE, payload, self.state)
        run(POST, {"hook_event_name": "PostToolUse", "tool_name": "Task",
                   "tool_input": {"subagent_type": "general-purpose"}}, self.state)
        rows = 0
        if self.state.exists():
            with sqlite3.connect(self.state) as conn:
                rows = conn.execute("select count(*) from sessions").fetchone()[0]
        self.assertEqual(rows, 0, "a session row was written without a session id")

    def test_valve_fails_open_without_a_brain(self):
        """An unopenable brain means an uncapped valve, silently — better than a blocked session."""
        blocker = self.tmp / "blocker.txt"
        blocker.write_text("not a directory")
        bad = blocker / "deeper" / "brain.sqlite"
        for _ in range(6):
            code, out, err = run(PRE, self.spawn_payload(), bad)
            self.assertEqual(code, 0)
            self.assertIsNone(self.decision(out), "a spawn was denied although no brain could count it")
            self.assertEqual(err, "", "the hook must say nothing about the brain")


class SessionStart(unittest.TestCase):
    def test_reports_an_unfinished_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            run_dir = root / "docs" / "gentic" / "2026-01-01-demo-run"
            run_dir.mkdir(parents=True)
            (run_dir / "progress.md").write_text("## Phases\n- [x] 1 Scout\n- [ ] 2 Interview\n")
            code, out, err = run(SESSION, {
                "hook_event_name": "SessionStart", "how": "startup", "cwd": str(root),
                "session_id": "sess-1",
            }, brain=str(root / "brain.sqlite"))
            self.assertEqual(code, 0, err)
            self.assertIn("demo-run", out)

    def test_silent_when_every_run_is_finished(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            run_dir = root / "docs" / "gentic" / "2026-01-01-finished"
            run_dir.mkdir(parents=True)
            (run_dir / "progress.md").write_text("## Phases\n- [x] 1 Scout\n- [x] 2 Interview\n")
            self.assertEqual(run(SESSION, {
                "hook_event_name": "SessionStart", "how": "startup", "cwd": str(root),
            }, brain=str(root / "brain.sqlite"))[1].strip(), "")

    def test_silent_outside_a_git_repository(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, err = run(SESSION, {
                "hook_event_name": "SessionStart", "how": "startup", "cwd": d,
            }, brain=str(Path(d) / "brain.sqlite"))
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), "")
            self.assertNotIn("Traceback", err)


class Degradation(unittest.TestCase):
    def test_both_survive_empty_and_malformed_stdin(self):
        for script in (GUARD, SESSION):
            for payload in ("", "{nope"):
                with self.subTest(script=script.name, payload=payload):
                    proc = subprocess.run(
                        [sys.executable, str(script)], input=payload,
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(proc.returncode, 0)
                    self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
