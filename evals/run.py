#!/usr/bin/env python3
"""gentic's fitness function: run the eval cases under evals/ with and without gentic.

Each case is a directory holding `prompt.md` (frontmatter + the prompt), optional `case.yaml`
(`context.scaffold_script`), and `graders/*.md`. The layout is the one `claude plugin eval`
documents; this runner exists because that command is early-access and disabled here. Every
run is one headless `claude -p` session in a fresh workspace. The `with` arm sees the user's
installed setup exactly as the user does; the `without` arm passes `--setting-sources project`,
which loads no user skills, hooks or agents. The difference between the two is the score.

Money is spent only here, on purpose: never from the test harness, which drives this file
through a fake `claude` on PATH.
"""

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO / "evals"

# Fibonacci-derived balancing values (house rule).
DEFAULT_MAX_TURNS = 13
DEFAULT_TIMEOUT = 900
DEFAULT_RUN_BUDGET = 2.0
DEFAULT_SUITE_BUDGET = 21.0
DEFAULT_MODEL = "sonnet"
DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "Bash"]

# Every flag this runner emits; preflight refuses to launch if `claude --help` lacks one.
REQUIRED_FLAGS = ("--output-format", "--verbose", "--max-turns", "--max-budget-usd",
                  "--permission-mode", "--allowedTools", "--no-session-persistence", "--model",
                  "--setting-sources")

CASE_KEYS = {"name", "tags", "runs", "max_turns", "timeout_seconds", "allowed_tools", "model"}
SUPPORTED_GRADERS = ("regex", "file_exists", "tool_used")


# --- parsing ---------------------------------------------------------------------------

def parse_flat(text):
    """One `key: value` per line. JSON arrays, booleans and integers are converted; the rest
    stay strings. Nested YAML is not supported — `case.yaml` uses dotted keys instead."""
    fields = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("["):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        elif value in ("true", "false"):
            value = value == "true"
        elif re.fullmatch(r"-?\d+", value):
            value = int(value)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def split_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}, text
    head = parts[0][3:]
    body = parts[1].lstrip("\n")
    return parse_flat(head), body


@dataclass
class Grader:
    name: str
    type: str
    fields: dict


@dataclass
class Case:
    name: str
    directory: Path
    prompt: str
    runs: int = 1
    max_turns: int = DEFAULT_MAX_TURNS
    timeout_seconds: int = DEFAULT_TIMEOUT
    allowed_tools: list = field(default_factory=lambda: list(DEFAULT_TOOLS))
    model: str = None
    tags: list = field(default_factory=list)
    scaffold_script: str = None
    graders: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def load_case(directory):
    directory = Path(directory)
    fields, body = split_frontmatter((directory / "prompt.md").read_text(encoding="utf-8"))
    case = Case(name=directory.name, directory=directory, prompt=body.strip())
    case.runs = int(fields.get("runs", 1))
    case.max_turns = int(fields.get("max_turns", DEFAULT_MAX_TURNS))
    case.timeout_seconds = int(fields.get("timeout_seconds", DEFAULT_TIMEOUT))
    tools = fields.get("allowed_tools")
    if isinstance(tools, list):
        case.allowed_tools = [str(t) for t in tools]
    case.model = fields.get("model") or None
    tags = fields.get("tags")
    case.tags = [str(t) for t in tags] if isinstance(tags, list) else []
    for key in fields:
        if key not in CASE_KEYS:
            case.warnings.append(f"{case.name}: prompt.md key {key!r} is not supported and was ignored")
    case_yaml = directory / "case.yaml"
    if case_yaml.is_file():
        meta = parse_flat(case_yaml.read_text(encoding="utf-8"))
        case.scaffold_script = meta.get("context.scaffold_script") or None
        for key in meta:
            if key != "context.scaffold_script":
                case.warnings.append(f"{case.name}: case.yaml key {key!r} is not supported and was ignored")
    graders_dir = directory / "graders"
    if graders_dir.is_dir():
        for path in sorted(graders_dir.glob("*.md")):
            gfields, _ = split_frontmatter(path.read_text(encoding="utf-8"))
            case.graders.append(Grader(name=path.stem, type=str(gfields.get("type", "")), fields=gfields))
    return case


def discover(evals_dir):
    """A case is any child directory holding prompt.md; `results/` and loose files are not."""
    evals_dir = Path(evals_dir)
    if not evals_dir.is_dir():
        return []
    return [load_case(p.parent) for p in sorted(evals_dir.glob("*/prompt.md"))]


# --- invocation ------------------------------------------------------------------------

def resolve_model(case, cli_model):
    return cli_model or case.model or DEFAULT_MODEL


def claude_argv(case, arm, model, run_budget):
    argv = ["-p", case.prompt, "--output-format", "stream-json", "--verbose",
            "--max-turns", str(case.max_turns), "--max-budget-usd", format_money(run_budget),
            "--permission-mode", "dontAsk", "--allowedTools", *case.allowed_tools,
            "--no-session-persistence", "--model", model]
    if arm == "without":
        argv += ["--setting-sources", "project"]
    return argv


def format_money(value):
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def preflight(skip_install_check):
    """The reason not to launch, or None."""
    claude = shutil.which("claude")
    if not claude:
        return "preflight: claude not found on PATH"
    try:
        help_text = subprocess.run([claude, "--help"], text=True, capture_output=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return f"preflight: claude --help failed: {exc}"
    for flag in REQUIRED_FLAGS:
        if flag not in help_text:
            return f"preflight: claude lacks {flag}"
    if not skip_install_check:
        check = subprocess.run(["bash", str(REPO / "install.sh"), "--check"], cwd=str(REPO),
                               text=True, capture_output=True, timeout=120)
        if check.returncode != 0:
            return "preflight: the installed setup differs from this checkout, so the `with` arm would " \
                   "measure something else\n" + check.stdout.strip() + "\nrun ./install.sh, or pass --skip-install-check"
    return None


# --- CLI -------------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evals-dir", default=str(EVALS_DIR))
    parser.add_argument("--arm", choices=("with", "without", "both"), default="both")
    parser.add_argument("--case", default=None, help="glob over case directory names")
    parser.add_argument("--runs", type=int, default=None, help="override every case's runs")
    parser.add_argument("--model", default=None, help="overrides frontmatter model; default sonnet")
    parser.add_argument("--max-budget-usd", type=float, default=DEFAULT_RUN_BUDGET, help="per run")
    parser.add_argument("--suite-budget-usd", type=float, default=DEFAULT_SUITE_BUDGET)
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-brain", action="store_true")
    parser.add_argument("--skip-install-check", action="store_true")
    return parser


def arms_for(choice):
    return ["with", "without"] if choice == "both" else [choice]


def main(argv=None):
    args = build_parser().parse_args(argv)
    problem = preflight(args.skip_install_check)
    if problem:
        print(problem)
        return 1
    cases = discover(args.evals_dir)
    if args.case:
        cases = [c for c in cases if fnmatch.fnmatch(c.name, args.case)]
    if not cases:
        print("no cases found")
        return 1
    if args.dry_run:
        print(f"dry run: {len(cases)} case(s)")
        for case in cases:
            print(f"{case.name}  {len(case.graders)} grader(s)  runs {args.runs or case.runs}")
            for arm in arms_for(args.arm):
                argv_text = " ".join(shlex.quote(a) for a in claude_argv(case, arm, resolve_model(case, args.model), args.max_budget_usd))
                print(f"  {arm + ':':9}claude {argv_text}")
            for warning in case.warnings:
                print(f"  warning: {warning}")
        return 0
    return run_suite(cases, args)


# --- running ---------------------------------------------------------------------------

def claude_version(claude):
    try:
        return subprocess.run([claude, "--version"], text=True, capture_output=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def parse_transcript(text):
    """(last message, tool uses, cost, turns, is_error) from stream-json lines."""
    last, tools, cost, turns, is_error = "", [], 0.0, 0, False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        kind = message.get("type")
        if kind == "assistant":
            content = (message.get("message") or {}).get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools.append({"name": str(block.get("name")), "input": block.get("input") or {}})
        elif kind == "result":
            last = str(message.get("result") or "")
            cost = float(message.get("total_cost_usd") or 0)
            turns = int(message.get("num_turns") or 0)
            is_error = bool(message.get("is_error"))
    return last, tools, cost, turns, is_error


def snapshot(workspace):
    return {str(p.relative_to(workspace)) for p in Path(workspace).rglob("*") if p.is_file()}


def execute_run(case, arm, index, args, claude, workspaces, hooks_brain):
    """One headless session in a fresh workspace. Returns the arm entry for result.json."""
    workspace = workspaces / f"{case.name}-{arm}-{index}"
    workspace.mkdir(parents=True, exist_ok=True)
    model = resolve_model(case, args.model)
    entry = {"model": model, "cost_usd": 0.0, "turns": 0, "is_error": False, "skipped": False,
             "graders": [], "_last": "", "_tools": [], "_created": set(), "_error": None}
    env = dict(os.environ, GENTIC_BRAIN=str(hooks_brain))
    before = snapshot(workspace)
    try:
        with open(os.devnull) as devnull:
            proc = subprocess.run([claude, *claude_argv(case, arm, model, args.max_budget_usd)],
                                  cwd=str(workspace), env=env, stdin=devnull, text=True,
                                  capture_output=True, timeout=case.timeout_seconds)
    except subprocess.TimeoutExpired:
        entry["is_error"] = True
        entry["_error"] = f"timeout after {case.timeout_seconds}s"
        entry["_created"] = snapshot(workspace) - before
        return entry
    last, tools, cost, turns, is_error = parse_transcript(proc.stdout)
    entry.update({"cost_usd": cost, "turns": turns, "is_error": is_error or proc.returncode != 0,
                  "_last": last, "_tools": tools, "_created": snapshot(workspace) - before})
    if proc.returncode != 0 and not entry["_error"]:
        entry["_error"] = f"claude exited {proc.returncode}: {proc.stderr.strip()[:300]}"
    return entry


def public(entry):
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def run_suite(cases, args):
    suite = time.strftime("%Y%m%d-%H%M%S")
    results_dir = Path(args.evals_dir) / "results" / suite
    workspaces = results_dir / "workspaces"
    workspaces.mkdir(parents=True, exist_ok=True)
    hooks_brain = results_dir / "hooks-brain.sqlite"
    claude = shutil.which("claude")
    report = {"suite": suite, "claude_version": claude_version(claude),
              "model": args.model or DEFAULT_MODEL, "install_in_sync": not args.skip_install_check,
              "warnings": [], "cases": [], "totals": {}}
    for case in cases:
        report["warnings"] += case.warnings
        entry = {"name": case.name, "tags": case.tags, "arms": {}}
        for arm in arms_for(args.arm):
            entry["arms"][arm] = []
            for index in range(args.runs or case.runs):
                result = execute_run(case, arm, index, args, claude, workspaces, hooks_brain)
                entry["arms"][arm].append(public(result))
        report["cases"].append(entry)
        print(f"{case.name:28}" + "  ".join(f"{arm} ran {len(runs)}" for arm, runs in entry["arms"].items()))
    (results_dir / "result.json").write_text(json.dumps(report, indent=2, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
