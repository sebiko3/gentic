#!/usr/bin/env python3
"""Structural validation of the setup itself.

Markdown agents, skills, and commands cannot be unit-tested by running them, but they can be
checked for the defect class that actually bit this setup: a reference to something that does
not exist. `settings.json` enabled a `pr-review-toolkit` that was never installed, and
`/ship` invoked three of its agents; nothing failed loudly, review just silently degraded.

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

# Agents shipped by the pr-review-toolkit plugin, which this setup deliberately does not depend
# on. Naming one without marking it optional is the exact bug this suite guards against.
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
GENTIC_SKILL = re.compile(r"\b(gentic-(?:scout|interview|masterprompt|execute|iterate))\b")


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
                if "pr-review-toolkit" not in line and not (EXTERNAL_AGENTS & set(BACKTICKED.findall(line))):
                    continue
                if not QUALIFIER.search(line):
                    offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "external agents referenced as if they exist:\n" + "\n".join(offenders))

    def test_the_original_ship_line_would_still_be_caught(self):
        """Guards the qualifier vocabulary against being widened until it accepts anything.

        This is verbatim the line that shipped broken: three plugin agents named as the primary
        review path, with nothing marking the plugin as optional.
        """
        original = ("Invoke the `pr-review-toolkit` review agents over the diff "
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

        `pr-review-toolkit` was listed in installed_plugins.json with an installPath that did
        not exist on disk, so its agents silently failed to resolve. Checking the key alone
        would have called that healthy.
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
