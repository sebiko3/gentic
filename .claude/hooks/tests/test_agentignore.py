#!/usr/bin/env python3
"""Tests for .agentignore parsing, matching, cascade resolution and enforcement."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))

from lib import agentignore  # noqa: E402

GUARD = HOOKS / "pre_tool_use.py"


def write_tree(root, files):
    """files: {relative path: contents}. Directories are created as needed."""
    for rel, contents in files.items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)


class Parser(unittest.TestCase):
    def parse(self, text):
        return agentignore.parse(text, base="/repo", source="/repo/.agentignore")

    def test_bare_pattern_denies_read_and_write(self):
        rules = self.parse("secrets/\n")
        self.assertEqual(rules[0].read, False)
        self.assertEqual(rules[0].write, False)

    def test_read_only_section(self):
        rules = self.parse("[read-only]\nvendor/\n")
        self.assertEqual((rules[0].read, rules[0].write), (True, False))

    def test_no_read_section(self):
        rules = self.parse("[no-read]\n.env\n")
        self.assertEqual((rules[0].read, rules[0].write), (False, True))

    def test_negation_reallows_both(self):
        rules = self.parse("secrets/\n!secrets/README.md\n")
        self.assertEqual((rules[1].read, rules[1].write), (True, True))

    def test_comments_and_blank_lines_ignored(self):
        self.assertEqual(len(self.parse("# a comment\n\n   \nsecrets/\n")), 1)

    def test_section_headers_are_case_insensitive(self):
        rules = self.parse("[READ-ONLY]\nvendor/\n")
        self.assertEqual((rules[0].read, rules[0].write), (True, False))

    def test_unknown_section_header_is_ignored_not_fatal(self):
        rules = self.parse("[nonsense]\nsecrets/\n")
        self.assertEqual(len(rules), 1)


class Patterns(unittest.TestCase):
    def verdict(self, patterns, path, base="/repo"):
        rules = agentignore.parse(patterns, base=base, source=f"{base}/.agentignore")
        return agentignore.resolve(rules, path)

    def test_directory_pattern_covers_contents(self):
        self.assertFalse(self.verdict("secrets/\n", "/repo/secrets/key.pem")["read"])

    def test_directory_pattern_covers_nested_contents(self):
        self.assertFalse(self.verdict("secrets/\n", "/repo/secrets/deep/inner/key.pem")["read"])

    def test_basename_glob_matches_at_any_depth(self):
        self.assertFalse(self.verdict("*.pem\n", "/repo/a/b/c/key.pem")["read"])

    def test_anchored_pattern_does_not_match_elsewhere(self):
        self.assertTrue(self.verdict("build/output.txt\n", "/repo/sub/build/output.txt")["read"])

    def test_anchored_pattern_matches_at_its_root(self):
        self.assertFalse(self.verdict("build/output.txt\n", "/repo/build/output.txt")["read"])

    def test_double_star_crosses_segments(self):
        self.assertFalse(self.verdict("src/**/generated.ts\n", "/repo/src/a/b/generated.ts")["read"])

    def test_leading_slash_anchors(self):
        self.assertFalse(self.verdict("/config.yml\n", "/repo/config.yml")["read"])
        self.assertTrue(self.verdict("/config.yml\n", "/repo/nested/config.yml")["read"])

    def test_last_matching_rule_wins(self):
        v = self.verdict("secrets/\n!secrets/README.md\n", "/repo/secrets/README.md")
        self.assertEqual((v["read"], v["write"]), (True, True))

    def test_unmatched_path_is_fully_allowed(self):
        v = self.verdict("secrets/\n", "/repo/src/app.py")
        self.assertEqual((v["read"], v["write"]), (True, True))

    def test_question_mark_matches_one_character(self):
        self.assertFalse(self.verdict("key?.pem\n", "/repo/key1.pem")["read"])


class Cascade(unittest.TestCase):
    def test_nearest_file_wins(self):
        with tempfile.TemporaryDirectory() as d:
            root = str(Path(d).resolve())
            write_tree(root, {
                ".git/HEAD": "ref: refs/heads/main\n",
                ".agentignore": "data/\n",
                "data/.agentignore": "!report.csv\n",
                "data/report.csv": "x",
                "data/secret.csv": "x",
            })
            self.assertTrue(agentignore.permissions_for(f"{root}/data/report.csv")["read"])
            self.assertFalse(agentignore.permissions_for(f"{root}/data/secret.csv")["read"])

    def test_no_agentignore_anywhere_allows_everything(self):
        with tempfile.TemporaryDirectory() as d:
            root = str(Path(d).resolve())
            write_tree(root, {".git/HEAD": "ref\n", "src/app.py": "x"})
            v = agentignore.permissions_for(f"{root}/src/app.py")
            self.assertEqual((v["read"], v["write"]), (True, True))

    def test_walk_stops_at_repo_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = str(Path(d).resolve())
            write_tree(root, {"outer.agentignore": "x", "repo/.git/HEAD": "ref\n", "repo/src/app.py": "x"})
            v = agentignore.permissions_for(f"{root}/repo/src/app.py")
            self.assertTrue(v["read"])

    def test_malformed_file_fails_open(self):
        with tempfile.TemporaryDirectory() as d:
            root = str(Path(d).resolve())
            write_tree(root, {".git/HEAD": "ref\n", ".agentignore": "[[[\x00\xff bad\n", "a.py": "x"})
            v = agentignore.permissions_for(f"{root}/a.py")
            self.assertEqual((v["read"], v["write"]), (True, True))


class Enforcement(unittest.TestCase):
    """Drives the real hook as a subprocess, exactly as Claude Code does."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.root = str(Path(self.dir).resolve())
        write_tree(self.root, {
            ".git/HEAD": "ref: refs/heads/main\n",
            ".agentignore": (
                "secrets/\n"
                "*.pem\n"
                "\n"
                "[read-only]\n"
                "vendor/\n"
                "\n"
                "[no-read]\n"
                ".env.production\n"
            ),
            "secrets/key.txt": "x",
            "vendor/lib.js": "x",
            ".env.production": "x",
            "src/app.py": "x",
        })

    def call(self, tool, tool_input):
        proc = subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps({
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": tool_input,
                "cwd": self.root,
                "session_id": "ai-test",
            }),
            capture_output=True, text=True, timeout=15,
        )
        decision = None
        if proc.stdout.strip():
            decision = json.loads(proc.stdout).get("hookSpecificOutput", {}).get("permissionDecision")
        return proc.returncode, decision, proc.stdout

    def test_read_denied(self):
        code, decision, _ = self.call("Read", {"file_path": f"{self.root}/secrets/key.txt"})
        self.assertEqual(code, 0)
        self.assertEqual(decision, "deny")

    def test_write_denied(self):
        for tool in ("Write", "Edit"):
            with self.subTest(tool=tool):
                self.assertEqual(self.call(tool, {"file_path": f"{self.root}/secrets/key.txt"})[1], "deny")

    def test_read_only_path(self):
        self.assertIsNone(self.call("Read", {"file_path": f"{self.root}/vendor/lib.js"})[1])
        self.assertEqual(self.call("Edit", {"file_path": f"{self.root}/vendor/lib.js"})[1], "deny")

    def test_no_read_section_allows_write_denies_read(self):
        self.assertEqual(self.call("Read", {"file_path": f"{self.root}/.env.production"})[1], "deny")
        self.assertIsNone(self.call("Write", {"file_path": f"{self.root}/.env.production"})[1])

    def test_basename_glob_enforced(self):
        self.assertEqual(self.call("Read", {"file_path": f"{self.root}/src/server.pem"})[1], "deny")

    def test_bash_read_denied(self):
        for command in ("cat secrets/key.txt", "head -5 secrets/key.txt", f"cat {self.root}/secrets/key.txt"):
            with self.subTest(command=command):
                self.assertEqual(self.call("Bash", {"command": command})[1], "deny")

    def test_bash_write_vs_read(self):
        self.assertIsNone(self.call("Bash", {"command": "cat vendor/lib.js"})[1])
        self.assertEqual(self.call("Bash", {"command": "rm vendor/lib.js"})[1], "deny")

    def test_no_false_positives(self):
        for tool, tool_input in [
            ("Read", {"file_path": f"{self.root}/src/app.py"}),
            ("Edit", {"file_path": f"{self.root}/src/app.py"}),
            ("Write", {"file_path": f"{self.root}/src/new.py"}),
            ("Bash", {"command": "npm test"}),
            ("Bash", {"command": "git status"}),
            ("Bash", {"command": "cat src/app.py"}),
            ("Bash", {"command": "ls -la"}),
            ("Bash", {"command": "echo 'secrets are important'"}),
            ("Bash", {"command": "python3 -c 'print(1)'"}),
        ]:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertIsNone(self.call(tool, tool_input)[1], f"false positive: {tool_input}")

    def test_destructive_git_guard_still_fires(self):
        self.assertEqual(self.call("Bash", {"command": "git push --force origin main"})[1], "deny")

    def test_inert_without_agentignore(self):
        os.remove(Path(self.root) / ".agentignore")
        for tool, tool_input in [
            ("Read", {"file_path": f"{self.root}/secrets/key.txt"}),
            ("Edit", {"file_path": f"{self.root}/secrets/key.txt"}),
            ("Bash", {"command": "cat secrets/key.txt"}),
        ]:
            with self.subTest(tool=tool):
                self.assertIsNone(self.call(tool, tool_input)[1])

    def test_malformed_fails_open(self):
        (Path(self.root) / ".agentignore").write_text("[[[ \x00 bad\n")
        code, decision, _ = self.call("Read", {"file_path": f"{self.root}/secrets/key.txt"})
        self.assertEqual(code, 0)
        self.assertIsNone(decision)

    def test_denial_reason_names_the_file_and_rule(self):
        _, _, out = self.call("Read", {"file_path": f"{self.root}/secrets/key.txt"})
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn(".agentignore", reason)
        self.assertIn("secrets/", reason)


class OversizedTokens(unittest.TestCase):
    """A pasted code blob is not a path.

    Reported from live use: a Bash command carrying a multi-line JSX blob produced
    `[Errno 63] File name too long`. `Path.resolve()` is lenient on macOS but `is_dir()`
    stats, and paths over PATH_MAX (1024) raise. Two consequences: a noisy hook error, and
    — worse — the raised exception aborted the token scan, so any genuinely protected path
    later in the same command went unchecked.
    """

    BLOB = (
        "                {messages?.map((message) =>\n"
        "                  message.role === user ? (\n"
        "                    <UserBubble key={message.id} content={message.content} />\n"
    ) * 12

    def test_permissions_for_oversized_path_does_not_raise(self):
        candidate = Path("/Users/nobody/project") / self.BLOB
        verdict = agentignore.permissions_for(candidate)
        self.assertEqual((verdict["read"], verdict["write"]), (True, True))

    def test_rules_for_oversized_path_does_not_raise(self):
        self.assertEqual(agentignore.rules_for(Path("/tmp") / self.BLOB), [])

    def test_path_tokens_skip_multiline_blobs(self):
        import pre_tool_use
        self.assertNotIn(self.BLOB, list(pre_tool_use.path_tokens(f'echo "{self.BLOB}"')))

    def test_path_tokens_skip_overlong_tokens(self):
        import pre_tool_use
        long_token = "a/" + ("b" * 5000)
        self.assertNotIn(long_token, list(pre_tool_use.path_tokens(f"cat {long_token}")))

    def test_path_tokens_still_yield_real_paths(self):
        import pre_tool_use
        self.assertIn("src/app.py", list(pre_tool_use.path_tokens("cat src/app.py")))


class OversizedEnforcement(Enforcement):
    """The blob must neither error nor mask a real violation in the same command."""

    def test_blob_command_produces_no_hook_error(self):
        command = 'git commit -m "' + OversizedTokens.BLOB + '"'
        proc = subprocess.run(
            [sys.executable, str(GUARD)],
            input=json.dumps({
                "hook_event_name": "PreToolUse", "tool_name": "Bash",
                "tool_input": {"command": command}, "cwd": self.root, "session_id": "blob",
            }),
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("hook error", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)

    def test_blob_does_not_mask_a_protected_path(self):
        command = 'echo "' + OversizedTokens.BLOB + '" && cat secrets/key.txt'
        self.assertEqual(self.call("Bash", {"command": command})[1], "deny")


class Docs(unittest.TestCase):
    def test_example_file_parses(self):
        example = HOOKS / "agentignore.example"
        self.assertTrue(example.exists(), "shipped example .agentignore missing")
        rules = agentignore.parse(example.read_text(), base="/repo", source=str(example))
        self.assertGreater(len(rules), 3)
        self.assertTrue(any(r.read is False for r in rules))
        self.assertTrue(any(r.read is True and r.write is False for r in rules))


if __name__ == "__main__":
    unittest.main(verbosity=1)
