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

    def test_does_not_install_build_artefacts(self):
        run(dest=self.dest)
        junk = [str(p) for p in self.dest.rglob("*") if "__pycache__" in p.parts or p.suffix == ".pyc"]
        self.assertEqual(junk, [], f"artefacts installed: {junk}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
