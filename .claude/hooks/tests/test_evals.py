#!/usr/bin/env python3
"""Contract tests for the eval runner, `evals/run.py`.

Every test drives the real runner through a fake `claude` placed first on PATH: it records its
argv, replays a canned stream-json transcript, and never talks to the network. Real API spend
happens exactly once per run of the workflow — at Iterate, by hand — never here. Each test also
points `GENTIC_BRAIN`, `CLAUDE_HOOK_STATE_DIR` and `CLAUDE_HOME` at private temp paths, so a test
run standalone cannot touch the user's memory or setup.
"""

import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parents[1]
RUNNER = REPO / "evals" / "run.py"
BRAIN = HOOKS / "lib" / "brain.py"

FLAGS = ["--output-format", "--verbose", "--max-turns", "--max-budget-usd", "--permission-mode",
         "--allowedTools", "--no-session-persistence", "--model", "--setting-sources"]

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
argv = sys.argv[1:]
if argv == ["--help"]:
    print(Path(os.environ["FAKE_CLAUDE_HELP"]).read_text())
    sys.exit(0)
if argv == ["--version"]:
    print("2.1.258 (fake)")
    sys.exit(0)
cwd = os.getcwd()
files = sorted(str(p.relative_to(cwd)) for p in Path(cwd).rglob("*") if p.is_file())
record = {"argv": argv, "cwd": cwd, "files": files, "env_brain": os.environ.get("GENTIC_BRAIN")}
with open(os.environ["FAKE_CLAUDE_ARGV"], "a") as handle:
    handle.write(json.dumps(record) + "\n")
for rel in filter(None, os.environ.get("FAKE_CLAUDE_TOUCH", "").split(":")):
    path = Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("touched")
time.sleep(float(os.environ.get("FAKE_CLAUDE_SLEEP", "0")))
transcript = os.environ.get("FAKE_CLAUDE_TRANSCRIPT")
if transcript:
    sys.stdout.write(Path(transcript).read_text())
sys.exit(int(os.environ.get("FAKE_CLAUDE_EXIT", "0")))
'''

TRANSCRIPT = "\n".join([
    json.dumps({"type": "system", "subtype": "init", "tools": ["Read", "Write", "Task"]}),
    json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Scouting."},
        {"type": "tool_use", "name": "Write", "input": {"file_path": "docs/gentic/x/brief.md", "content": "# Brief"}},
    ]}}),
    json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Task", "input": {"subagent_type": "dod-auditor", "prompt": "audit"}},
    ]}}),
    json.dumps({"type": "result", "result": "Item 1 PROVEN. Item 2 FAILED. The password_hash column is "
                "excluded — an unconfirmed default. get_usr_nm is a naming nit, not flagged.",
                "total_cost_usd": 0.5, "num_turns": 3, "is_error": False}),
]) + "\n"


def frontmatter(fields, body):
    lines = ["---"] + [f"{k}: {json.dumps(v) if isinstance(v, list) else v}" for k, v in fields.items()] + ["---", body]
    return "\n".join(lines) + "\n"


class EvalsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="evals-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        fake = self.bin / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.help = self.tmp / "help.txt"
        self.help.write_text("Usage: claude\n" + "\n".join(f"  {f} <x>" for f in FLAGS) + "\n")
        self.argv_log = self.tmp / "argv.jsonl"
        self.transcript = self.tmp / "transcript.jsonl"
        self.transcript.write_text(TRANSCRIPT)
        self.evals = self.tmp / "evals"
        self.evals.mkdir()
        self.brain_db = self.tmp / "brain.sqlite"
        self.home = self.tmp / "claude-home"
        (self.home / "skills" / "gentic").mkdir(parents=True)
        (self.home / "skills" / "gentic" / "SKILL.md").write_text("# gentic")
        (self.home / "agents").mkdir()
        (self.home / "agents" / "dod-auditor.md").write_text("# auditor")

    def case(self, name, graders=None, fields=None, body="Do the thing."):
        directory = self.evals / name
        (directory / "graders").mkdir(parents=True)
        defaults = {"name": name}
        defaults.update(fields or {})
        (directory / "prompt.md").write_text(frontmatter(defaults, body))
        for grader_name, grader_fields in (graders or {"done": {"type": "regex", "pattern": "PROVEN"}}).items():
            (directory / "graders" / f"{grader_name}.md").write_text(frontmatter(grader_fields, "Rubric."))
        return directory

    def run_runner(self, *args, env=None, cwd=None):
        environ = dict(os.environ)
        environ.update({
            "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_CLAUDE_HELP": str(self.help),
            "FAKE_CLAUDE_ARGV": str(self.argv_log),
            "FAKE_CLAUDE_TRANSCRIPT": str(self.transcript),
            "GENTIC_BRAIN": str(self.brain_db),
            "CLAUDE_HOOK_STATE_DIR": str(self.tmp / "state"),
            "CLAUDE_HOME": str(self.home),
        })
        environ.pop("FAKE_CLAUDE_TOUCH", None)
        environ.update(env or {})
        return subprocess.run(
            [sys.executable, str(RUNNER), "--evals-dir", str(self.evals), "--skip-install-check", *args],
            cwd=str(cwd or REPO), env=environ, text=True, capture_output=True, timeout=120,
        )

    def records(self):
        if not self.argv_log.exists():
            return []
        return [json.loads(line) for line in self.argv_log.read_text().splitlines() if line.strip()]

    def result_json(self):
        results = sorted((self.evals / "results").glob("*/result.json"))
        self.assertTrue(results, "no result.json written")
        return json.loads(results[-1].read_text())


class Preflight(EvalsCase):
    def test_preflight_refuses_a_missing_flag(self):
        self.case("one")
        self.help.write_text("Usage: claude\n" + "\n".join(f"  {f}" for f in FLAGS if f != "--no-session-persistence"))
        proc = self.run_runner("--arm", "with")
        self.assertEqual(proc.returncode, 1, "runner did not refuse")
        self.assertIn("preflight: claude lacks --no-session-persistence", proc.stdout + proc.stderr)
        self.assertEqual(self.records(), [], "claude was invoked despite a failed preflight")
        self.help.write_text("Usage: claude\n" + "\n".join(f"  {f} <x>" for f in FLAGS))
        proc = self.run_runner("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class DryRun(EvalsCase):
    def test_dry_run_lists_cases_and_argv(self):
        self.case("alpha")
        self.case("beta", graders={"a": {"type": "regex", "pattern": "x"}, "b": {"type": "file_exists", "path": "*.md"}})
        (self.evals / "results" / "20250101-000000").mkdir(parents=True)
        (self.evals / "notes.md").write_text("not a case")
        proc = self.run_runner("--dry-run")
        self.assertEqual(proc.returncode, 0, f"runner did not run: {proc.stderr}")
        out = proc.stdout
        self.assertIn("alpha", out)
        self.assertIn("beta", out)
        self.assertNotIn("results", out.replace("results/", ""), "results/ listed as a case")
        self.assertIn("2 grader", out)
        with_line = next(l for l in out.splitlines() if "with" in l and "claude" in l and "beta" not in l)
        without_line = next(l for l in out.splitlines() if "without" in l and "claude" in l)
        self.assertIn("--setting-sources project", without_line)
        self.assertNotIn("--setting-sources", with_line)
        self.assertEqual(self.records(), [], "dry run invoked claude")


class Invocation(EvalsCase):
    def test_invocation_flags_per_arm(self):
        self.case("one", fields={"allowed_tools": ["Read", "Bash"], "max_turns": 5}, body="Hello there.")
        proc = self.run_runner("--arm", "both")
        self.assertTrue(self.records(), "claude was never invoked")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        records = self.records()
        self.assertEqual(len(records), 2)
        with_argv, without_argv = records[0]["argv"], records[1]["argv"]
        expected = ["-p", "Hello there.", "--output-format", "stream-json", "--verbose", "--max-turns", "5",
                    "--max-budget-usd", "2", "--permission-mode", "dontAsk", "--allowedTools", "Read", "Bash",
                    "--no-session-persistence", "--model", "sonnet"]
        self.assertEqual(with_argv, expected)
        self.assertEqual(without_argv, expected + ["--setting-sources", "project"])
        self.assertNotEqual(records[0]["cwd"], records[1]["cwd"], "arms shared a workspace")
        for record in records:
            self.assertIn("/workspaces/", record["cwd"])
            self.assertTrue(record["env_brain"].endswith("hooks-brain.sqlite"), record["env_brain"])
            self.assertNotEqual(record["env_brain"], str(self.brain_db), "eval session would write the runner's brain")
        self.case("two", fields={"model": "haiku"})
        self.run_runner("--arm", "with", "--case", "two")
        self.assertIn("haiku", self.records()[-1]["argv"])
        self.run_runner("--arm", "with", "--case", "two", "--model", "opus")
        self.assertIn("opus", self.records()[-1]["argv"])


class Graders(EvalsCase):
    def test_graders_score_a_replayed_transcript(self):
        self.case("one", graders={
            "found-failed": {"type": "regex", "pattern": r"\bfailed\b", "flags": "i"},
            "no-decoy-finding": {"type": "regex", "pattern": "get_usr_nm[^\\n]{0,80}confidence (8|9)\\d", "match": "not_contains"},
            "brief-created": {"type": "file_exists", "path": "docs/gentic/*/brief.md"},
            "files-target": {"type": "regex", "pattern": r"brief\.md", "target": "files"},
            "used-agent": {"type": "tool_used", "tool": "Agent", "input_match": "dod-auditor", "min": 1},
            "judge": {"type": "llm", "criteria": "is it good"},
        })
        proc = self.run_runner("--arm", "with", env={"FAKE_CLAUDE_TOUCH": "docs/gentic/x/brief.md"})
        result = self.result_json()
        graders = result["cases"][0]["arms"]["with"][0]["graders"]
        self.assertEqual(len(graders), 6, "graders were not evaluated")
        verdict = {g["name"]: g for g in graders}
        for name in ("found-failed", "no-decoy-finding", "brief-created", "files-target", "used-agent"):
            self.assertTrue(verdict[name]["passed"], f"{name}: {verdict[name]['detail']}")
        self.assertFalse(verdict["judge"]["passed"])
        self.assertIn("unsupported grader llm", verdict["judge"]["detail"])
        self.assertEqual(proc.returncode, 1, "a failed grader must exit 1")

        self.case("slow", fields={"timeout_seconds": 1}, graders={"any": {"type": "regex", "pattern": "."}})
        self.run_runner("--arm", "with", "--case", "slow", env={"FAKE_CLAUDE_SLEEP": "3"})
        arm = self.result_json()["cases"][0]["arms"]["with"][0]
        self.assertTrue(arm["is_error"])
        self.assertFalse(arm["graders"][0]["passed"])
        self.assertIn("timeout after 1s", arm["graders"][0]["detail"])


class Scaffold(EvalsCase):
    def test_scaffold_runs_first_and_is_not_created(self):
        case = self.case("one", graders={"fixture-not-created": {"type": "file_exists", "path": "fixture.txt"}})
        (case / "fixture").mkdir()
        (case / "fixture" / "fixture.txt").write_text("from fixture")
        (case / "setup.sh").write_text('cp "$EVAL_CASE_DIR/fixture/fixture.txt" . && printf "%s" "$EVAL_REPO" > repo.txt\n')
        (case / "case.yaml").write_text("context.scaffold_script: setup.sh\n")
        self.run_runner("--arm", "with")
        record = self.records()[-1]
        self.assertIn("fixture.txt", record["files"], "scaffold did not run before claude")
        self.assertIn("repo.txt", record["files"])
        self.assertEqual((Path(record["cwd"]) / "repo.txt").read_text(), str(REPO))
        grader = self.result_json()["cases"][0]["arms"]["with"][0]["graders"][0]
        self.assertFalse(grader["passed"], "a scaffolded file counted as created")

        (case / "setup.sh").write_text('echo "disk full" >&2; exit 3\n')
        self.run_runner("--arm", "with")
        arm = self.result_json()["cases"][0]["arms"]["with"][0]
        self.assertTrue(arm["is_error"])
        self.assertIn("disk full", arm["graders"][0]["detail"])


class BrainRows(EvalsCase):
    def rows(self, sql):
        if not self.brain_db.exists():
            return []
        with sqlite3.connect(self.brain_db) as conn:
            return conn.execute(sql).fetchall()

    def test_brain_rows_and_evals_summary(self):
        self.case("one", graders={"a": {"type": "regex", "pattern": "PROVEN"}, "b": {"type": "regex", "pattern": "FAILED"}})
        proc = self.run_runner("--arm", "both")
        self.assertEqual(len(self.rows("select * from eval_runs")), 2, "no eval_runs rows in brain")
        self.assertEqual(len(self.rows("select * from eval_graders")), 4)
        self.assertEqual(self.rows("select outcome from runs")[0][0], "done")
        self.assertEqual(len(self.rows("select * from stamps")), 2, "installed skill and agent files were not stamped")
        summary = subprocess.run([sys.executable, str(BRAIN), "evals"], cwd=str(REPO), text=True, capture_output=True,
                                 env=dict(os.environ, GENTIC_BRAIN=str(self.brain_db)))
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertIn("one", summary.stdout)
        self.assertIn("delta", summary.stdout)
        self.assertIn("with 2/2", summary.stdout)

        fresh = self.tmp / "fresh.sqlite"
        self.run_runner("--arm", "with", "--no-brain", env={"GENTIC_BRAIN": str(fresh)})
        self.assertFalse(fresh.exists(), "--no-brain still touched the brain")


class Money(EvalsCase):
    def test_money_ceiling_and_exit_codes(self):
        expensive = self.tmp / "expensive.jsonl"
        expensive.write_text(TRANSCRIPT.replace('"total_cost_usd": 0.5', '"total_cost_usd": 8'))
        for name in ("a", "b", "c"):
            self.case(name)
        proc = self.run_runner("--arm", "with", "--max-budget-usd", "8", "--suite-budget-usd", "21",
                               env={"FAKE_CLAUDE_TRANSCRIPT": str(expensive)})
        self.assertEqual(proc.returncode, 2, "suite ceiling did not stop the third run")
        self.assertEqual(len(self.records()), 2)
        self.assertIn("skipped: suite budget", proc.stdout)
        totals = self.result_json()["totals"]
        self.assertEqual(totals["skipped"], 1)
        self.assertAlmostEqual(totals["cost_usd"], 16)
        self.assertIn("delta", totals)

        self.argv_log.unlink()
        proc = self.run_runner("--arm", "with", "--suite-budget-usd", "100")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(len(self.records()), 3)
        self.case("d", graders={"never": {"type": "regex", "pattern": "zzz-not-there"}})
        proc = self.run_runner("--arm", "with", "--suite-budget-usd", "100", "--case", "d")
        self.assertEqual(proc.returncode, 1)


class FiveCases(unittest.TestCase):
    EXPECTED = ["critic-finds-contradiction", "csv-export-probe", "dod-auditor-false-claim",
                "executor-refuses-vague", "reviewer-seeded-defect"]

    def test_five_cases_are_well_formed(self):
        evals = REPO / "evals"
        names = sorted(p.parent.name for p in evals.glob("*/prompt.md")) if evals.is_dir() else []
        self.assertEqual(names, self.EXPECTED)
        sys.path.insert(0, str(REPO / "evals"))
        try:
            import run as runner  # noqa: E402
        finally:
            sys.path.remove(str(REPO / "evals"))
        for name in names:
            case = runner.load_case(evals / name)
            with self.subTest(case=name):
                self.assertGreaterEqual(len(case.graders), 2)
                for grader in case.graders:
                    self.assertIn(grader.type, ("regex", "file_exists", "tool_used"))
                if name == "csv-export-probe":
                    self.assertEqual(case.max_turns, 21)
                    self.assertEqual(case.allowed_tools, ["Read", "Glob", "Grep", "Write", "Edit", "Bash"])
                else:
                    self.assertEqual(case.max_turns, 8)
                    self.assertEqual(case.allowed_tools, ["Read", "Glob", "Grep", "Bash", "Task"])
                if name != "executor-refuses-vague":
                    self.assertTrue(case.scaffold_script, f"{name} has no scaffold")
                    self.assertTrue((evals / name / case.scaffold_script).is_file())
        fixture = evals / "csv-export-probe" / "fixture"
        files = [p for p in fixture.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        self.assertLessEqual(len(files), 5)
        self.assertLessEqual(sum(len(p.read_text().splitlines()) for p in files), 200)
        for path in files:
            if path.suffix == ".py":
                self.assertNotIn("import flask", path.read_text().lower(), "fixture must be stdlib-only")
        proc = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=str(fixture), text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class Hygiene(unittest.TestCase):
    def test_harness_registers_evals_offline(self):
        text = (HOOKS / "tests" / "run.sh").read_text(encoding="utf-8")
        suites = next(line for line in text.splitlines() if line.startswith("for suite in"))
        self.assertIn("test_evals", suites)
        self.assertNotIn("evals/run.py", text, "the harness must never spend money")

    def test_docs_evals_are_documented(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("## The fitness function", readme)
        for token in ("evals/run.py", "--setting-sources project", "brain evals", "claude plugin eval", "21"):
            self.assertIn(token, readme, f"README does not mention {token!r}")
        hooks_readme = (HOOKS / "README.md").read_text(encoding="utf-8")
        for runner in ("playwright", "cypress", "lighthouse", "axe"):
            self.assertIn(runner, hooks_readme.lower(), f"hooks README does not name {runner}")

    def test_manifest_and_gitignore(self):
        manifest = REPO / ".claude-plugin" / "plugin.json"
        self.assertTrue(manifest.is_file(), ".claude-plugin/plugin.json missing")
        data = json.loads(manifest.read_text())
        self.assertEqual(sorted(data), ["description", "experimental", "name", "version"])
        self.assertEqual(data["name"], "gentic")
        self.assertEqual(data["experimental"], {"evals": "evals"})
        proc = subprocess.run(["git", "check-ignore", "-q", "evals/results/x"], cwd=str(REPO))
        self.assertEqual(proc.returncode, 0, "evals/results/ is not git-ignored")


if __name__ == "__main__":
    unittest.main()
