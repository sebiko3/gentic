#!/usr/bin/env python3
"""Branch and commit naming that belongs to the project, not to gentic — and the project's
standing authorizations, which belong to the user.

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

Authorizations (`authorized <action>`) are the one place the answer must fail *closed*: a grant
counts only when the root CLAUDE.md lists the action under `## gentic authorizations` AND the
git root's path is in the machine-side trust file, which only the user writes. A cloned
repository can therefore never grant itself a push.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

MARKER = "gentic/<slug>"
MARKER_FILE = "CLAUDE.md"
AUTH_HEADING = "## gentic authorizations"
VOCABULARY = ("push", "open-pr", "merge-on-green", "deploy-preview", "use-workflow-tool", "spawn-teams")
# Beside the hooks' state directory (~/.claude/state) — derived, so this file embeds no
# machine path literal; the harness pins that.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TRUST_FILE = common.STATE_DIR.parent / "gentic" / "trusted-projects"
GRANT_LINE = re.compile(r"^\s*[-*]\s*([A-Za-z-]+)")
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


def trust_file():
    override = os.environ.get("GENTIC_TRUST")
    return Path(override) if override else TRUST_FILE


def is_trusted(root):
    """True when the git root's absolute path is a line of the machine-side trust file."""
    if root is None:
        return False
    try:
        wanted = str(Path(root).resolve())
        lines = trust_file().read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    return any(line.strip() == wanted for line in lines)


def grants(root):
    """(granted words in document order, problem) from the root CLAUDE.md's section."""
    if root is None:
        return [], "no project root"
    try:
        lines = (root / MARKER_FILE).read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return [], "no CLAUDE.md"
    words, inside, seen = [], False, False
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == AUTH_HEADING:
            inside, seen = True, True
            continue
        if inside and stripped.startswith("## "):
            inside = False
        if not inside:
            continue
        match = GRANT_LINE.match(line)
        if not match:
            continue
        word = match.group(1).lower()
        if word not in VOCABULARY:
            print(f"ignored: {word}", file=sys.stderr)
        elif word not in words:
            words.append(word)
    if not seen:
        return [], "no section"
    return words, None


def authorized(action, root, list_only=False):
    """Exit code for `authorized`: 0 when granted and trusted, 1 otherwise. Prints yes/no."""
    if not is_trusted(root):
        print(f"project not trusted: {root} (add its path to {trust_file()})", file=sys.stderr)
        if list_only:
            return 0
        print("no")
        return 1
    words, problem = grants(root)
    if list_only:
        for word in words:
            print(word)
        if problem:
            print(problem, file=sys.stderr)
        return 0
    if problem:
        print(problem, file=sys.stderr)
        print("no")
        return 1
    if not action:
        print("action required", file=sys.stderr)
        print("no")
        return 1
    if action.lower() not in VOCABULARY:
        print(f"unknown action {action}", file=sys.stderr)
        print("no")
        return 1
    if action.lower() in words:
        print("yes")
        return 0
    print("not granted", file=sys.stderr)
    print("no")
    return 1


def branch_name(slug, root):
    if is_adopted(root):
        return f"gentic/{slug}"
    prefix = dominant_prefix(root)
    return f"{prefix}/{slug}" if prefix else slug


def commit_subject(slug, message, root):
    return f"gentic({slug}): {message}" if is_adopted(root) else message


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("branch", "commit", "authorized"))
    parser.add_argument("slug", nargs="?", default=None, help="slug, or the action for `authorized`")
    parser.add_argument("message", nargs="?", default="")
    parser.add_argument("--root", default=None)
    parser.add_argument("--list", action="store_true", help="authorized: print the granted, trusted words")
    args = parser.parse_args(argv)

    root = project_root(args.root if args.root is not None else Path.cwd())
    if args.mode == "authorized":
        return authorized(args.slug, root, list_only=args.list)
    if args.slug is None:
        parser.error("slug is required")
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
        # Consent is the exception: an unexpected failure answers `no`.
        argv = sys.argv[1:]
        if argv and argv[0] == "authorized":
            print("no")
            sys.exit(1)
        if argv and argv[0] == "commit":
            print(argv[2] if len(argv) > 2 else "")
        elif len(argv) > 1:
            print(argv[1])
        sys.exit(0)
