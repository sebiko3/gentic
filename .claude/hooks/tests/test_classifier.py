#!/usr/bin/env python3
"""Contract tests for the UserPromptSubmit intent classifier.

Runs the hook as a real subprocess, exactly as Claude Code does: JSON on stdin,
assert on exit code and stdout. A trivial prompt must produce *no* output at all —
false positives here turn the routing directive into ambient noise.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "user_prompt_submit.py"

# Long enough to trip the length rule on its own (>= 240 chars).
LONG_PROMPT = (
    "I want to reorganise how the reporting module pulls its data, because right now "
    "each report re-queries the warehouse independently and the dashboard takes a very "
    "long time to load for larger accounts, so I would like the queries batched and "
    "cached somewhere sensible instead."
)

TRIVIAL = [
    "fix typo in README",
    "what does this function do?",
    "how do I run the tests?",
    "bump the version to 1.2.0",
    "add a docstring to parse_config",
    "why is this returning None?",
    "delete the temp file",
]

NON_TRIVIAL = [
    "/gentic add rate limiting",
    "Add user authentication across all API routes and then migrate the existing sessions",
    "refactor every service to use the new secure token store",
    "make the export pipeline faster and more robust, then deploy it",
    "rewrite the billing module to handle production payment retries",
    LONG_PROMPT,
]

RESUME = [
    "resume the auth work",
    "continue where we left off yesterday",
]


def run_hook(prompt, cwd=None):
    """Invoke the hook the way Claude Code does. Returns (exit_code, stdout)."""
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "session_id": "test-session",
        "cwd": cwd or tempfile.gettempdir(),
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.returncode, proc.stdout, proc.stderr


def routed(stdout):
    """True when the hook injected a routing directive."""
    return "gentic" in stdout.lower()


class Classification(unittest.TestCase):
    def test_trivial_prompts_produce_no_output(self):
        for prompt in TRIVIAL:
            with self.subTest(prompt=prompt):
                code, out, err = run_hook(prompt)
                self.assertEqual(code, 0, err)
                self.assertEqual(out.strip(), "", f"false positive on: {prompt!r}")

    def test_non_trivial_prompts_are_routed(self):
        for prompt in NON_TRIVIAL:
            with self.subTest(prompt=prompt):
                code, out, err = run_hook(prompt)
                self.assertEqual(code, 0, err)
                self.assertTrue(routed(out), f"missed routing on: {prompt!r}")

    def test_resume_prompts_are_routed(self):
        for prompt in RESUME:
            with self.subTest(prompt=prompt):
                code, out, err = run_hook(prompt)
                self.assertEqual(code, 0, err)
                self.assertTrue(routed(out), f"missed resume routing on: {prompt!r}")


class Contract(unittest.TestCase):
    def test_never_blocks(self):
        for prompt in TRIVIAL + NON_TRIVIAL + RESUME:
            with self.subTest(prompt=prompt):
                self.assertEqual(run_hook(prompt)[0], 0)

    def test_output_is_valid_json_when_present(self):
        for prompt in NON_TRIVIAL:
            with self.subTest(prompt=prompt):
                out = run_hook(prompt)[1]
                json.loads(out)

    def test_injected_block_stays_under_1200_chars(self):
        for prompt in NON_TRIVIAL + RESUME:
            with self.subTest(prompt=prompt):
                out = run_hook(prompt)[1]
                context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
                self.assertLess(len(context), 1200)

    def test_survives_empty_stdin(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK)], input="", capture_output=True, text=True, timeout=15
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", proc.stderr)

    def test_survives_malformed_json(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="{not json",
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", proc.stderr)

    def test_survives_missing_cwd_and_prompt(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"hook_event_name": "UserPromptSubmit"}),
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", proc.stderr)

    def test_runs_outside_a_git_repository(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, err = run_hook("refactor every service to use the new secure token store", cwd=d)
            self.assertEqual(code, 0)
            self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main(verbosity=1)
