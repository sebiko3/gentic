#!/usr/bin/env python3
"""Unit tests for the shared hook library."""

import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import common  # noqa: E402


class ReadPayload(unittest.TestCase):
    def _stdin(self, text):
        sys.stdin = io.StringIO(text)
        self.addCleanup(lambda: setattr(sys, "stdin", sys.__stdin__))

    def test_parses_well_formed_json(self):
        self._stdin('{"prompt": "hello", "session_id": "s1"}')
        self.assertEqual(common.read_payload()["prompt"], "hello")

    def test_empty_stdin_yields_empty_dict(self):
        self._stdin("")
        self.assertEqual(common.read_payload(), {})

    def test_malformed_json_yields_empty_dict(self):
        self._stdin("{not json at all")
        self.assertEqual(common.read_payload(), {})

    def test_non_object_json_yields_empty_dict(self):
        self._stdin("[1, 2, 3]")
        self.assertEqual(common.read_payload(), {})


class SafeMain(unittest.TestCase):
    def setUp(self):
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        self.addCleanup(lambda: (setattr(sys, "stdout", sys.__stdout__),
                                 setattr(sys, "stderr", sys.__stderr__)))

    def test_exits_zero_when_body_raises(self):
        def boom():
            raise RuntimeError("kaboom")

        with self.assertRaises(SystemExit) as caught:
            common.safe_main(boom)
        self.assertEqual(caught.exception.code, 0)

    def test_exits_zero_on_clean_run(self):
        with self.assertRaises(SystemExit) as caught:
            common.safe_main(lambda: None)
        self.assertEqual(caught.exception.code, 0)



class PublicSurface(unittest.TestCase):
    """The session-state helpers left with the Stop hook; nothing dead may linger here."""

    LIVE = {"read_payload", "emit", "emit_context", "emit_message", "safe_main", "git_root"}

    def test_common_exports_only_the_live_helpers(self):
        public = {name for name, value in vars(common).items()
                  if callable(value) and getattr(value, "__module__", None) == common.__name__
                  and not name.startswith("_")}
        self.assertEqual(public, self.LIVE)
        self.assertFalse(hasattr(common, "STATE_DIR"), "the JSON state directory is gone")


class GitRoot(unittest.TestCase):
    def test_returns_none_outside_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(common.git_root(d))

    def test_returns_none_for_missing_directory(self):
        self.assertIsNone(common.git_root("/no/such/place/at/all"))

    def test_finds_root_from_a_subdirectory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / ".git").mkdir()
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            self.assertEqual(Path(common.git_root(str(nested))).resolve(), root)


class Emit(unittest.TestCase):
    def _capture(self):
        buf = io.StringIO()
        sys.stdout = buf
        self.addCleanup(lambda: setattr(sys, "stdout", sys.__stdout__))
        return buf

    def test_emit_context_writes_parseable_json(self):
        buf = self._capture()
        common.emit_context("hello there")
        payload = json.loads(buf.getvalue())
        self.assertIn("hello there", json.dumps(payload))

    def test_emit_context_is_silent_for_empty_text(self):
        buf = self._capture()
        common.emit_context("   ")
        self.assertEqual(buf.getvalue().strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=1)
