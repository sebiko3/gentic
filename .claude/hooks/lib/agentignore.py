"""`.agentignore` — per-project declarations of what Claude may read and modify.

Format (gitignore-shaped, with a read/write axis):

    secrets/            # bare: no read, no write
    *.pem

    [read-only]         # readable, never modified
    vendor/

    [no-read]           # writable, never read
    .env.production

    !secrets/README.md  # re-allow both

Rules are collected from every `.agentignore` between the repo root and the target file, with
nearer files appended later so they win. The last matching rule decides.

This is an accident-preventer, not a security boundary — see the README. It fails **open**: an
unreadable or malformed file warns and allows, because a typo must not block every file operation
in a repo.
"""

import fnmatch
import re
from pathlib import Path

FILENAME = ".agentignore"

SECTIONS = {
    "deny": (False, False),
    "read-only": (True, False),
    "readonly": (True, False),
    "no-read": (False, True),
    "noread": (False, True),
    "no-write": (True, False),
}

_HEADER = re.compile(r"^\[([^\]]+)\]$")
_cache = {}


class Rule:
    """One pattern plus the verdict it confers."""

    __slots__ = ("pattern", "base", "read", "write", "source", "_regex")

    def __init__(self, pattern, base, read, write, source):
        self.pattern = pattern
        self.base = base
        self.read = read
        self.write = write
        self.source = source
        self._regex = _compile(pattern)

    def matches(self, path):
        """True when `path` (absolute, normalised) falls under this rule."""
        try:
            relative = Path(path).relative_to(self.base).as_posix()
        except ValueError:
            return False
        return self._regex.match(relative) is not None

    def __repr__(self):
        return f"Rule({self.pattern!r}, read={self.read}, write={self.write})"


def _compile(pattern):
    """Translate a gitignore-subset pattern into a regex over repo-relative POSIX paths."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    directory_only = pattern.endswith("/")
    body = pattern.strip("/") if pattern.startswith("/") else pattern.rstrip("/")

    # A pattern with no slash matches the basename at any depth.
    prefix = "" if anchored else r"(?:.*/)?"

    parts = []
    for segment in body.split("/"):
        if segment == "**":
            parts.append(r".*")
        else:
            escaped = fnmatch.translate(segment)
            # fnmatch wraps in (?s:...)\Z and lets * cross '/', which we must not allow.
            escaped = escaped.replace(r"(?s:", "").replace(r")\Z", "")
            escaped = escaped.replace(".*", "[^/]*")
            parts.append(escaped)
    core = "/".join(parts).replace("[^/]*/[^/]*/", ".*/")
    # A directory pattern, or any matched directory, also covers everything beneath it.
    suffix = "(?:/.*)?" if directory_only else "(?:/.*)?"
    return re.compile(f"^{prefix}{core}{suffix}$")


def parse(text, base, source):
    """Parse `.agentignore` text into an ordered list of Rules."""
    rules = []
    read, write = SECTIONS["deny"]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        header = _HEADER.match(line)
        if header:
            key = header.group(1).strip().lower()
            if key in SECTIONS:
                read, write = SECTIONS[key]
            continue
        if line.startswith("!"):
            pattern = line[1:].strip()
            if pattern:
                rules.append(Rule(pattern, base, True, True, source))
            continue
        rules.append(Rule(line, base, read, write, source))
    return rules


def resolve(rules, path):
    """Apply rules to a path; the last match wins. Returns the verdict and the rule behind it."""
    verdict = {"read": True, "write": True, "rule": None}
    normalised = str(Path(path))
    for rule in rules:
        if rule.matches(normalised):
            verdict = {"read": rule.read, "write": rule.write, "rule": rule}
    return verdict


def _repo_root(start):
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _load(path):
    """Parsed rules for one `.agentignore`, cached. Returns [] if unreadable or malformed."""
    key = str(path)
    if key not in _cache:
        try:
            _cache[key] = parse(path.read_text(errors="strict"), base=str(path.parent), source=key)
        except Exception:
            _cache[key] = []  # fail open
    return _cache[key]


def rules_for(path):
    """Every rule applying to `path`, outermost `.agentignore` first so nearer files win.

    Every filesystem call here is inside the guard: `resolve()` is lenient about absurd paths
    on macOS but `is_dir()` and `exists()` stat, and anything over PATH_MAX raises ENAMETOOLONG.
    Failing open is the contract, so one bad path must not raise out of this function.
    """
    try:
        target = Path(path).resolve()
        start = target if target.is_dir() else target.parent
        root = _repo_root(start)

        directories = []
        for candidate in (start, *start.parents):
            directories.append(candidate)
            if root is not None and candidate == root:
                break
            if root is None and candidate == candidate.parent:
                break

        rules = []
        for directory in reversed(directories):  # outermost first
            ignore_file = directory / FILENAME
            if ignore_file.is_file():
                rules.extend(_load(ignore_file))
        return rules
    except Exception:
        return []


def permissions_for(path):
    """`{"read": bool, "write": bool, "rule": Rule|None}` for an absolute or relative path."""
    try:
        target = Path(path).resolve()
    except Exception:
        return {"read": True, "write": True, "rule": None}
    return resolve(rules_for(target), target)
