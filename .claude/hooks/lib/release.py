#!/usr/bin/env python3
"""The release lane's deterministic half: what a pull request's checks say, and a merge that
refuses on its own.

Four modes over `gh`, every one a script's answer rather than an agent's memory:

  checks       one line per check, a summary line, and an exit code that means something
  wait         poll `checks` until it settles, within a ceiling
  failed-logs  the failing jobs' logs, last N lines each
  merge        gated four ways — grant, own repository, mergeable PR, green — then `gh pr merge`

Deterministic: the same inputs produce the same `gh` argv; nothing is cached or retried; the
only clock in the output is `wait`'s elapsed-seconds prefix. Not a hot-path hook, so
`subprocess` is fine here.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_conventions  # noqa: E402

# Fibonacci-derived balancing values (house rule).
DEFAULT_TIMEOUT = 1597   # seconds a `wait` may take
DEFAULT_INTERVAL = 21    # seconds between polls
DEFAULT_LINES = 89       # log lines per failing job

GREEN = {"pass", "skipping"}
RED = {"fail", "cancel"}
NO_CHECKS = "no checks reported on the"
JOB_LINK = re.compile(r"/actions/runs/(\d+)/job/(\d+)")

EXIT_GREEN, EXIT_RED, EXIT_PENDING, EXIT_NONE, EXIT_TIMEOUT, EXIT_NO_GH, EXIT_GH_ERROR = 0, 1, 2, 3, 4, 5, 6


def gh_path():
    return shutil.which("gh")


def gh(args, repo=None):
    """Run one `gh` command. Returns (returncode, stdout, stderr)."""
    argv = [gh_path(), *args]
    if repo:
        argv += ["--repo", repo]
    proc = subprocess.run(argv, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def fetch_checks(pr, repo):
    """(exit code, checks). Exit 3 when there are none, 6 when gh failed for any other reason."""
    code, out, err = gh(["pr", "checks", str(pr), "--json", "name,state,bucket,link,workflow"], repo)
    if code != 0:
        if NO_CHECKS in err:
            return EXIT_NONE, []
        sys.stderr.write(err if err.endswith("\n") else err + "\n")
        return EXIT_GH_ERROR, []
    try:
        checks = json.loads(out or "[]")
    except ValueError:
        sys.stderr.write("gh pr checks returned no JSON\n")
        return EXIT_GH_ERROR, []
    if not checks:
        return EXIT_NONE, []
    return None, checks


def verdict(checks):
    buckets = [str(c.get("bucket", "")) for c in checks]
    if any(b in RED for b in buckets):
        return EXIT_RED
    if any(b == "pending" for b in buckets):
        return EXIT_PENDING
    if all(b in GREEN for b in buckets):
        return EXIT_GREEN
    return EXIT_PENDING


def summary(checks):
    counts = {k: sum(1 for c in checks if c.get("bucket") == k) for k in ("pass", "fail", "pending", "skipping", "cancel")}
    return "  ".join(f"{k}: {v}" for k, v in counts.items())


def cmd_checks(args):
    code, checks = fetch_checks(args.pr, args.repo)
    if code is not None:
        if code == EXIT_NONE:
            print(summary([]))
        return code
    for check in checks:
        print(f"{check.get('bucket', '?'):9} {check.get('name', '?')}  {check.get('link', '')}")
    print(summary(checks))
    return verdict(checks)


def cmd_wait(args):
    start = time.monotonic()
    while True:
        code, checks = fetch_checks(args.pr, args.repo)
        elapsed = int(time.monotonic() - start)
        if code == EXIT_GH_ERROR:
            return EXIT_GH_ERROR
        if code == EXIT_NONE:
            print(f"{elapsed:4d}s  {summary([])}  (no checks yet)")
        else:
            print(f"{elapsed:4d}s  {summary(checks)}")
            state = verdict(checks)
            if state in (EXIT_GREEN, EXIT_RED):
                return state
        if time.monotonic() - start >= args.timeout:
            print(f"{elapsed:4d}s  timeout after {args.timeout}s")
            return EXIT_TIMEOUT
        time.sleep(args.interval)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("checks", "wait", "failed-logs", "merge"))
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", default=None, help="OWNER/NAME, passed to every gh call")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument("--lines", type=int, default=DEFAULT_LINES)
    return parser


COMMANDS = {"checks": cmd_checks, "wait": cmd_wait}


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not gh_path():
        sys.stderr.write("gh not found\n")
        return EXIT_NO_GH
    handler = COMMANDS.get(args.mode)
    if handler is None:
        sys.stderr.write(f"{args.mode}: not implemented\n")
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
