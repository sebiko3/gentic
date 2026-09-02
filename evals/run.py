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
DEFAULT_RUN_BUDGET = 3.0
DEFAULT_SUITE_BUDGET = 21.0
DEFAULT_MODEL = "sonnet"
DEFAULT_TOOLS = ["Read", "Glob", "Grep", "Write", "Edit", "Bash"]

# Every flag this runner emits, minus one: preflight refuses to launch if `claude --help`
# lacks any of these. `--max-turns` is emitted too but cannot be checked this way — Claude Code
# 2.1.258 accepts it (a one-turn smoke run returned num_turns 1) while its --help never lists
# it, and the CLI ignores unknown flags rather than rejecting them, so there is no cheaper probe.
REQUIRED_FLAGS = ("--output-format", "--verbose", "--max-budget-usd",
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
        elif (len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'"
              and value[0] not in value[1:-1]):
            # Outer quotes are stripped only when the value holds no other such quote;
            # `"subagent_type": "x"` stays verbatim.
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


RUN_ARTIFACTS = {"transcript.jsonl", "stderr.txt"}   # written by the runner, never "created"


def parse_transcript(text):
    """Facts from stream-json lines: result text, subtype, tool uses, cost, turns, is_error."""
    last, tools, cost, turns, is_error, subtype, last_text = "", [], 0.0, 0, False, "", ""
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
            texts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tools.append({"name": str(block.get("name")), "input": block.get("input") or {}})
                elif block.get("type") == "text" and str(block.get("text") or "").strip():
                    texts.append(str(block["text"]))
            if texts:
                last_text = "\n".join(texts)
        elif kind == "result":
            last = str(message.get("result") or "")
            cost = float(message.get("total_cost_usd") or 0)
            turns = int(message.get("num_turns") or 0)
            is_error = bool(message.get("is_error"))
            subtype = str(message.get("subtype") or "")
    # The result text wins; an exhausted session has none, so its last spoken text stands in.
    return {"result": last or last_text, "tools": tools, "cost": cost, "turns": turns,
            "is_error": is_error, "subtype": subtype}


def snapshot(workspace):
    return {str(p.relative_to(workspace)) for p in Path(workspace).rglob("*")
            if p.is_file() and p.name not in RUN_ARTIFACTS}


def scaffold(case, workspace):
    """Run the case's scaffold script in the workspace. Returns an error string or None."""
    if not case.scaffold_script:
        return None
    script = case.directory / case.scaffold_script
    env = dict(os.environ, EVAL_CASE_DIR=str(case.directory), EVAL_REPO=str(REPO))
    try:
        proc = subprocess.run(["bash", str(script)], cwd=str(workspace), env=env, text=True,
                              capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"scaffold failed: {exc}"
    if proc.returncode != 0:
        return f"scaffold failed ({proc.returncode}): {proc.stderr.strip()[:300]}"
    return None


def execute_run(case, arm, index, args, claude, workspaces, hooks_brain):
    """One headless session in a fresh workspace. Returns the arm entry for result.json."""
    workspace = workspaces / f"{case.name}-{arm}-{index}"
    workspace.mkdir(parents=True, exist_ok=True)
    model = resolve_model(case, args.model)
    entry = {"model": model, "cost_usd": 0.0, "turns": 0, "is_error": False, "exhausted": False,
             "skipped": False, "transcript": None, "stderr": None,
             "graders": [], "_last": "", "_tools": [], "_created": set(), "_error": None}
    env = dict(os.environ, GENTIC_BRAIN=str(hooks_brain))
    problem = scaffold(case, workspace)
    if problem:
        entry["is_error"] = True
        entry["_error"] = problem
        return entry
    # Taken after the scaffold: what the scaffold placed is never "created" by the agent.
    before = snapshot(workspace)
    try:
        with open(os.devnull) as devnull:
            proc = subprocess.run([claude, *claude_argv(case, arm, model, args.max_budget_usd)],
                                  cwd=str(workspace), env=env, stdin=devnull, text=True,
                                  capture_output=True, timeout=case.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        entry["is_error"] = True
        entry["_error"] = f"timeout after {case.timeout_seconds}s"
        entry["_created"] = snapshot(workspace) - before
        keep_output(entry, workspace, workspaces.parent, exc.stdout, exc.stderr)
        return entry
    entry["_created"] = snapshot(workspace) - before
    keep_output(entry, workspace, workspaces.parent, proc.stdout, proc.stderr)
    facts = parse_transcript(proc.stdout)
    entry.update({"cost_usd": facts["cost"], "turns": facts["turns"], "_last": facts["result"], "_tools": facts["tools"]})
    if facts["subtype"] == "error_max_turns":
        # The session ran out of turns: what it created and did is real, so it is graded.
        entry["exhausted"] = True
    elif proc.returncode != 0 or facts["is_error"]:
        entry["is_error"] = True
        entry["_error"] = f"claude exited {proc.returncode}: {proc.stderr.strip()[:300]}"
    return entry


def keep_output(entry, workspace, results_dir, stdout, stderr):
    """Raw stdout and stderr next to the workspace, after the created-file snapshot."""
    def text(value):
        if value is None:
            return ""
        return value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    for key, name, value in (("transcript", "transcript.jsonl", stdout), ("stderr", "stderr.txt", stderr)):
        path = workspace / name
        path.write_text(text(value))
        entry[key] = str(path.relative_to(results_dir))


# --- grading ---------------------------------------------------------------------------

RE_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def evaluate(grader, entry):
    """One grader's verdict over a finished run. Never raises."""
    fields = grader.fields
    kind = grader.type
    try:
        if kind == "regex":
            pattern = str(fields.get("pattern", ""))
            flags = 0
            for letter in str(fields.get("flags", "")):
                flags |= RE_FLAGS.get(letter, 0)
            target = str(fields.get("target", "last_message"))
            text = "\n".join(sorted(entry["_created"])) if target == "files" else entry["_last"]
            found = re.search(pattern, text, flags) is not None
            wanted = str(fields.get("match", "contains")) != "not_contains"
            passed = found == wanted
            detail = f"{'matched' if found else 'no match for'} /{pattern}/ in {target}"
        elif kind == "file_exists":
            pattern = str(fields.get("path", ""))
            hits = sorted(p for p in entry["_created"] if fnmatch.fnmatchcase(p, pattern))
            passed = bool(hits)
            detail = f"created {', '.join(hits)}" if hits else f"no created file matches {pattern}"
        elif kind == "tool_used":
            tool = str(fields.get("tool", ""))
            names = {"Task", "Agent"} if tool in ("Task", "Agent") else {tool}
            input_match = fields.get("input_match")
            count = 0
            for use in entry["_tools"]:
                if use["name"] not in names:
                    continue
                if input_match and not re.search(str(input_match), json.dumps(use["input"], sort_keys=True)):
                    continue
                count += 1
            low = int(fields.get("min", 1))
            high = fields.get("max")
            passed = count >= low and (high is None or count <= int(high))
            detail = f"{tool} used {count} time(s)"
        else:
            passed, detail = False, f"unsupported grader {kind}"
    except (re.error, ValueError, TypeError) as exc:
        passed, detail = False, f"grader error: {exc}"
    return {"name": grader.name, "type": kind, "passed": bool(passed), "detail": detail}


def skipped_run(case, model):
    return {"model": model, "cost_usd": 0.0, "turns": 0, "is_error": False, "exhausted": False,
            "skipped": True, "transcript": None, "stderr": None,
            "graders": [{"name": g.name, "type": g.type, "passed": False, "detail": "skipped: suite budget"}
                        for g in case.graders],
            "_last": "", "_tools": [], "_created": set(), "_error": "skipped: suite budget"}


def grade(case, entry):
    if entry["_error"]:
        return [{"name": g.name, "type": g.type, "passed": False, "detail": entry["_error"]} for g in case.graders]
    return [evaluate(grader, entry) for grader in case.graders]


def run_score(run):
    graders = run["graders"]
    if run.get("skipped") or not graders:
        return 0.0
    return sum(1 for g in graders if g["passed"]) / len(graders)


def arm_rate(runs):
    scored = [run_score(r) for r in runs if not r.get("skipped")]
    return sum(scored) / len(scored) if scored else 0.0


def counts(runs):
    passed = sum(1 for r in runs for g in r["graders"] if g["passed"])
    total = sum(len(r["graders"]) for r in runs)
    return passed, total


def public(entry):
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def console_line(name, arms, cost):
    parts = [f"{name:28}"]
    for arm in ("with", "without"):
        runs = arms.get(arm)
        if runs is None:
            continue
        if runs and all(r.get("skipped") for r in runs):
            parts.append(f"{arm} skipped: suite budget")
            continue
        passed, total = counts(runs)
        flag = " exhausted" if any(r.get("exhausted") for r in runs) else ""
        parts.append(f"{arm} {passed}/{total} ({arm_rate(runs):.2f}){flag}")
    if "with" in arms and "without" in arms:
        parts.append(f"delta {arm_rate(arms['with']) - arm_rate(arms['without']):+.2f}")
    parts.append(f"${cost:.2f}")
    return "  ".join(parts)


def load_brain():
    """gentic's brain module, imported from the hooks library. None under --no-brain."""
    lib = str(REPO / ".claude" / "hooks" / "lib")
    sys.path.insert(0, lib)
    try:
        import brain  # noqa: F401
    finally:
        sys.path.remove(lib)
    return brain


def installed_files():
    """The skill and agent files the `with` arm actually runs: the installed copies."""
    home = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")
    return sorted(str(p) for p in home.glob("skills/gentic*/SKILL.md")) + sorted(str(p) for p in home.glob("agents/*.md"))


def run_suite(cases, args):
    suite = time.strftime("%Y%m%d-%H%M%S")
    brain = None if args.no_brain else load_brain()
    if brain:
        brain.main(["--project", REPO.name, "run", "start", suite, "--goal", f"eval suite {suite}"])
        files = installed_files()
        if files:
            brain.main(["--project", REPO.name, "stamp", suite, *files])
    results_dir = Path(args.evals_dir) / "results" / suite
    workspaces = results_dir / "workspaces"
    workspaces.mkdir(parents=True, exist_ok=True)
    hooks_brain = results_dir / "hooks-brain.sqlite"
    claude = shutil.which("claude")
    report = {"suite": suite, "claude_version": claude_version(claude),
              "model": args.model or DEFAULT_MODEL, "install_in_sync": not args.skip_install_check,
              "warnings": [], "cases": [], "totals": {}}
    total_cost = 0.0
    skipped = 0
    for case in cases:
        report["warnings"] += case.warnings
        if not case.graders:
            report["warnings"].append(f"{case.name}: no graders; every run scores 0")
        entry = {"name": case.name, "tags": case.tags, "arms": {}, "pass_rate": {}, "delta": None}
        case_cost = 0.0
        for arm in arms_for(args.arm):
            entry["arms"][arm] = []
            for index in range(args.runs or case.runs):
                # The ceiling is checked before launch against the worst case, so the true
                # maximum spend is the suite budget itself, never budget-plus-one-run.
                if total_cost + args.max_budget_usd > args.suite_budget_usd:
                    result = skipped_run(case, resolve_model(case, args.model))
                    skipped += 1
                    print(f"{case.name}: {arm} run {index} skipped: suite budget")
                else:
                    result = execute_run(case, arm, index, args, claude, workspaces, hooks_brain)
                    result["graders"] = grade(case, result)
                case_cost += result["cost_usd"]
                total_cost += result["cost_usd"]   # per run, so the ceiling sees every run
                entry["arms"][arm].append(public(result))
                if brain:
                    run_id = brain.record_eval_run(str(REPO), suite, case.name, arm, index, result["model"],
                                                   result["cost_usd"], result["turns"], result["is_error"],
                                                   result["skipped"], result.get("exhausted", False))
                    for verdict in result["graders"] if run_id else ():
                        brain.record_eval_grader(run_id, verdict["name"], verdict["type"], verdict["passed"], verdict["detail"])
            entry["pass_rate"][arm] = round(arm_rate(entry["arms"][arm]), 4)
        if "with" in entry["arms"] and "without" in entry["arms"]:
            entry["delta"] = round(entry["pass_rate"]["with"] - entry["pass_rate"]["without"], 4)
        report["cases"].append(entry)
        print(console_line(case.name, entry["arms"], case_cost))
    suite_rates = {}
    for arm in arms_for(args.arm):
        rates = [c["pass_rate"][arm] for c in report["cases"] if arm in c["pass_rate"]]
        suite_rates[arm] = round(sum(rates) / len(rates), 4) if rates else 0.0
    delta = round(suite_rates["with"] - suite_rates["without"], 4) if len(suite_rates) == 2 else None
    below = [c["name"] for c in report["cases"] if "with" in c["pass_rate"] and c["pass_rate"]["with"] < args.threshold]
    code = 2 if skipped else 1 if below else 0
    report["totals"] = {"pass_rate": suite_rates, "delta": delta, "cost_usd": round(total_cost, 4),
                        "skipped": skipped, "exit": code}
    (results_dir / "result.json").write_text(json.dumps(report, indent=2, default=list))
    summary = "  ".join(f"{arm} {rate:.2f}" for arm, rate in suite_rates.items())
    print(f"{'suite ' + suite:28}{summary}" + (f"  delta {delta:+.2f}" if delta is not None else "")
          + f"  ${total_cost:.2f}  exit {code}")
    if below:
        print("below threshold: " + ", ".join(below))
    if brain:
        brain.main(["--project", REPO.name, "run", "finish", suite, "--outcome",
                    "stopped" if report["totals"]["skipped"] else "done"])
    return code


if __name__ == "__main__":
    sys.exit(main())
