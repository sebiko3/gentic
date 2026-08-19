#!/usr/bin/env python3
"""Branch and commit naming that belongs to the project, not to gentic.

gentic's own conventions - a `gentic/<slug>` branch, a `gentic(<slug>): ...` commit subject -
were written into machine-wide rules, so every repository got them whether or not it had
adopted the workflow. A project with its own `feat/` convention got gentic's instead.

This decides per project:

  adopted                      -> gentic/<slug>      gentic(<slug>): <message>
  unadopted, dominant prefix P -> P/<slug>           <message>
  unadopted, no usable prefix  -> <slug>             <message>

Adoption is decided first and never depends on git: falling back to a bare slug because a git
call failed would silently rename branches in the one repository that does want the prefix.

Not a hot-path hook - nothing in hooks/*.py imports this - so calling git through subprocess is
fine here, unlike in common.py.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

MARKER = "gentic/<slug>"
MARKER_FILE = "CLAUDE.md"
# Must open with an alphanumeric: `..` is otherwise a valid-looking prefix and yields `../x`.
SAFE_PREFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MIN_COUNT = 2


def project_root(start):
    """Nearest ancestor containing a `.git` entry, or `start` itself.

    `.git` is a directory in a normal checkout and a file in a linked worktree; both count.
    """
    try:
        current = Path(start).resolve()
    except Exception:
        return None
    if not current.is_dir():
        return None
    for candidate in (current, *current.parents):
        try:
            if (candidate / ".git").exists():
                return candidate
        except Exception:
            continue
    return current


def is_adopted(root):
    """True when the repository root's CLAUDE.md declares the gentic branch rule.

    A literal substring match, deliberately: it is the line the install instructions tell
    people to copy. Wording it differently means "not adopted", which is the safe direction -
    the workflow declines to impose rather than imposing by accident.
    """
    if root is None:
        return False
    try:
        return MARKER in (root / MARKER_FILE).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


def _branches(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "for-each-ref", "--format=%(refname:short)", "refs/heads"],
            text=True, capture_output=True, timeout=5,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _default_branch(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "symbolic-ref", "--short", "HEAD"],
            text=True, capture_output=True, timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def dominant_prefix(root):
    """The project's own branch prefix, or None when it has no clear one.

    Plurality over local heads, excluding the current/default branch. A tie or a single
    sighting yields None: inventing a convention for a project that has none is the behaviour
    this module exists to remove.
    """
    if root is None:
        return None
    skip = _default_branch(root)
    counts = {}
    for branch in _branches(root):
        if branch == skip or "/" not in branch:
            continue
        prefix = branch.split("/", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    if not counts:
        return None

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    winner, count = ranked[0]
    if count < MIN_COUNT:
        return None
    if len(ranked) > 1 and ranked[1][1] == count:
        return None
    # The result is handed to `git checkout -b`; anything but a plain name is discarded.
    return winner if SAFE_PREFIX.match(winner) else None


def branch_name(slug, root):
    if is_adopted(root):
        return f"gentic/{slug}"
    prefix = dominant_prefix(root)
    return f"{prefix}/{slug}" if prefix else slug


def commit_subject(slug, message, root):
    return f"gentic({slug}): {message}" if is_adopted(root) else message


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("branch", "commit"))
    parser.add_argument("slug")
    parser.add_argument("message", nargs="?", default="")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)

    root = project_root(args.root if args.root is not None else Path.cwd())
    if args.mode == "branch":
        print(branch_name(args.slug, root))
    else:
        print(commit_subject(args.slug, args.message, root))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # Never break a run over a naming helper: fall back to the least opinionated answer.
        argv = sys.argv[1:]
        if argv and argv[0] == "commit":
            print(argv[2] if len(argv) > 2 else "")
        elif len(argv) > 1:
            print(argv[1])
        sys.exit(0)
