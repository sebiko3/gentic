#!/usr/bin/env python3
"""Structural validation of the setup itself.

Markdown agents, skills, and commands cannot be unit-tested by running them, but they can be
checked for the defect class that actually bit this setup: a reference to something that does
not exist. `settings.json` enabled an optional review plugin whose recorded install directory
was missing, and `/ship` invoked three of its agents as if they were the primary path; nothing
failed loudly, review just silently degraded.

Every rule below exists to make that specific failure impossible to reintroduce.
"""

import json
import os
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLAUDE = REPO / ".claude"
AGENTS = CLAUDE / "agents"

EXPECTED_AGENTS = {"code-reviewer", "dod-auditor", "masterprompt-critic", "task-executor"}

# The optional review plugin this setup deliberately does not depend on, and the agents it
# ships. Naming any of them without marking them optional is the exact bug this suite guards.
OPTIONAL_PLUGIN = "pr-review-toolkit"  # optional; nothing in this setup requires it
EXTERNAL_AGENTS = {
    "silent-failure-hunter",
    "pr-test-analyzer",
    "comment-analyzer",
    "type-design-analyzer",
    "code-simplifier",
}

# Phrases that mark a reference as conditional. Must appear on the same line as the reference:
# a qualifier a paragraph away does not stop a reader treating the line as a hard dependency.
QUALIFIER = re.compile(
    r"\boptional(ly)?\b|\b(if|when|where)\s+(that\s+|the\s+)?\w*\s*(is\s+)?"
    r"(available|installed|present)\b|\bis\s+(available|installed)\b|\bunavailable\b|\bnot installed\b",
    re.I,
)

BACKTICKED = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
SUPERPOWERS_REF = re.compile(r"superpowers:([a-z][a-z0-9-]*)")
# A slash command, not a path segment: preceded by start/space/backtick/paren, and not
# followed by another path component or a file extension.
SLASH_COMMAND = re.compile(r"(?:^|(?<=[\s`(]))/([a-z][a-z0-9-]{2,})(?![\w/.-])")
HOOK_PATH = re.compile(r"hooks/([a-z_]+\.py)")
# Only the phase skills. `gentic-runs` is a directory in the fallback artifact path, not a skill.
GENTIC_SKILL = re.compile(r"\b(gentic-(?:scout|interview|masterprompt|execute|iterate|tdd|brain))\b")


def frontmatter(path):
    """Parse a leading `---` YAML block into a flat dict. Returns None when absent."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fields, key = {}, None
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] += " " + line.strip()
    return fields


def markdown_files():
    """Every markdown file that describes the setup. Run artifacts under docs/ are excluded:
    they record history, including mistakes, and must not be edited to satisfy a check."""
    files = sorted(CLAUDE.rglob("*.md"))
    for extra in ("README.md", "CLAUDE.md"):
        candidate = REPO / extra
        if candidate.is_file():
            files.append(candidate)
    return files


def lines_of(path):
    return path.read_text(encoding="utf-8").splitlines()


class AgentDefinitions(unittest.TestCase):
    def test_exactly_the_expected_agents_exist(self):
        self.assertTrue(AGENTS.is_dir(), f"{AGENTS} missing")
        found = {p.stem for p in AGENTS.glob("*.md")}
        self.assertEqual(found, EXPECTED_AGENTS, f"agent set drifted: {found}")

    def test_each_agent_has_valid_frontmatter(self):
        for path in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=path.name):
                fields = frontmatter(path)
                self.assertIsNotNone(fields, "no YAML frontmatter")
                for required in ("name", "description", "model"):
                    self.assertIn(required, fields, f"missing `{required}`")
                    self.assertTrue(fields[required], f"empty `{required}`")

    def test_agent_name_matches_filename(self):
        for path in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=path.name):
                self.assertEqual(frontmatter(path)["name"], path.stem)

    EXPECTED_TOOLS = {
        "code-reviewer": "Read, Grep, Glob, Bash",
        "dod-auditor": "Read, Grep, Glob, Bash",
        "masterprompt-critic": "Read, Grep, Glob",
    }

    def test_reviewing_agents_declare_exactly_the_documented_tools(self):
        """The README makes a claim about these tool sets; pin them so it cannot go stale.

        No reviewing agent may gain an edit tool (Edit, Write, MultiEdit, NotebookEdit) without
        this failing and the README being updated in the same change.
        """
        for name, expected in self.EXPECTED_TOOLS.items():
            with self.subTest(agent=name):
                fields = frontmatter(AGENTS / f"{name}.md")
                self.assertEqual(fields.get("tools"), expected)
                for forbidden in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                    self.assertNotIn(forbidden, fields.get("tools", ""))

    def test_each_agent_states_what_it_returns(self):
        """An agent whose output shape is undefined cannot be merged by its caller."""
        for path in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=path.name):
                body = path.read_text(encoding="utf-8").lower()
                self.assertRegex(body, r"##+ .*(output|returns|report)", "no output contract section")


class ResolvableReferences(unittest.TestCase):
    def setUp(self):
        self.agents = {p.stem for p in AGENTS.glob("*.md")} if AGENTS.is_dir() else set()
        self.commands = {p.stem for p in (CLAUDE / "commands").glob("*.md")}
        self.skills = {p.name for p in (CLAUDE / "skills").iterdir() if p.is_dir()}
        self.hooks = {p.name for p in (CLAUDE / "hooks").glob("*.py")}

    def test_no_unqualified_reference_to_an_uninstalled_plugin(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                if OPTIONAL_PLUGIN not in line and not (EXTERNAL_AGENTS & set(BACKTICKED.findall(line))):
                    continue
                if not QUALIFIER.search(line):
                    offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "external agents referenced as if they exist:\n" + "\n".join(offenders))

    def test_the_original_ship_line_would_still_be_caught(self):
        """Guards the qualifier vocabulary against being widened until it accepts anything.

        This is verbatim the line that shipped broken: three plugin agents named as the primary
        review path, with nothing marking the plugin as optional.
        """
        original = (f"Invoke the `{OPTIONAL_PLUGIN}` review agents over the diff "
                    "(`code-reviewer`, plus `silent-failure-hunter` and `pr-test-analyzer`).")
        self.assertIsNone(QUALIFIER.search(original), "qualifier regex now accepts the original defect")

    def test_first_party_agent_references_resolve(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                for token in BACKTICKED.findall(line):
                    if token in EXPECTED_AGENTS and token not in self.agents:
                        offenders.append(f"{path.relative_to(REPO)}:{number}: `{token}` has no agent file")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_superpowers_references_are_marked_conditional(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                if SUPERPOWERS_REF.search(line) and not QUALIFIER.search(line):
                    offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "plugin skills referenced unconditionally:\n" + "\n".join(offenders))

    def test_slash_commands_resolve(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                for name in SLASH_COMMAND.findall(line):
                    if name in self.commands or name in self.skills:
                        continue
                    offenders.append(f"{path.relative_to(REPO)}:{number}: /{name} resolves to nothing")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_referenced_hook_files_exist(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                for name in HOOK_PATH.findall(line):
                    if name not in self.hooks:
                        offenders.append(f"{path.relative_to(REPO)}:{number}: hooks/{name} missing")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_referenced_gentic_skills_exist(self):
        offenders = []
        for path in markdown_files():
            for number, line in enumerate(lines_of(path), 1):
                for name in GENTIC_SKILL.findall(line):
                    if name not in self.skills:
                        offenders.append(f"{path.relative_to(REPO)}:{number}: skill {name} missing")
        self.assertEqual(offenders, [], "\n".join(offenders))


class ReviewFixture(unittest.TestCase):
    """The seeded-defect fixture must stay honest: planted defects present, decoy harmless."""

    fixture = CLAUDE / "hooks/tests/fixtures/seeded_defect.py"
    expected = CLAUDE / "hooks/tests/fixtures/seeded_defect.expected.md"

    def test_both_files_exist(self):
        self.assertTrue(self.fixture.is_file(), "fixture missing")
        self.assertTrue(self.expected.is_file(), "expectation file missing")

    def test_the_planted_defects_are_still_planted(self):
        source = self.fixture.read_text()
        self.assertIn("except Exception:\n        pass", source, "swallowed exception was fixed")
        self.assertRegex(source, r'execute\(f"SELECT', "SQL interpolation was fixed")

    def test_the_fixture_is_syntactically_valid(self):
        compile(self.fixture.read_text(), str(self.fixture), "exec")

    def test_the_expectation_names_both_defects_and_the_decoy(self):
        text = self.expected.read_text()
        for symbol in ("load_user", "record_login", "get_usr_nm"):
            self.assertIn(symbol, text)


class NamingIsProjectScoped(unittest.TestCase):
    """gentic's own naming must never read as a universal rule.

    `gentic/<slug>` and `gentic(<slug>)` were stated unconditionally in the skills and in
    /ship, so every repository got them whether or not it had adopted the workflow. Each
    surviving occurrence must sit on a line that marks it conditional.

    CLAUDE.md is exempt: its unqualified copy of the rule IS the adoption marker the helper
    looks for, so qualifying it would un-adopt this repository.
    """

    CONDITIONAL = re.compile(r"adopted|project_conventions|this repo", re.I)

    def test_no_hardcoded_naming_reads_as_universal(self):
        offenders = []
        for path in sorted((CLAUDE / "skills").rglob("*.md")) + sorted((CLAUDE / "commands").glob("*.md")):
            for number, line in enumerate(lines_of(path), 1):
                if "gentic/<slug>" not in line and "gentic(<slug>)" not in line:
                    continue
                if not self.CONDITIONAL.search(line):
                    offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:88]}")
        self.assertEqual(offenders, [], "naming stated unconditionally:\n" + "\n".join(offenders))

    def test_the_adoption_marker_in_claude_md_stays_unqualified(self):
        text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("gentic/<slug>", text,
                      "the adoption marker was removed; this repo would stop being adopted")


class CommandDefinitions(unittest.TestCase):
    def test_every_command_has_a_description(self):
        for path in sorted((CLAUDE / "commands").glob("*.md")):
            with self.subTest(command=path.name):
                fields = frontmatter(path)
                self.assertIsNotNone(fields, "no frontmatter")
                self.assertTrue(fields.get("description"), "no description")


class SkillDefinitions(unittest.TestCase):
    def test_every_skill_has_name_and_description(self):
        for path in sorted((CLAUDE / "skills").glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                fields = frontmatter(path)
                self.assertIsNotNone(fields, "no frontmatter")
                self.assertEqual(fields.get("name"), path.parent.name)
                self.assertTrue(fields.get("description"), "no description")


class TestFirstSpine(unittest.TestCase):
    """The workflow's test-first discipline must be real text, not an aspiration.

    Before this suite, TDD inside gentic was a single delegated sentence in one phase skill.
    Each rule below pins one piece of the spine: the discipline exists on its own, Execute
    routes through it, the spec designs the tests, and the task table can hold the evidence.
    """

    def read(self, relative):
        path = CLAUDE / relative
        self.assertTrue(path.is_file(), f"{path.relative_to(REPO)} does not exist")
        return path.read_text(encoding="utf-8")

    def test_gentic_tdd_skill_is_self_contained(self):
        body = self.read("skills/gentic-tdd/SKILL.md")
        fields = frontmatter(CLAUDE / "skills/gentic-tdd/SKILL.md")
        self.assertIsNotNone(fields, "no frontmatter")
        self.assertEqual(fields.get("name"), "gentic-tdd")
        lowered = body.lower()
        for token in ("iron law", "red", "green", "refactor"):
            self.assertIn(token, lowered, f"gentic-tdd does not define {token!r}")
        self.assertRegex(body, r"\|.*\|", "no rationalisation or red-flag table")
        # The discipline must stand alone: superpowers is a composition point, not a dependency.
        for line in body.splitlines():
            if SUPERPOWERS_REF.search(line):
                self.assertRegex(line, QUALIFIER, f"unconditional plugin dependency: {line.strip()[:80]}")

    def test_gentic_tdd_is_validated_like_the_other_phase_skills(self):
        """`GENTIC_SKILL` gates which references get existence-checked; a skill missing from it
        can be referenced by a typo forever without anything failing."""
        self.assertRegex("gentic-tdd", GENTIC_SKILL, "GENTIC_SKILL does not cover gentic-tdd")

    def test_execute_routes_tasks_through_tdd(self):
        body = self.read("skills/gentic-execute/SKILL.md")
        self.assertIn("gentic-tdd", body, "gentic-execute does not invoke gentic-tdd")
        self.assertRegex(body, r"(?i)red", "gentic-execute never mentions RED evidence")

    def test_masterprompt_requires_test_contracts(self):
        body = self.read("skills/gentic-masterprompt/SKILL.md")
        self.assertIn("contract:", body, "masterprompt template has no test contract")
        lowered = body.lower()
        for field in ("test file", "test name", "expected red"):
            self.assertIn(field, lowered, f"test contract does not name {field!r}")
        self.assertRegex(lowered, r"contract.*scan|scan.*contract",
                         "the critique pass has no test-contract scan")

    def test_task_table_template_has_tdd_columns(self):
        body = self.read("skills/gentic/SKILL.md")
        header = next((line for line in body.splitlines()
                       if line.startswith("|") and "Task" in line and "Size" in line), "")
        self.assertTrue(header, "no task table header in the progress.md template")
        self.assertIn("Test", header, "task table header lacks a Test column")
        self.assertIn("RED", header, "task table header lacks a RED column")

    def test_docs_document_the_tdd_spine(self):
        for name in ("README.md", "CLAUDE.md"):
            with self.subTest(doc=name):
                body = (REPO / name).read_text(encoding="utf-8")
                self.assertIn("gentic-tdd", body, f"{name} does not mention gentic-tdd")
                self.assertRegex(body, r"(?i)\bRED\b", f"{name} does not mention RED evidence")


class BrainWiring(unittest.TestCase):
    """The brain is only memory if the phases actually consult it.

    A `gentic-brain` skill that nothing invokes is the `ROUTING.md` defect again: shipped,
    installed, invisible. Every phase that has something to remember or recall must name it.
    """

    PHASES_THAT_REMEMBER = (
        "gentic", "gentic-scout", "gentic-interview", "gentic-masterprompt",
        "gentic-execute", "gentic-iterate",
    )

    def test_brain_skill_is_wired_into_the_phases(self):
        skill = CLAUDE / "skills" / "gentic-brain" / "SKILL.md"
        self.assertTrue(skill.is_file(), "skills/gentic-brain/SKILL.md missing")
        fields = frontmatter(skill)
        self.assertEqual(fields.get("name"), "gentic-brain")
        description = fields.get("description", "")
        self.assertTrue(description.startswith("Use when"), "description is not trigger-style")
        named = sum(1 for word in ("note", "recall", "decide", "lesson") if word in description)
        self.assertGreaterEqual(named, 2, "description names fewer than two brain verbs")
        for name in self.PHASES_THAT_REMEMBER:
            body = (CLAUDE / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("gentic-brain", body, f"{name} does not mention gentic-brain")
        self.assertRegex("gentic-brain", GENTIC_SKILL, "GENTIC_SKILL does not cover gentic-brain")
        run_sh = (CLAUDE / "hooks" / "tests" / "run.sh").read_text(encoding="utf-8")
        self.assertIn('= "8"', run_sh, "run.sh does not expect 8 gentic skills")


class AutonomousRuns(unittest.TestCase):
    """The fitness suite showed a headless run stopping at the Interview to "flag" defaults and
    the executor answering in prose. The rules that prevent both live in the wording below."""

    def lowered(self, rel):
        return (REPO / rel).read_text(encoding="utf-8").lower()

    def test_interview_continues_when_no_question_can_be_asked(self):
        body = self.lowered(".claude/skills/gentic-interview/SKILL.md")
        for needle in ('`askuserquestion` is unavailable', 'never end the turn', 'return to the orchestrator'):
            self.assertIn(needle, body)

    def test_orchestrator_has_an_autonomous_runs_section(self):
        body = self.lowered(".claude/skills/gentic/SKILL.md")
        self.assertIn('## autonomous runs', body)
        self.assertIn('nobody to object', body)

    def test_executor_block_is_the_entire_message(self):
        body = self.lowered(".claude/agents/task-executor.md")
        output = body[body.index('## output'):]
        self.assertIn('entire final message', output)
        self.assertIn('assignment unclear', output)

    def test_readme_says_headless_runs_continue(self):
        body = self.lowered("README.md")
        self.assertIn('no `askuserquestion`', body)
        self.assertIn("don't stop to flag", body)


class StandingAuthorizations(unittest.TestCase):
    """A grant in CLAUDE.md plus a machine-side trust file let a run push and open a PR; a STOP
    file halts it; a valve caps fan-out. Each rule lives in wording that must stay in place."""

    def lowered(self, rel):
        return (REPO / rel).read_text(encoding="utf-8").lower()

    def test_routing_names_the_grant_and_the_helper(self):
        body = self.lowered(".claude/skills/gentic/ROUTING.md")
        self.assertIn("## gentic authorizations", body)
        self.assertIn("authorized push", body)

    def test_iterate_consumes_the_grant_and_checks_stop(self):
        body = self.lowered(".claude/skills/gentic-iterate/SKILL.md")
        self.assertIn("authorized open-pr", body)
        self.assertIn("ship.md", body)
        self.assertIn("docs/gentic/<run>/stop", body)

    def test_ship_admits_the_second_caller(self):
        self.assertIn("trusted-projects", self.lowered(".claude/commands/ship.md"))

    def test_execute_checks_stop_before_each_task(self):
        self.assertIn("check for `stop`", self.lowered(".claude/skills/gentic-execute/SKILL.md"))

    def test_orchestrator_has_a_stop_request(self):
        self.assertIn("## stop request", self.lowered(".claude/skills/gentic/SKILL.md"))

    def test_this_repo_declares_its_authorizations(self):
        self.assertIn("## gentic authorizations", self.lowered("CLAUDE.md"))

    def test_readme_documents_authorizations_and_trust(self):
        body = self.lowered("README.md")
        self.assertIn("## standing authorizations", body)
        self.assertIn("trusted-projects", body)

    def test_hooks_readme_documents_the_valve(self):
        body = self.lowered(".claude/hooks/README.md")
        self.assertIn("in flight", body)
        self.assertIn("run_in_background", body)


class NoOrphanedSkillFiles(unittest.TestCase):
    """A file shipped inside a skill that its SKILL.md never mentions is invisible.

    `ROUTING.md` was exactly that: installed alongside the gentic skill, carrying the
    machine-wide rules, and referenced by nothing after a stale repo copy overwrote the live
    SKILL.md. Nothing failed — the rules simply stopped being read.
    """

    def test_every_shipped_skill_file_is_referenced_by_its_skill_md(self):
        orphans = []
        for skill_md in sorted((CLAUDE / "skills").glob("*/SKILL.md")):
            body = skill_md.read_text(encoding="utf-8")
            for sibling in sorted(skill_md.parent.rglob("*")):
                if not sibling.is_file() or sibling.name == "SKILL.md":
                    continue
                if sibling.name not in body:
                    orphans.append(f"{sibling.relative_to(REPO)} is never mentioned by {skill_md.relative_to(REPO)}")
        self.assertEqual(orphans, [], "orphaned skill files:\n" + "\n".join(orphans))


class LiveMachineConfig(unittest.TestCase):
    """Checks the installed machine, not the repo. Skips where that machine is not this one."""

    def setUp(self):
        home = Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))
        self.settings = home / "settings.json"
        self.installed = home / "plugins" / "installed_plugins.json"
        if not (self.settings.is_file() and self.installed.is_file()):
            self.skipTest("no installed Claude Code config on this machine")

    def test_no_enabled_plugin_is_uninstalled(self):
        """Registry membership is not installation.

        The optional review plugin was listed in installed_plugins.json with an installPath
        that did not exist on disk, so its agents silently failed to resolve. Checking the key
        alone would have called that healthy.
        """
        enabled = json.loads(self.settings.read_text()).get("enabledPlugins", {})
        registry = json.loads(self.installed.read_text()).get("plugins", {})
        broken = []
        for name, on in sorted(enabled.items()):
            if not on:
                continue
            entries = registry.get(name)
            if not entries:
                broken.append(f"{name}: enabled, absent from the registry")
                continue
            if not any(Path(e.get("installPath", "")).is_dir() for e in entries):
                paths = ", ".join(e.get("installPath", "?") for e in entries)
                broken.append(f"{name}: registered but installPath does not exist ({paths})")
        self.assertEqual(broken, [], "enabled plugins that cannot load:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main(verbosity=1)
