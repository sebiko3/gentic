#!/usr/bin/env python3
"""gentic's persistent brain: one SQLite file the workflow may use as it likes.

Structured memory (events the hooks record, decisions, lessons, runs, skill-version stamps)
sits next to free-form notes with full-text recall, and an unrestricted ``sql`` command, so
the agent is never limited to the tables it was given.

Two callers, two contracts:

* Hooks import :func:`record_event` on the hot path. It is best-effort by design — a missing,
  locked or unwritable brain returns ``False`` within the busy timeout and never raises.
* Skills and the agent use the CLI (``python3 <this file> <command> ...``). It reports errors
  on stderr with exit 1 and is not on any hot path.

Every row carries a ``project`` key (the basename of the git root), because the file is
machine-wide. ``GENTIC_BRAIN`` overrides the location; tests and the harness rely on that.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path.home() / ".claude" / "gentic" / "brain.sqlite"

# Fibonacci-derived balancing values (house rule).
BUSY_TIMEOUT = 0.034   # seconds a hot-path write may wait on a lock
RECALL_LIMIT = 8       # notes printed by default
DETAIL_CHARS = 300     # matches post_tool_use.py's command trim
PREFERENCE_MIN = 2     # agreeing user decisions before a preference is learned

EVENT_KINDS = ("red", "verification", "gate_block", "nudge_tdd", "nudge_review", "nudge_spend")

DESTRUCTIVE = re.compile(r"^\s*(drop|delete|update|alter)\b", re.I)

# Credential shapes that routinely ride inside shell commands. The value is replaced, the
# key is kept, so a stored event still says *what* was run.
SECRETS = (
    re.compile(r"(Authorization:\s*(?:(?:Bearer|Basic|Token)\s+)?)\S+", re.I),
    re.compile(r"(--password[= ]|(?:token|password|secret)=|AWS_[A-Z_]+=)\S+", re.I),
)

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS notes ("
    " id INTEGER PRIMARY KEY, ts REAL, project TEXT, run TEXT, key TEXT, body TEXT, tags TEXT)",
    "CREATE TABLE IF NOT EXISTS events ("
    " id INTEGER PRIMARY KEY, ts REAL, project TEXT, session TEXT, kind TEXT, detail TEXT, data TEXT)",
    "CREATE TABLE IF NOT EXISTS decisions ("
    " id INTEGER PRIMARY KEY, ts REAL, project TEXT, run TEXT, topic TEXT, chosen TEXT, source TEXT)",
    "CREATE TABLE IF NOT EXISTS lessons ("
    " id INTEGER PRIMARY KEY, ts REAL, project TEXT, run TEXT, item TEXT, rung INTEGER,"
    " points INTEGER, caught_by TEXT, cause TEXT, note TEXT)",
    "CREATE TABLE IF NOT EXISTS runs ("
    " id INTEGER PRIMARY KEY, project TEXT, slug TEXT, goal TEXT, started REAL, finished REAL,"
    " outcome TEXT, UNIQUE(project, slug))",
    "CREATE TABLE IF NOT EXISTS stamps ("
    " project TEXT, slug TEXT, path TEXT, sha TEXT, ts REAL, PRIMARY KEY(project, slug, path))",
)

FTS_SCHEMA = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5("
    " key, body, content='notes', content_rowid='id')",
    "CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN"
    " INSERT INTO notes_fts(rowid, key, body) VALUES (new.id, new.key, new.body); END",
)


# --- location and identity -------------------------------------------------------------

def db_path():
    override = os.environ.get("GENTIC_BRAIN")
    return Path(override) if override else DEFAULT_PATH


def git_root(start):
    """Nearest ancestor with a `.git` entry, or None. Walks the tree; never shells out."""
    try:
        current = Path(start).resolve()
    except Exception:
        return None
    if not current.is_dir():
        return None
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def project_key(cwd):
    root = git_root(cwd) if cwd else None
    return root.name if root else None


def scrub(text):
    for pattern in SECRETS:
        text = pattern.sub(r"\1***", text)
    return text


# --- connection and schema -------------------------------------------------------------

def fts_wanted():
    return not os.environ.get("GENTIC_BRAIN_NO_FTS")


def has_fts(conn):
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'notes_fts'").fetchone()
    return row is not None


def ensure_schema(conn):
    for statement in SCHEMA:
        conn.execute(statement)
    if fts_wanted() and not has_fts(conn):
        try:
            for statement in FTS_SCHEMA:
                conn.execute(statement)
            conn.execute("INSERT INTO notes_fts(notes_fts) VALUES ('rebuild')")
        except sqlite3.Error:
            # No FTS5 in this build: recall uses LIKE. Notes are still stored.
            pass


def connect(timeout=BUSY_TIMEOUT):
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    ensure_schema(conn)
    return conn


# --- hot path --------------------------------------------------------------------------

def record_event(cwd, session, kind, detail, data=None):
    """Append one event for the project at `cwd`. Best-effort; never raises.

    Returns True when a row was written, False when the brain was unavailable or `cwd` has
    no git root (events without a project would be noise).
    """
    project = project_key(cwd)
    if not project:
        return False
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO events (ts, project, session, kind, detail, data) VALUES (?,?,?,?,?,?)",
            (time.time(), project, session, kind, scrub(str(detail))[:DETAIL_CHARS],
             json.dumps(data) if data is not None else None),
        )
        conn.commit()
    finally:
        conn.close()
    return True


# --- CLI commands ----------------------------------------------------------------------

def when(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M")


def cmd_note(args, conn, project):
    conn.execute(
        "INSERT INTO notes (ts, project, run, key, body, tags) VALUES (?,?,?,?,?,?)",
        (time.time(), project, args.run, args.key, " ".join(args.body), args.tags),
    )
    conn.commit()
    return 0


def cmd_recall(args, conn, project):
    terms = [t for t in " ".join(args.words).split() if t]
    if not terms:
        return 0
    scope_sql = "" if args.all else " AND project = ?"
    scope = () if args.all else (project,)
    if fts_wanted() and has_fts(conn):
        match = " AND ".join('"' + t.replace('"', '""') + '"' for t in terms)
        rows = conn.execute(
            "SELECT id, ts, key, body FROM notes WHERE id IN"
            " (SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)" + scope_sql +
            " ORDER BY id DESC LIMIT ?",
            (match, *scope, args.limit),
        ).fetchall()
    else:
        clauses = " AND ".join("(key || ' ' || body) LIKE ?" for _ in terms)
        rows = conn.execute(
            "SELECT id, ts, key, body FROM notes WHERE " + clauses + scope_sql +
            " ORDER BY id DESC LIMIT ?",
            (*[f"%{t}%" for t in terms], *scope, args.limit),
        ).fetchall()
    for row_id, ts, key, body in rows:
        print(f"#{row_id} {when(ts)} [{key}] {body}")
    return 0


def cmd_sql(args, conn, project):
    if DESTRUCTIVE.match(args.statement):
        backup = sqlite3.connect(str(db_path()) + ".bak")
        try:
            conn.backup(backup)
        finally:
            backup.close()
    try:
        cursor = conn.execute(args.statement)
        if cursor.description:
            names = [d[0] for d in cursor.description]
            for row in cursor.fetchall():
                print(json.dumps(dict(zip(names, row)), default=str))
        conn.commit()
    except sqlite3.Error as exc:
        print(f"sql error: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=None, help="override the project key")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("note", help="store a free-form note")
    p.add_argument("key")
    p.add_argument("body", nargs="+")
    p.add_argument("--tags", default=None)
    p.add_argument("--run", default=None)
    p.set_defaults(fn=cmd_note)

    p = sub.add_parser("recall", help="full-text search over notes")
    p.add_argument("words", nargs="+")
    p.add_argument("--limit", type=int, default=RECALL_LIMIT)
    p.add_argument("--all", action="store_true", help="search every project")
    p.set_defaults(fn=cmd_recall)

    p = sub.add_parser("sql", help="run one SQL statement; SELECT rows print as JSON lines")
    p.add_argument("statement")
    p.set_defaults(fn=cmd_sql)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    project = args.project or project_key(Path.cwd())
    if not project:
        print("brain: not inside a git repository; pass --project", file=sys.stderr)
        return 1
    conn = connect(timeout=1.0)
    try:
        return args.fn(args, conn, project)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
