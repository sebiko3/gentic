#!/usr/bin/env python3
"""PreToolUse — refuse actions the project or the user has declared off-limits.

Two guards share this hook:

1. **Destructive commands.** The small set of Bash invocations that destroy work irreversibly,
   encoding the rule from ~/.claude/CLAUDE.md at the harness level so it holds even when the
   model has lost that context.

2. **`.agentignore`.** Per-project declarations of which paths may be read and which may be
   modified, enforced before the tool runs rather than after the damage.

Both are deliberately narrow. Everything not covered passes through with no decision at all —
a guard that fires on ordinary work would just be trained away.
"""

import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import agentignore, common, token_efficiency  # noqa: E402

# What each tool needs permission to do.
READ_TOOLS = {"Read", "NotebookRead"}
WRITE_TOOLS = {"Write", "NotebookEdit"}
READ_WRITE_TOOLS = {"Edit", "MultiEdit"}  # an edit reads the file before changing it

MUTATING = re.compile(
    r"(^|[|;&]\s*)(rm|mv|cp|dd|install|truncate|chmod|chown|ln)\b"
    r"|\bsed\s+(-[a-zA-Z]*\s+)*-i\b"
    r"|\btee\b"
    r"|(?<![0-9&])>>?\s*(?![&|])\S",
    re.I,
)

def _short_flags(argv):
    """Every letter appearing in a short-flag cluster: ["-f", "-rd"] -> {"f", "r", "d"}."""
    letters = set()
    for arg in argv:
        if arg.startswith("-") and not arg.startswith("--"):
            letters.update(arg[1:])
    return letters


def is_force_push(argv):
    if argv[:2] != ["git", "push"]:
        return False
    if any(a.startswith("--force-with-lease") for a in argv):
        return False
    return "--force" in argv or "f" in _short_flags(argv)


def is_hard_reset(argv):
    return argv[:2] == ["git", "reset"] and "--hard" in argv


def is_destructive_clean(argv):
    """`git clean` that both forces and recurses into directories, and is not a dry run."""
    if argv[:2] != ["git", "clean"]:
        return False
    flags = _short_flags(argv)
    if "n" in flags or "--dry-run" in argv:
        return False
    return ("f" in flags or "--force" in argv) and "d" in flags


RULES = [
    (
        is_force_push,
        "`git push --force` overwrites remote history irreversibly. "
        "Use `--force-with-lease`, which refuses if someone else has pushed.",
    ),
    (
        is_hard_reset,
        "`git reset --hard` discards uncommitted work with no recovery path. "
        "Stash or commit first, or use `git reset --soft`.",
    ),
    (
        is_destructive_clean,
        "`git clean -fd` permanently deletes untracked files, including ones never committed. "
        "Run it with `-n` first to see what would go.",
    ),
]

DANGEROUS_TARGETS = re.compile(
    r"^(/|~|~/|\$HOME/?|\$\{HOME\}/?|/Users/[^/]+/?|/home/[^/]+/?|/\*|/etc/?|/usr/?|/var/?)$"
)

_SEPARATORS = {";", "&", "&&", "|", "||", "\n", "&|"}


def command_argvs(command):
    """Split a shell line into one argv list per command.

    Deciding on argv is what makes `git reset "--hard"` and `git reset --hard` the same
    invocation while `echo "git reset --hard"` stays a single argument to echo. The previous
    approach blanked quoted spans before matching raw text, which got the second case right and
    the first catastrophically wrong: `rm -rf "$HOME"`, the quoting shellcheck asks for, was
    invisible to the guard.

    Returns None when the line cannot be tokenised, so the caller can fall back rather than
    treat an unparseable command as harmless.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    argvs, current = [], []
    try:
        for token in lexer:
            if token in _SEPARATORS or set(token) <= {";", "&", "|"} and token:
                if current:
                    argvs.append(current)
                    current = []
            else:
                current.append(token)
    except ValueError:
        return None
    if current:
        argvs.append(current)
    return argvs


def dangerous_rm(argv):
    """The home or system directory a recursive-force rm would delete, if any."""
    if not argv or argv[0] != "rm":
        return None
    flags = _short_flags(argv)
    if not (({"r", "R"} & flags) and "f" in flags):
        return None
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        if DANGEROUS_TARGETS.match(arg):
            return arg
    return None


def duplicate_read_guard(payload, tool_input, cwd):
    """Deny a repeat Read of an unchanged file — once per path, valve always open.

    State is saved *before* blocking (the verification gate's pattern): the fired-marker must
    be durable by the time the model retries, so the retry passes unconditionally.
    """
    session_id = payload.get("session_id")
    if not session_id:
        return None
    state = common.load_state(session_id)
    session = state.setdefault("session", {})
    reason = token_efficiency.check_read(session, tool_input, cwd)
    common.save_state(session_id, state)
    if reason:
        common.block(reason)


def bare_cat_guard(payload, command, cwd):
    """Deny a bare cat of one large file — once per path, same valve ledger as the read guard."""
    session_id = payload.get("session_id")
    if not session_id:
        return None
    state = common.load_state(session_id)
    session = state.setdefault("session", {})
    reason = token_efficiency.check_cat(session, command, cwd)
    common.save_state(session_id, state)
    if reason:
        common.block(reason)


def deny(reason):
    common.emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    })


def refusal(path, verdict, action):
    rule = verdict.get("rule")
    where = Path(rule.source).name if rule else agentignore.FILENAME
    pattern = rule.pattern if rule else "?"
    return (
        f"{agentignore.FILENAME} forbids {action} `{path}` — matched by `{pattern}` "
        f"in {rule.source if rule else where}. "
        f"Do not work around this. If the access is genuinely needed, ask the user to edit that file."
    )


def check_path(path, need_read, need_write, cwd):
    """Deny reason for touching `path`, or None."""
    if not path:
        return None
    resolved = Path(path)
    if not resolved.is_absolute() and cwd:
        resolved = Path(cwd) / resolved
    verdict = agentignore.permissions_for(resolved)
    if need_read and not verdict["read"]:
        return refusal(path, verdict, "reading")
    if need_write and not verdict["write"]:
        return refusal(path, verdict, "modifying")
    return None


# Filesystem limits. macOS: PATH_MAX 1024, NAME_MAX 255 (Linux is more generous).
# Anything beyond these cannot name a real file, and stat-ing it raises ENAMETOOLONG.
PATH_MAX = 1024
NAME_MAX = 255


def plausible_path(token):
    """Could this token name a real file? A pasted code blob cannot."""
    if not token or len(token) > PATH_MAX:
        return False
    if any(ch in token for ch in ("\n", "\r", "\x00")):
        return False
    return all(len(segment) <= NAME_MAX for segment in token.split("/"))


def path_tokens(command):
    """Tokens from a shell command that plausibly name a path."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        if token.startswith("-") or not plausible_path(token):
            continue
        if "/" in token or Path(token).suffix:
            yield token
            continue
        try:
            if Path(token).exists():
                yield token
        except OSError:
            continue


def check_bash(command, cwd):
    """First protected path named by the command, or None.

    One unusable token must never abort the scan — that would let a blob of pasted code mask a
    genuine violation later in the same command.
    """
    mutating = bool(MUTATING.search(command))
    for token in path_tokens(command):
        try:
            reason = check_path(token, need_read=True, need_write=mutating, cwd=cwd)
        except Exception:
            continue
        if reason:
            return reason
    return None


def main():
    payload = common.read_payload()
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    cwd = payload.get("cwd")

    if tool in READ_TOOLS or tool in WRITE_TOOLS or tool in READ_WRITE_TOOLS:
        reason = check_path(
            tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path"),
            need_read=tool in READ_TOOLS or tool in READ_WRITE_TOOLS,
            need_write=tool in WRITE_TOOLS or tool in READ_WRITE_TOOLS,
            cwd=cwd,
        )
        if reason:
            return deny(reason)
        if tool == "Read":
            return duplicate_read_guard(payload, tool_input, cwd)
        return None

    if tool != "Bash":
        return
    command = str(tool_input.get("command") or "")
    if not command:
        return

    argvs = command_argvs(command)
    if argvs is None:
        # Unparseable (an unterminated quote, usually). Fall back to splitting the raw text on
        # separators and stripping quote characters: noisier than real tokenisation, but a
        # command we cannot parse must never be waved through.
        argvs = [segment.replace('"', " ").replace("'", " ").split()
                 for segment in re.split(r"[;&|\n]+", command)]

    for argv in argvs:
        for matches, reason in RULES:
            if matches(argv):
                return deny(reason)

        target = dangerous_rm(argv)
        if target:
            return deny(
                f"`rm -rf {target}` would recursively delete a home or system directory. "
                "Name a specific project path instead."
            )

    reason = check_bash(command, cwd)
    if reason:
        return deny(reason)

    bare_cat_guard(payload, command, cwd)


if __name__ == "__main__":
    common.safe_main(main)
