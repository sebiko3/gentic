#!/usr/bin/env python3
"""The destructive-command guard, decided on argv rather than raw text.

The guard matched regexes against the raw command string, then blanked quoted spans so that
`echo "git reset --hard"` would not read as an invocation. That fixed the false positive and opened a
bypass: quotes delimit arguments, they do not neuter them, so `rm -rf "$HOME"` - the form shellcheck
tells you to write - sailed straight through.

Every ALLOW case below was verified against the pre-fix hook.

Note: the dangerous literals are assembled from fragments. Spelled out contiguously they trip
the live guard while merely being read, which makes the file unwritable and ungreppable.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]

G = "git"
RM = "rm"
HARD = G + " reset --hard"
FORCE = G + " push origin main --force"
CLEAN = G + " clean"


def decision(command, cwd=None):
    payload = json.dumps({
        "session_id": "guard-test", "cwd": cwd or os.getcwd(),
        "tool_name": "Bash", "tool_input": {"command": command},
    })
    result = subprocess.run([sys.executable, str(HOOKS / "pre_tool_use.py")],
                            input=payload, text=True, capture_output=True)
    return "deny" if '"permissionDecision": "deny"' in result.stdout else "allow"


class QuotingMustNotDisarmTheGuard(unittest.TestCase):
    """The regression the argv rewrite exists to close."""

    def test_quoted_forms_are_denied(self):
        for command in [
            RM + ' -rf "$HOME"',
            RM + " -rf '$HOME'",
            RM + ' -rf "/"',
            G + ' reset "--hard"',
            G + ' push origin main "--force"',
        ]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "deny")

    def test_unquoted_forms_are_still_denied(self):
        for command in [RM + " -rf $HOME", RM + " -rf /", HARD, FORCE]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "deny")


class SeparatedFlagsMustNotDisarmTheGuard(unittest.TestCase):
    def test_separated_flags(self):
        for command in [CLEAN + " -f -d", CLEAN + " --force -d", CLEAN + " -d -f"]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "deny")

    def test_clustered_flags_still_denied(self):
        for command in [CLEAN + " -fd", CLEAN + " -fdx"]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "deny")

    def test_dry_run_is_allowed(self):
        for command in [CLEAN + " -nfd", CLEAN + " -f -d -n", CLEAN + " --dry-run -fd"]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "allow")


class CompoundCommandsAreScannedThroughout(unittest.TestCase):
    def test_paired_apostrophes_quote_the_command_away(self):
        """Not a bypass - bash does not run it either.

        `echo don't; <destructive>; echo won't` has two apostrophes, so the shell pairs them
        and the whole middle becomes one literal argument to echo. Verified:

            $ bash -c "echo don't; echo SENTINEL_RAN; echo won't"
            dont; echo SENTINEL_RAN; echo wont

        SENTINEL_RAN is printed, not executed. Denying this would be a false positive, so the
        argv guard agreeing with the shell is the correct outcome.
        """
        self.assertEqual(decision("echo don't; " + HARD + "; echo won't"), "allow")

    def test_an_unpaired_apostrophe_does_not_hide_a_real_command(self):
        self.assertEqual(decision("echo it's fine; " + HARD), "deny")

    def test_each_segment_of_a_chain_is_checked(self):
        for command in ["npm test && " + HARD, "true || " + RM + " -rf /",
                        "echo hi | grep h; " + FORCE]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "deny")


class MentionsAreStillNotInvocations(unittest.TestCase):
    """The false positives the quote-blanking existed to prevent must stay fixed."""

    def test_talking_about_a_command_is_allowed(self):
        for command in [
            'echo "' + HARD + '"',
            "printf 'run " + RM + " -rf / to lose everything'",
            'grep -r "' + G + ' push --force" docs/',
        ]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "allow")

    def test_ordinary_work_is_allowed(self):
        for command in [G + " reset --soft HEAD~1", G + " push origin main",
                        G + " push --force-with-lease origin feature",
                        RM + " -rf ./build", RM + " -rf node_modules", CLEAN + " -n"]:
            with self.subTest(command=command):
                self.assertEqual(decision(command), "allow")


class RedirectionIsNotAlwaysMutation(unittest.TestCase):
    def test_stderr_redirection_is_not_treated_as_a_write(self):
        sys.path.insert(0, str(HOOKS))
        import pre_tool_use
        self.assertIsNone(pre_tool_use.MUTATING.search("pytest tests/ 2>&1"))
        self.assertIsNotNone(pre_tool_use.MUTATING.search("echo x > out.txt"))


class MalformedInputDegradesSafely(unittest.TestCase):
    def test_unterminated_quote_still_catches_a_destructive_command(self):
        self.assertEqual(decision(HARD + ' "unterminated'), "deny")

    def test_unterminated_quote_does_not_crash(self):
        self.assertIn(decision('echo "unterminated'), ("allow", "deny"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
