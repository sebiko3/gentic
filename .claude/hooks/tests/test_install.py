#!/usr/bin/env python3
"""Contract tests for install.sh.

The installer is the one destructive-capable component in this setup: it writes into the
user's live ~/.claude. Every test here therefore runs against a temporary CLAUDE_HOME, which
is also why the installer must accept that override at all.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INSTALL = REPO / "install.sh"


def run(*args, dest=None):
    env = dict(os.environ)
    if dest is not None:
        env["CLAUDE_HOME"] = str(dest)
    return subprocess.run(
        ["bash", str(INSTALL), *args], cwd=REPO, env=env, text=True, capture_output=True
    )


class InstallContract(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp(prefix="claude-home-"))
        self.addCleanup(shutil.rmtree, self.dest, True)

    def test_installer_exists_and_is_bash(self):
        self.assertTrue(INSTALL.is_file(), f"{INSTALL} missing")
        self.assertTrue(INSTALL.read_text().startswith("#!"), "no shebang")

    def test_copies_every_owned_tree(self):
        result = run(dest=self.dest)
        self.assertEqual(result.returncode, 0, result.stderr)
        for rel in (
            "hooks/stop.py",
            "hooks/lib/common.py",
            "hooks/tests/run.sh",
            "commands/ship.md",
            "skills/gentic/SKILL.md",
            "skills/gentic/ROUTING.md",
            "skills/gentic-execute/SKILL.md",
        ):
            self.assertTrue((self.dest / rel).is_file(), f"{rel} not installed")

    def test_source_list_includes_the_brain(self):
        """The brain ships as three files; an installer that misses one leaves a phase skill
        pointing at a CLI that is not there — the `ROUTING.md` orphan class again."""
        result = run("--check", dest=self.dest)
        for rel in ("hooks/lib/brain.py", "hooks/tests/test_brain.py", "skills/gentic-brain/SKILL.md"):
            self.assertIn(rel, result.stdout, f"installer source list lacks {rel}")

    def test_run_sh_stays_executable(self):
        run(dest=self.dest)
        self.assertTrue(os.access(self.dest / "hooks/tests/run.sh", os.X_OK))

    def test_second_run_changes_nothing(self):
        run(dest=self.dest)
        second = run(dest=self.dest)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertRegex(second.stdout, r"\b0 (file|change)", second.stdout)

    def test_check_passes_when_synced(self):
        run(dest=self.dest)
        check = run("--check", dest=self.dest)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_check_fails_and_names_the_drifted_file(self):
        run(dest=self.dest)
        drifted = self.dest / "hooks/stop.py"
        drifted.write_text(drifted.read_text() + "\n# drift\n")
        check = run("--check", dest=self.dest)
        self.assertNotEqual(check.returncode, 0, "drift went undetected")
        self.assertIn("stop.py", check.stdout + check.stderr)

    def test_check_reports_a_missing_file_as_drift(self):
        run(dest=self.dest)
        (self.dest / "commands/ship.md").unlink()
        check = run("--check", dest=self.dest)
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("ship.md", check.stdout + check.stderr)

    def test_never_deletes_what_it_does_not_own(self):
        foreign_skill = self.dest / "skills/zcontext/SKILL.md"
        foreign_skill.parent.mkdir(parents=True)
        foreign_skill.write_text("not ours\n")
        session = self.dest / "sessions/abc.json"
        session.parent.mkdir(parents=True)
        session.write_text("{}\n")
        stray = self.dest / "agents/hand-written.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("user's own agent\n")

        run(dest=self.dest)

        self.assertTrue(foreign_skill.is_file(), "foreign skill destroyed")
        self.assertEqual(foreign_skill.read_text(), "not ours\n")
        self.assertTrue(session.is_file(), "session data destroyed")
        self.assertTrue(stray.is_file(), "user's own agent destroyed")

    def test_source_contains_no_recursive_destruction(self):
        """No rm -rf and no rsync --delete anywhere in the installer."""
        source = INSTALL.read_text()
        offenders = [
            line.strip()
            for line in source.splitlines()
            if re.search(r"rm\s+-[a-z]*r[a-z]*f|rsync[^\n]*--delete", line)
            and not line.strip().startswith("#")
        ]
        self.assertEqual(offenders, [], f"destructive command in installer: {offenders}")

    def test_refuses_a_destination_that_is_not_a_directory(self):
        target = self.dest / "afile"
        target.write_text("x")
        result = run(dest=target)
        self.assertNotEqual(result.returncode, 0, "installed over a regular file")

    def test_does_not_install_untracked_files(self):
        """The installer must ship what the repo tracks, not whatever is lying in the tree.

        Claude Code writes project-scoped permission grants to .claude/settings.local.json.
        Copying that to ~/.claude promotes them to machine scope silently.
        """
        planted = REPO / ".claude" / "settings.local.json"
        planted.write_text('{"permissions": {"allow": ["Bash(rm:*)"]}}\n')
        self.addCleanup(planted.unlink, True)
        stray = REPO / ".claude" / "agents" / ".DS_Store"
        stray.write_bytes(b"\x00")
        self.addCleanup(stray.unlink, True)

        run(dest=self.dest)

        self.assertFalse((self.dest / "settings.local.json").exists(),
                         "untracked local settings were promoted to user scope")
        self.assertFalse((self.dest / "agents/.DS_Store").exists(),
                         "untracked junk was installed")

    def test_never_installs_a_settings_file_even_if_tracked(self):
        """settings.json is machine state (theme, marketplaces), never repo-shipped."""
        source = INSTALL.read_text()
        self.assertRegex(source, r"settings", "installer does not mention settings at all")
        run(dest=self.dest)
        for name in ("settings.json", "settings.local.json"):
            self.assertFalse((self.dest / name).exists(), f"{name} must never be installed")

    def test_warns_when_hooks_are_not_registered(self):
        """Hooks copied but unregistered do nothing. That must never be silent."""
        result = run(dest=self.dest)
        combined = result.stdout + result.stderr
        self.assertIn("hooks", combined.lower())
        self.assertRegex(combined, r"not registered|inert|will not run|won't run",
                         "install said nothing about the hooks being unregistered")
        self.assertIn("PreToolUse", combined, "no concrete settings block was printed")

    def test_stays_quiet_when_hooks_are_already_registered(self):
        (self.dest).mkdir(parents=True, exist_ok=True)
        (self.dest / "settings.json").write_text(
            '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]}}\n')
        result = run(dest=self.dest)
        self.assertNotIn("PreToolUse", result.stdout + result.stderr,
                         "nagged about hooks that are already registered")

    def test_does_not_install_build_artefacts(self):
        run(dest=self.dest)
        junk = [str(p) for p in self.dest.rglob("*") if "__pycache__" in p.parts or p.suffix == ".pyc"]
        self.assertEqual(junk, [], f"artefacts installed: {junk}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
