#!/usr/bin/env python3
"""Contract tests for the SQLite brain.

The brain is machine-wide state under the user's home, so every test here points
``GENTIC_BRAIN`` at a private temporary file — the same reason ``CLAUDE_HOOK_STATE_DIR``
exists for the session ledger. A test that forgets the override would write into the user's
real memory; the harness (``run.sh``) exports the variable for the same reason.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parents[1]
BRAIN = HOOKS / "lib" / "brain.py"
POST = HOOKS / "post_tool_use.py"
STOP = HOOKS / "stop.py"
SESSION_START = HOOKS / "session_start.py"


class BrainCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="brain-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "brain.sqlite"
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.repo = self.tmp / "proj-alpha"
        (self.repo / ".git").mkdir(parents=True)
        (self.repo / "src").mkdir()
        self.session = f"s-{uuid.uuid4().hex[:8]}"

    def env(self, **extra):
        env = dict(os.environ, GENTIC_BRAIN=str(self.db), CLAUDE_HOOK_STATE_DIR=str(self.state))
        env.pop("GENTIC_BRAIN_NO_FTS", None)
        env.update({k: str(v) for k, v in extra.items()})
        return env

    def brain(self, *args, cwd=None, **extra):
        return subprocess.run(
            [sys.executable, str(BRAIN), *args],
            cwd=str(cwd or self.repo), env=self.env(**extra),
            text=True, capture_output=True, timeout=30,
        )

    def ok(self, *args, **kw):
        proc = self.brain(*args, **kw)
        self.assertEqual(proc.returncode, 0, f"brain CLI did not run: {proc.stderr}")
        return proc.stdout

    def hook(self, script, payload, **extra):
        payload.setdefault("session_id", self.session)
        payload.setdefault("cwd", str(self.repo))
        proc = subprocess.run(
            [sys.executable, str(script)], input=json.dumps(payload),
            env=self.env(**extra), text=True, capture_output=True, timeout=30,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def bash_post(self, command, exit_code=0, **extra):
        return self.hook(POST, {
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}, "tool_output": {"exit_code": exit_code},
        }, **extra)

    def edit_post(self, path="src/app.py", **extra):
        return self.hook(POST, {
            "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(self.repo / path)},
        }, **extra)

    def stop(self, message, **extra):
        return self.hook(STOP, {"hook_event_name": "Stop", "last_assistant_message": message}, **extra)

    def rows(self, sql):
        if not self.db.exists():
            return []
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql)]


class NotesAndRecall(BrainCase):
    def assert_recall_works(self, **extra):
        self.ok("note", "calendar-dnd", "drag and drop needs pointer events on touch", **extra)
        self.ok("note", "unrelated", "the build cache lives under dist", **extra)
        out = self.ok("recall", "events pointer", **extra)
        self.assertIn("pointer events", out, "two-term recall did not find the note")
        self.assertNotIn("build cache", out, "recall returned an unrelated note")
        self.assertIn("pointer events", self.ok("recall", "calendar-dnd", **extra), "key is not searchable")

    def test_note_then_recall_finds_it(self):
        self.assert_recall_works()

    def test_recall_falls_back_to_like(self):
        self.assert_recall_works(GENTIC_BRAIN_NO_FTS="1")


class FreeSql(BrainCase):
    def test_sql_is_unrestricted_inside_the_brain(self):
        self.ok("sql", "create table scratch (x integer)")
        self.ok("sql", "insert into scratch values (1)")
        out = self.ok("sql", "select x from scratch")
        self.assertEqual(json.loads(out.strip()), {"x": 1})
        bad = self.brain("sql", "selec x from scratch")
        self.assertEqual(bad.returncode, 1, "a SQL error must exit 1")
        self.assertTrue(bad.stderr.strip(), "a SQL error must be reported on stderr")

    def test_sql_destructive_statement_leaves_a_backup(self):
        self.ok("sql", "create table scratch (x integer)")
        self.ok("sql", "insert into scratch values (1)")
        self.ok("sql", "DELETE FROM scratch")
        backup = Path(str(self.db) + ".bak")
        self.assertTrue(backup.exists(), "no .bak before a destructive statement")
        with sqlite3.connect(backup) as conn:
            self.assertEqual(conn.execute("select count(*) from scratch").fetchone()[0], 1,
                             "the backup does not hold the pre-delete state")


class HooksWriteEvents(BrainCase):
    def test_hooks_write_events_to_the_brain(self):
        self.bash_post("pytest tests/test_app.py -x", exit_code=1)
        red = self.rows("select * from events where kind = 'red'")
        self.assertEqual(len(red), 1, "no red event in brain")
        self.assertEqual(red[0]["project"], "proj-alpha")
        self.assertTrue(red[0]["detail"].startswith("pytest tests/test_app.py -x"[:40]))

        self.bash_post("pytest tests/test_app.py -x", exit_code=0)
        self.assertEqual(len(self.rows("select * from events where kind = 'verification'")), 1)

        self.bash_post('curl -H "Authorization: Bearer abc123" https://x.test && npm test', exit_code=0)
        latest = self.rows("select detail from events order by id desc limit 1")[0]["detail"]
        self.assertNotIn("abc123", latest, "secret stored verbatim")
        self.assertIn("***", latest)

        self.session = f"s-{uuid.uuid4().hex[:8]}"
        self.edit_post()
        code, _, _ = self.stop("Done — everything is passing.")
        self.assertEqual(code, 2, "the verification gate should still block")
        self.assertEqual(len(self.rows("select * from events where kind = 'gate_block'")), 1)
        self.assertEqual(len(self.rows("select * from events where kind = 'nudge_tdd'")), 1)

    def test_brain_failure_is_invisible_to_hooks(self):
        blocker = self.tmp / "blocker.txt"
        blocker.write_text("not a directory")
        bad = blocker / "deeper" / "brain.sqlite"

        code, out, err = self.bash_post("pytest -x", exit_code=1, GENTIC_BRAIN=bad)
        self.assertEqual(code, 0)
        self.assertNotIn("hook error", out)
        self.assertEqual(out, "", "post_tool_use must stay silent")
        self.assertEqual(err, "")

        self.edit_post(GENTIC_BRAIN=bad)
        code, out, err = self.stop("Still working on it.", GENTIC_BRAIN=bad)
        self.assertEqual(code, 0)
        self.assertNotIn("hook error", out)
        self.assertEqual(err, "")

        sys.path.insert(0, str(HOOKS))
        os.environ["GENTIC_BRAIN"] = str(bad)
        try:
            from lib import brain
            start = time.perf_counter()
            brain.record_event(str(self.repo), self.session, "red", "pytest -x")
            elapsed = time.perf_counter() - start
        finally:
            os.environ.pop("GENTIC_BRAIN", None)
            sys.path.remove(str(HOOKS))
        self.assertLess(elapsed, 0.089, "record_event took too long to give up")


class Preferences(BrainCase):
    def test_preference_needs_two_agreeing_user_decisions(self):
        self.ok("decide", "artifact-location", "in-repo", "--source", "user")
        first = self.brain("preference", "artifact-location")
        self.assertEqual((first.returncode, first.stdout), (1, ""), "one decision must not teach")
        self.ok("decide", "artifact-location", "in-repo", "--source", "user")
        self.assertEqual(self.ok("preference", "artifact-location").strip(), "in-repo")

        self.ok("decide", "branch-prefix", "feat", "--source", "default")
        self.ok("decide", "branch-prefix", "feat", "--source", "default")
        self.assertEqual(self.brain("preference", "branch-prefix").returncode, 1, "defaults must not teach")

        for value in ("A", "A", "B"):
            self.ok("decide", "changed-mind", value, "--source", "user")
        self.assertEqual(self.brain("preference", "changed-mind").returncode, 1, "a changed mind must win")


class Lessons(BrainCase):
    def test_lessons_recorded_and_summarised(self):
        self.ok("lesson", "--item", "D3 preference", "--rung", "1", "--points", "2",
                "--caught-by", "suite", "--cause", "off by one in the count")
        self.assertIn("D3 preference", self.ok("lessons"))
        stats = self.ok("stats")
        self.assertIn("suite: 1", stats)
        self.assertIn("points: 2", stats)

    def test_lessons_default_to_current_project(self):
        self.ok("lesson", "--item", "alpha-item", "--rung", "1", "--points", "1",
                "--caught-by", "live", "--cause", "x")
        self.ok("lesson", "--item", "beta-item", "--rung", "2", "--points", "2",
                "--caught-by", "review", "--cause", "y", "--project", "beta")
        scoped = self.ok("lessons")
        self.assertIn("alpha-item", scoped)
        self.assertNotIn("beta-item", scoped, "another project's lesson leaked")
        self.assertIn("beta-item", self.ok("lessons", "--all"))
        nogit = self.tmp / "nogit"
        nogit.mkdir()
        self.assertEqual(self.brain("lessons", cwd=nogit).returncode, 1, "no git root must exit 1")


class RunsAndStamps(BrainCase):
    def test_run_lifecycle_and_stamps(self):
        self.ok("run", "start", "my-run", "--goal", "prove the brain")
        self.ok("run", "finish", "my-run", "--outcome", "done")
        runs = self.rows("select * from runs")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["outcome"], "done")

        a = self.repo / "a.md"
        b = self.repo / "b.md"
        a.write_text("one")
        b.write_text("two")
        self.ok("stamp", "my-run", str(a), str(b))
        self.assertEqual(len(self.rows("select * from stamps")), 2)
        before = self.rows("select sha from stamps where path like '%a.md'")[0]["sha"]
        a.write_text("changed")
        self.ok("stamp", "my-run", str(a), str(b))
        stamps = self.rows("select * from stamps")
        self.assertEqual(len(stamps), 2, "re-stamping the same run must replace, not add")
        self.assertNotEqual(self.rows("select sha from stamps where path like '%a.md'")[0]["sha"], before)
        self.ok("stamp", "other-run", str(a))
        self.assertEqual(len(self.rows("select * from stamps")), 3, "a second run must add its own rows")


class SessionStart(BrainCase):
    def test_session_start_mentions_brain_when_it_has_something(self):
        payload = {"hook_event_name": "SessionStart"}
        _, out, _ = self.hook(SESSION_START, dict(payload))
        self.assertNotIn("brain:", out, "an empty brain must stay silent")
        self.ok("lesson", "--item", "x", "--rung", "1", "--points", "1", "--caught-by", "suite", "--cause", "c")
        _, out, _ = self.hook(SESSION_START, dict(payload))
        self.assertIn("brain:", out)
        self.assertIn("proj-alpha", out)


class Documentation(unittest.TestCase):
    def test_docs_document_the_brain(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("## The brain", readme)
        for token in ("brain.sqlite", "GENTIC_BRAIN", "sql", ".bak", "iCloud"):
            self.assertIn(token, readme, f"README does not mention {token!r}")
        hooks_readme = (HOOKS / "README.md").read_text(encoding="utf-8")
        for kind in ("red", "verification", "gate_block", "nudge_tdd", "nudge_review", "nudge_spend"):
            self.assertIn(kind, hooks_readme, f"hooks README does not list the {kind} event")
        self.assertIn("silent", hooks_readme)

    def test_harness_registers_and_isolates_the_brain_suite(self):
        text = (HOOKS / "tests" / "run.sh").read_text(encoding="utf-8")
        suites = next(line for line in text.splitlines() if line.startswith("for suite in"))
        self.assertIn("test_brain", suites)
        export = text.find("export GENTIC_BRAIN")
        self.assertNotEqual(export, -1, "run.sh does not export GENTIC_BRAIN")
        self.assertLess(export, text.find("Unit and contract suites"), "GENTIC_BRAIN exported too late")


if __name__ == "__main__":
    unittest.main()
