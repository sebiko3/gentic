#!/usr/bin/env python3
"""Contract tests for the destructive-command guard and the session resume notice."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
GUARD = HOOKS / "pre_tool_use.py"
SESSION = HOOKS / "session_start.py"


def run(script, payload, state_dir=None):
    env = dict(os.environ)
    if state_dir:
        env["CLAUDE_HOOK_STATE_DIR"] = state_dir
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
            }, state_dir=str(root / "state"))
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
            }, state_dir=str(root / "state"))[1].strip(), "")

    def test_silent_outside_a_git_repository(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, err = run(SESSION, {
                "hook_event_name": "SessionStart", "how": "startup", "cwd": d,
            }, state_dir=d)
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
