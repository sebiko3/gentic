#!/usr/bin/env python3
"""Project-scoped branch and commit naming.

gentic used to name every branch `gentic/<slug>` and every commit `gentic(<slug>): ...`, in
every repository it ran in, because those project rules had been promoted to machine-wide ones.
A project with its own `feat/` convention got gentic's instead.

The contract under test lives in the run's masterprompt; the table in
`test_the_documented_output_table` is that contract, transcribed.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HELPER = REPO / ".claude" / "hooks" / "lib" / "project_conventions.py"


def helper(*args, root=None, env=None):
    cmd = [sys.executable, str(HELPER), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    result = subprocess.run(cmd, text=True, capture_output=True,
                            env=env if env is not None else dict(os.environ))
    return result


def git(repo, *args, allow_fail=False):
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if not allow_fail:
        assert result.returncode == 0, result.stderr
    return result


def make_repo(branches=(), claude_md=None, commit=True):
    path = Path(tempfile.mkdtemp(prefix="conv-"))
    subprocess.run(["git", "init", "-b", "main", str(path)], capture_output=True)
    if claude_md is not None:
        (path / "CLAUDE.md").write_text(claude_md)
    if commit:
        # Never depend on ambient git config: a fresh machine has no user.name.
        git(path, "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "--allow-empty", "-m", "init")
        for branch in branches:
            git(path, "branch", branch)
    return path


class ThisRepositoryIsAdopted(unittest.TestCase):
    def test_branch_keeps_the_gentic_prefix(self):
        self.assertEqual(helper("branch", "demo-slug", root=REPO).stdout.strip(),
                         "gentic/demo-slug")

    def test_commit_keeps_the_gentic_wrapper(self):
        self.assertEqual(helper("commit", "demo-slug", "did a thing", root=REPO).stdout.strip(),
                         "gentic(demo-slug): did a thing")

    def test_adoption_survives_git_being_unavailable(self):
        """Adoption is decided before, and independently of, any git call.

        Fail-open to a bare slug would silently change this repo's naming whenever git
        hiccups - the one regression that would never show up in a happy-path test.
        """
        env = dict(os.environ, PATH="")
        self.assertEqual(helper("branch", "demo-slug", root=REPO, env=env).stdout.strip(),
                         "gentic/demo-slug")


class AnUnadoptedProjectKeepsItsOwnConvention(unittest.TestCase):
    def test_a_dominant_prefix_wins(self):
        repo = make_repo(["feat/a", "feat/b", "feat/c", "fix/d", "integration/e"])
        self.addCleanup(shutil.rmtree, repo, True)
        self.assertEqual(helper("branch", "x", root=repo).stdout.strip(), "feat/x")

    def test_commit_subjects_lose_the_wrapper(self):
        repo = make_repo(["feat/a", "feat/b"])
        self.addCleanup(shutil.rmtree, repo, True)
        out = helper("commit", "x", "did a thing", root=repo).stdout.strip()
        self.assertEqual(out, "did a thing")
        self.assertNotIn("gentic(", out)

    def test_a_claude_md_without_the_marker_is_not_adoption(self):
        repo = make_repo(["feat/a", "feat/b"], claude_md="# Project\n\nSome rules.\n")
        self.addCleanup(shutil.rmtree, repo, True)
        self.assertEqual(helper("branch", "x", root=repo).stdout.strip(), "feat/x")

    def test_the_marker_makes_a_project_adopted(self):
        repo = make_repo(["feat/a", "feat/b"],
                         claude_md="Runs execute on a `gentic/<slug>` branch.\n")
        self.addCleanup(shutil.rmtree, repo, True)
        self.assertEqual(helper("branch", "x", root=repo).stdout.strip(), "gentic/x")


class NoUsablePrefixMeansNoPrefix(unittest.TestCase):
    def assert_bare(self, repo):
        self.addCleanup(shutil.rmtree, repo, True)
        self.assertEqual(helper("branch", "x", root=repo).stdout.strip(), "x")

    def test_unprefixed_branches(self):
        self.assert_bare(make_repo(["websockets", "android-port"]))

    def test_a_tie_yields_nothing(self):
        self.assert_bare(make_repo(["feat/a", "fix/b"]))

    def test_a_single_occurrence_is_below_the_threshold(self):
        self.assert_bare(make_repo(["feat/a"]))

    def test_a_repository_with_no_commits(self):
        self.assert_bare(make_repo(commit=False))

    def test_the_default_branch_is_excluded_from_the_census(self):
        self.assert_bare(make_repo(["feat/only"]))


class ItFailsOpen(unittest.TestCase):
    def test_a_directory_that_is_not_a_repository(self):
        plain = Path(tempfile.mkdtemp(prefix="plain-"))
        self.addCleanup(shutil.rmtree, plain, True)
        result = helper("branch", "x", root=plain)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "x")

    def test_a_root_that_does_not_exist(self):
        result = helper("branch", "x", root="/nonexistent/nowhere/at/all")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "x")

    def test_commit_returns_the_message_unchanged_on_failure(self):
        result = helper("commit", "x", "did a thing", root="/nonexistent/nowhere")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "did a thing")

    def test_no_traceback_ever_reaches_stderr(self):
        for root in ("/nonexistent/nowhere", tempfile.mkdtemp(prefix="plain2-")):
            with self.subTest(root=root):
                self.assertNotIn("Traceback", helper("branch", "x", root=root).stderr)


class AHostileCensusCannotReachGit(unittest.TestCase):
    """The prefix is fed to `git checkout -b`, so it is an injection surface.

    The masterprompt's DoD 7 asks for a fixture repository carrying branches like
    `a;rm -rf x/b` and `../evil/c`. That fixture cannot be built - git refuses the names
    itself:

        $ git branch '../evil/one'
        fatal: '../evil/one' is not a valid branch name
        $ git branch 'a;rm -rf x/one'
        fatal: 'a;rm -rf x/one' is not a valid branch name

    So the claim is true for a stronger reason than the one specified: git will not create such
    a ref, and if one arrived by another route the validator discards it. The guard is tested by
    injecting the census directly, since the end-to-end path is unreachable by construction.
    """

    def setUp(self):
        sys.path.insert(0, str(REPO / ".claude" / "hooks" / "lib"))
        import project_conventions
        self.mod = project_conventions

    def inject(self, branches):
        original = self.mod._branches
        self.mod._branches = lambda root: branches
        self.addCleanup(setattr, self.mod, "_branches", original)
        return self.mod.dominant_prefix(Path("/tmp"))

    def test_git_refuses_to_create_such_refs_at_all(self):
        repo = make_repo()
        self.addCleanup(shutil.rmtree, repo, True)
        for name in ("../evil/one", "a;rm -rf x/one"):
            with self.subTest(name=name):
                result = git(repo, "branch", name, allow_fail=True)
                self.assertNotEqual(result.returncode, 0, "git accepted a hostile ref name")

    def test_shell_metacharacters_are_discarded(self):
        self.assertIsNone(self.inject(["a;rm -rf x/one", "a;rm -rf x/two"]))

    def test_path_traversal_is_discarded(self):
        self.assertIsNone(self.inject(["../evil/one", "../evil/two"]))

    def test_a_plain_prefix_still_wins(self):
        self.assertEqual(self.inject(["feat/a", "feat/b"]), "feat")


class TheDocumentedContract(unittest.TestCase):
    def test_the_documented_output_table(self):
        adopted = make_repo(["feat/a", "feat/b"], claude_md="`gentic/<slug>`\n")
        prefixed = make_repo(["feat/a", "feat/b", "feat/c"])
        bare = make_repo(["websockets"])
        for repo in (adopted, prefixed, bare):
            self.addCleanup(shutil.rmtree, repo, True)
        cases = [
            (adopted,  "gentic/s", "gentic(s): m"),
            (prefixed, "feat/s",   "m"),
            (bare,     "s",        "m"),
        ]
        for repo, branch, commit in cases:
            with self.subTest(repo=repo.name):
                self.assertEqual(helper("branch", "s", root=repo).stdout.strip(), branch)
                self.assertEqual(helper("commit", "s", "m", root=repo).stdout.strip(), commit)

    def test_root_defaults_to_cwd_and_walks_up_to_the_repository(self):
        result = subprocess.run(
            [sys.executable, str(HELPER), "branch", "demo"],
            cwd=str(REPO / ".claude" / "hooks"), text=True, capture_output=True)
        self.assertEqual(result.stdout.strip(), "gentic/demo")

    def test_the_helper_embeds_no_dot_claude_path_literal(self):
        """run.sh:88 fails the build on one; the helper needs only "CLAUDE.md"."""
        import re
        offenders = [line for line in HELPER.read_text().splitlines()
                     if re.search(r'"[^"]*\.claude[^"]*"', line)]
        self.assertEqual(offenders, [], f"quoted .claude literal: {offenders}")


class Authorizations(unittest.TestCase):
    """Standing permissions: a grant in the project's CLAUDE.md counts only when the machine
    also trusts the project. A clone must never be able to grant itself."""

    GRANTS = "# Project\n\n## gentic authorizations\n- push\n- open-pr — CI is required here\n- Push\n\n## Other\n- merge-on-green\n"

    def setUp(self):
        self.trust = Path(tempfile.mkdtemp(prefix="trust-")) / "trusted-projects"

    def env(self, *roots):
        self.trust.write_text("".join(str(Path(r).resolve()) + "\n" for r in roots))
        return dict(os.environ, GENTIC_TRUST=str(self.trust))

    def test_authorized_reads_the_section(self):
        repo = make_repo(claude_md=self.GRANTS)
        env = self.env(repo)
        result = helper("authorized", "push", root=repo, env=env)
        self.assertEqual(result.returncode, 0, "authorized push")
        self.assertEqual(result.stdout.strip(), "yes")
        self.assertEqual(helper("authorized", "open-pr", root=repo, env=env).stdout.strip(), "yes")
        denied = helper("authorized", "merge-on-green", root=repo, env=env)
        self.assertEqual((denied.returncode, denied.stdout.strip()), (1, "no"))
        listed = helper("authorized", "--list", root=repo, env=env)
        self.assertEqual(listed.returncode, 0)
        self.assertEqual(listed.stdout, "push\nopen-pr\n")

    def test_authorized_fails_closed(self):
        repo = make_repo(claude_md=self.GRANTS)
        untrusted = helper("authorized", "push", root=repo, env=self.env())
        self.assertEqual(untrusted.returncode, 1, "untrusted must be a no")
        self.assertEqual(untrusted.stdout.strip(), "no")
        self.assertIn("not trusted", untrusted.stderr)
        no_section = make_repo(claude_md="# Project\n\nWe push often.\n")
        no_file = make_repo(claude_md=None)
        prose = make_repo(claude_md="## gentic authorizations\n\nWe allow push here.\n")
        env = self.env(repo, no_section, no_file, prose)   # all trusted; the section decides
        self.assertEqual(helper("authorized", "push", root=no_section, env=env).returncode, 1)
        self.assertEqual(helper("authorized", "push", root=no_file, env=env).returncode, 1)
        unknown = helper("authorized", "deploy", root=repo, env=env)
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("unknown action", unknown.stderr)
        self.assertEqual(helper("authorized", "push", root=prose, env=env).returncode, 1)

    def test_branch_and_commit_still_need_a_slug(self):
        repo = make_repo()
        self.assertEqual(helper("branch", root=repo).returncode, 2)
        self.assertEqual(helper("commit", root=repo).returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
