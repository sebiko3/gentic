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

from lib import agentignore, common  # noqa: E402

# What each tool needs permission to do.
READ_TOOLS = {"Read", "NotebookRead"}
WRITE_TOOLS = {"Write", "NotebookEdit"}
READ_WRITE_TOOLS = {"Edit", "MultiEdit"}  # an edit reads the file before changing it

MUTATING = re.compile(
    r"(^|[|;&]\s*)(rm|mv|cp|dd|install|truncate|chmod|chown|ln)\b"
    r"|\bsed\s+(-[a-zA-Z]*\s+)*-i\b"
    r"|\btee\b"
    r"|>>?\s*\S",
    re.I,
)

RULES = [
    (
        re.compile(r"\bgit\s+push\b(?=.*\s(--force|-f)\b)(?!.*--force-with-lease)", re.I),
        "`git push --force` overwrites remote history irreversibly. "
        "Use `--force-with-lease`, which refuses if someone else has pushed.",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
        "`git reset --hard` discards uncommitted work with no recovery path. "
        "Stash or commit first, or use `git reset --soft`.",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-z]*f[a-z]*d|\bgit\s+clean\s+-[a-z]*d[a-z]*f", re.I),
        "`git clean -fd` permanently deletes untracked files, including ones never committed. "
        "Run it with `-n` first to see what would go.",
    ),
]

RECURSIVE_RM = re.compile(r"\brm\b[^|;&]*?\s-[a-zA-Z]*(rf|fr|[rR]\s+-f|f\s+-[rR])[a-zA-Z]*\s+(?P<target>[^\s|;&]+)", re.I)

DANGEROUS_TARGETS = re.compile(
    r"^(/|~|~/|\$HOME/?|\$\{HOME\}/?|/Users/[^/]+/?|/home/[^/]+/?|/\*|/etc/?|/usr/?|/var/?)$"
)


_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def unquoted(command):
    """The command with quoted sections blanked out.

    A command that merely *mentions* `git push --force` inside a string is not an invocation
    of it. Matching the raw text blocked legitimate work (echo, grep, printf, heredocs), which
    is exactly how a guard earns a reputation for crying wolf and gets disabled.
    """
    return _QUOTED.sub(" ", command)


def dangerous_rm(command):
    for match in RECURSIVE_RM.finditer(command):
        target = match.group("target").strip("'\"")
        if DANGEROUS_TARGETS.match(target):
            return target
    return None


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
        return deny(reason) if reason else None

    if tool != "Bash":
        return
    command = str(tool_input.get("command") or "")
    if not command:
        return

    scannable = unquoted(command)
    for pattern, reason in RULES:
        if pattern.search(scannable):
            return deny(reason)

    target = dangerous_rm(scannable)
    if target:
        return deny(
            f"`rm -rf {target}` would recursively delete a home or system directory. "
            "Name a specific project path instead."
        )

    reason = check_bash(command, cwd)
    if reason:
        return deny(reason)


if __name__ == "__main__":
    common.safe_main(main)
