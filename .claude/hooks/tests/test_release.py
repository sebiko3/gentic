#!/usr/bin/env python3
"""Contract tests for the release lane helper, `lib/release.py`.

Every test drives the real helper through a fake `gh` placed first on PATH: it replays canned
check lists, logs and PR views, records its argv, and never touches GitHub. The live lane is
exercised once per run, by hand, against a real pull request — never here.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parents[1]
HELPER = HOOKS / "lib" / "release.py"

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
argv = sys.argv[1:]
with open(os.environ["FAKE_GH_ARGV"], "a") as handle:
    handle.write(json.dumps(argv) + "\n")
def out(text):
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
if argv[:2] == ["pr", "checks"]:
    source = Path(os.environ["FAKE_GH_CHECKS"])
    if source.is_dir():
        counter = Path(os.environ["FAKE_GH_COUNTER"])
        k = int(counter.read_text()) + 1 if counter.exists() else 1
        counter.write_text(str(k))
        candidates = sorted(source.glob("checks.*.json"), key=lambda p: int(p.stem.split(".")[1]))
        source = candidates[min(k, len(candidates)) - 1]
    text = source.read_text().strip()
    if text == "none":
        sys.stderr.write("no checks reported on the 'x' branch\n"); sys.exit(1)
    if text == "broken":
        sys.stderr.write("HTTP 502: bad gateway\n"); sys.exit(1)
    out(text); sys.exit(0)
if argv[:2] == ["pr", "view"]:
    out(os.environ.get("FAKE_GH_VIEW") or json.dumps({"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "headRefName": "b"})); sys.exit(0)
if argv[:2] == ["repo", "view"]:
    out(json.dumps({"nameWithOwner": os.environ.get("FAKE_GH_REPO", "owner/repo")})); sys.exit(0)
if argv[:2] == ["run", "view"]:
    out(Path(os.environ["FAKE_GH_LOG"]).read_text()); sys.exit(0)
if argv[:2] == ["pr", "merge"]:
    sys.exit(int(os.environ.get("FAKE_GH_MERGE_EXIT", "0")))
if argv[:2] == ["auth", "status"]:
    out("Token scopes: 'repo', 'workflow'"); sys.exit(0)
sys.stderr.write("fake gh: unknown " + " ".join(argv) + "\n"); sys.exit(9)
'''

LINK = "https://github.com/owner/repo/actions/runs/123456/job/7890"


def checks(*buckets):
    return json.dumps([{"name": f"check-{i}", "state": b.upper(), "bucket": b, "link": LINK, "workflow": "gentic"}
                       for i, b in enumerate(buckets)])


class ReleaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="release-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        fake = self.bin / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.argv_log = self.tmp / "argv.jsonl"
        self.checks_file = self.tmp / "checks.json"
        self.checks_file.write_text(checks("pass"))
        self.log = self.tmp / "log.txt"
        self.log.write_text("\n".join(f"line {i}" for i in range(1, 101)) + "\n")
        self.trust = self.tmp / "trusted-projects"
        self.trust.write_text("")
        self.repo = self.tmp / "proj"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / "CLAUDE.md").write_text("# proj\n")

    def grant(self, *words, trusted=True):
        (self.repo / "CLAUDE.md").write_text("# proj\n\n## gentic authorizations\n" + "".join(f"- {w}\n" for w in words))
        self.trust.write_text(str(self.repo.resolve()) + "\n" if trusted else "")

    def run_helper(self, *args, env=None, checks_source=None):
        environ = dict(os.environ)
        environ.update({
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_GH_ARGV": str(self.argv_log),
            "FAKE_GH_CHECKS": str(checks_source or self.checks_file),
            "FAKE_GH_COUNTER": str(self.tmp / "counter"),
            "FAKE_GH_LOG": str(self.log),
            "GENTIC_TRUST": str(self.trust),
        })
        environ.update(env or {})
        return subprocess.run([sys.executable, str(HELPER), *args], cwd=str(self.repo), env=environ,
                              text=True, capture_output=True, timeout=120)

    def argvs(self):
        if not self.argv_log.exists():
            return []
        return [json.loads(line) for line in self.argv_log.read_text().splitlines() if line.strip()]


class Checks(ReleaseCase):
    def test_checks_reports_buckets_and_exit_codes(self):
        proc = self.run_helper("checks", "--pr", "2")
        self.assertEqual(proc.returncode, 0, f"checks did not run: {proc.stderr}")
        self.assertIn("pass: 1  fail: 0  pending: 0  skipping: 0  cancel: 0", proc.stdout)
        self.checks_file.write_text(checks("pass", "fail"))
        self.assertEqual(self.run_helper("checks", "--pr", "2").returncode, 1)
        self.checks_file.write_text(checks("pass", "pending"))
        self.assertEqual(self.run_helper("checks", "--pr", "2").returncode, 2)
        self.checks_file.write_text("none")
        self.assertEqual(self.run_helper("checks", "--pr", "2").returncode, 3)
        self.checks_file.write_text("[]")
        self.assertEqual(self.run_helper("checks", "--pr", "2").returncode, 3, "an empty list must not be green")
        self.checks_file.write_text("broken")
        broken = self.run_helper("checks", "--pr", "2")
        self.assertEqual(broken.returncode, 6)
        self.assertIn("HTTP 502", broken.stderr)


class Wait(ReleaseCase):
    def sequence(self, *contents):
        folder = self.tmp / "seq"
        folder.mkdir(exist_ok=True)
        for i, content in enumerate(contents, 1):
            (folder / f"checks.{i}.json").write_text(content)
        return folder

    def test_wait_polls_until_settled(self):
        folder = self.sequence(checks("pending"), checks("pending"), checks("pass"))
        proc = self.run_helper("wait", "--pr", "2", "--timeout", "30", "--interval", "1", checks_source=folder)
        self.assertEqual(proc.returncode, 0, f"wait did not run: {proc.stderr}")
        self.assertEqual(sum(1 for a in self.argvs() if a[:2] == ["pr", "checks"]), 3)
        polls = [line for line in proc.stdout.splitlines() if "pass:" in line]
        self.assertEqual(len(polls), 3)
        for line in polls:
            self.assertRegex(line, r"^\s*\d+s  pass: ")

    def test_wait_times_out(self):
        folder = self.sequence(checks("pending"))
        proc = self.run_helper("wait", "--pr", "2", "--timeout", "1", "--interval", "1", checks_source=folder)
        self.assertEqual(proc.returncode, 4)

    def test_wait_stops_on_a_hard_error(self):
        folder = self.sequence("broken", checks("pass"))
        proc = self.run_helper("wait", "--pr", "2", "--timeout", "30", "--interval", "1", checks_source=folder)
        self.assertEqual(proc.returncode, 6)
        self.assertEqual(sum(1 for a in self.argvs() if a[:2] == ["pr", "checks"]), 1)


class FailedLogs(ReleaseCase):
    def test_failed_logs_prints_the_failing_job(self):
        self.checks_file.write_text(checks("pass", "fail"))
        proc = self.run_helper("failed-logs", "--pr", "2", "--lines", "3")
        self.assertEqual(proc.returncode, 0, f"failed-logs did not run: {proc.stderr}")
        self.assertIn("== check-1 (run 123456, job 7890)", proc.stdout)
        self.assertIn("line 100", proc.stdout)
        self.assertNotIn("line 96", proc.stdout, "more than --lines lines printed")
        self.assertIn(["run", "view", "123456", "--job", "7890", "--log-failed"], self.argvs())
        self.checks_file.write_text(json.dumps([{"name": "odd", "state": "FAILURE", "bucket": "fail", "link": "https://example.com/nope", "workflow": "w"}]))
        proc = self.run_helper("failed-logs", "--pr", "2")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no link for odd", proc.stderr)


class Merge(ReleaseCase):
    def merged_calls(self):
        return [a for a in self.argvs() if a[:2] == ["pr", "merge"]]

    def test_merge_refuses_without_a_grant(self):
        self.grant("merge-on-green", trusted=False)
        proc = self.run_helper("merge", "--pr", "2")
        self.assertEqual(proc.returncode, 1, "merge did not refuse")
        self.assertIn("not authorized: merge-on-green", proc.stderr)
        self.assertEqual(self.merged_calls(), [])

    def test_merge_refuses_a_foreign_repo(self):
        self.grant("merge-on-green")
        proc = self.run_helper("merge", "--pr", "2", "--repo", "other/place")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("foreign repository", proc.stderr)
        self.assertEqual(self.merged_calls(), [])

    def test_merge_refuses_a_non_open_pr(self):
        self.grant("merge-on-green")
        proc = self.run_helper("merge", "--pr", "2", env={"FAKE_GH_VIEW": json.dumps({"state": "MERGED", "isDraft": False, "mergeable": "UNKNOWN"})})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("pr not mergeable", proc.stderr)
        self.assertEqual(self.merged_calls(), [])

    def test_merge_refuses_when_checks_are_not_green(self):
        self.grant("merge-on-green")
        self.checks_file.write_text(checks("fail"))
        proc = self.run_helper("merge", "--pr", "2")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("checks not green", proc.stderr)
        self.assertEqual(self.merged_calls(), [])

    def test_merge_merges_when_granted_and_green(self):
        self.grant("merge-on-green")
        proc = self.run_helper("merge", "--pr", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "merged", "stdout must carry only the documented line")
        self.assertIn(["pr", "merge", "2", "--merge"], self.merged_calls())


class Hygiene(unittest.TestCase):
    def test_harness_registers_release_suite(self):
        text = (HOOKS / "tests" / "run.sh").read_text(encoding="utf-8")
        suites = next(line for line in text.splitlines() if line.startswith("for suite in"))
        self.assertIn("test_release", suites)

    def test_workflow_runs_the_harness_and_no_evals(self):
        path = REPO / ".github" / "workflows" / "gentic.yml"
        self.assertTrue(path.is_file(), ".github/workflows/gentic.yml missing")
        text = path.read_text(encoding="utf-8")
        for needle in (".claude/hooks/tests/run.sh", "ubuntu-latest", "actions/checkout@v4", "actions/setup-python@v5"):
            self.assertIn(needle, text)
        for forbidden in ("evals/run.py", "permissions:", "concurrency:", "timeout-minutes", "paths"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
