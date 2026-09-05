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
SESSION_TIMEOUT = 0.144  # seconds; the valve is contended by up to five parallel spawns
RECALL_LIMIT = 8       # notes printed by default
DETAIL_CHARS = 300     # matches post_tool_use.py's command trim
PREFERENCE_MIN = 2     # agreeing user decisions before a preference is learned
EVENT_DAYS = 89        # retention for hook events
SESSION_DAYS = 8       # retention for idle session rows

EVENT_KINDS = ("red", "verification")

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
    "CREATE TABLE IF NOT EXISTS eval_runs ("
    " id INTEGER PRIMARY KEY, ts REAL, project TEXT, suite TEXT, case_name TEXT, arm TEXT,"
    " run_index INTEGER, model TEXT, cost_usd REAL, turns INTEGER, is_error INTEGER, skipped INTEGER,"
    " exhausted INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS eval_graders ("
    " id INTEGER PRIMARY KEY, run_id INTEGER, name TEXT, type TEXT, passed INTEGER, detail TEXT)",
)

# Schema versions are additive and every statement is guarded, so opening a brain of any earlier
# shape upgrades it in place. Version 1 is the pre-versioning shape (eval_runs.exhausted);
# version 2 adds the sessions table, events.run and the query indexes. Existing rows are never
# rewritten: events from before version 2 keep run = NULL.
SCHEMA_VERSION = 2

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_events_project_ts ON events(project, ts)",
    "CREATE INDEX IF NOT EXISTS idx_events_run ON events(run)",
    "CREATE INDEX IF NOT EXISTS idx_notes_project_ts ON notes(project, ts)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_project_ts ON lessons(project, ts)",
    "CREATE INDEX IF NOT EXISTS idx_runs_project_finished ON runs(project, finished)",
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


def add_column(conn, table, column, declaration):
    """ALTER TABLE … ADD COLUMN, skipped when the column already exists."""
    if column not in [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def migrate_1(conn):
    add_column(conn, "eval_runs", "exhausted", "INTEGER DEFAULT 0")


def migrate_2(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        " id TEXT PRIMARY KEY, agents_in_flight INTEGER NOT NULL DEFAULT 0, updated REAL)"
    )
    add_column(conn, "events", "run", "TEXT")
    for statement in INDEXES:
        conn.execute(statement)


MIGRATIONS = (migrate_1, migrate_2)


def ensure_schema(conn):
    for statement in SCHEMA:
        conn.execute(statement)
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, migrate in enumerate(MIGRATIONS, start=1):
        if version > current:
            migrate(conn)
    if current < SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
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
    try:
        project = project_key(cwd)
        if not project:
            return False
        conn = connect()
        try:
            conn.execute(
                "INSERT INTO events (ts, project, session, kind, detail, data, run) VALUES (?,?,?,?,?,?,?)",
                (time.time(), project, session, kind, scrub(str(detail))[:DETAIL_CHARS],
                 json.dumps(data) if data is not None else None, open_run(conn, project)),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        # A brain that cannot be opened, created or locked in time is invisible to the session.
        return False


# --- session state (the concurrency valve's counter) -----------------------------------------
#
# Best-effort like record_event: nothing here raises, prints, or waits past its busy timeout.
# A brain that cannot be opened fails OPEN — session_acquire says yes — because an uncapped
# fan-out is preferred to a blocked session. Sessions are keyed by session id alone; they need
# no project, and any hook may create the file, exactly as the JSON state file was created.

def _session_write(fn):
    try:
        conn = connect(timeout=SESSION_TIMEOUT)
        try:
            result = fn(conn)
            conn.commit()
            return result
        finally:
            conn.close()
    except Exception:
        return None


def session_reset(session_id):
    """Zero the session's in-flight counter (a new user prompt). True when written."""
    def write(conn):
        conn.execute(
            "INSERT INTO sessions (id, agents_in_flight, updated) VALUES (?, 0, ?)"
            " ON CONFLICT(id) DO UPDATE SET agents_in_flight = 0, updated = excluded.updated",
            (session_id, time.time()),
        )
        return True
    return _session_write(write) or False


def session_acquire(session_id, cap):
    """Take one in-flight slot if fewer than `cap` are taken. True when taken — or when no
    brain could count (fail open)."""
    def write(conn):
        conn.execute("INSERT OR IGNORE INTO sessions (id, agents_in_flight, updated) VALUES (?, 0, ?)",
                     (session_id, time.time()))
        taken = conn.execute(
            "UPDATE sessions SET agents_in_flight = agents_in_flight + 1, updated = ?"
            " WHERE id = ? AND agents_in_flight < ?",
            (time.time(), session_id, cap),
        ).rowcount
        return taken == 1
    result = _session_write(write)
    return True if result is None else result


def session_release(session_id):
    """Free one in-flight slot (floor 0). True when written."""
    def write(conn):
        conn.execute(
            "UPDATE sessions SET agents_in_flight = MAX(agents_in_flight - 1, 0), updated = ? WHERE id = ?",
            (time.time(), session_id),
        )
        return True
    return _session_write(write) or False


# --- retention -------------------------------------------------------------------------
#
# Events and sessions are the only tables that grow on their own. Retention is global: the
# brain is machine-wide, and an old event is old whichever project wrote it.

def prune(conn, events_days=EVENT_DAYS, sessions_days=SESSION_DAYS):
    """Delete events and idle sessions past their retention. Returns (events, sessions) removed."""
    now = time.time()
    events = conn.execute("DELETE FROM events WHERE ts < ?", (now - events_days * 86400,)).rowcount
    sessions = conn.execute("DELETE FROM sessions WHERE updated < ?", (now - sessions_days * 86400,)).rowcount
    conn.commit()
    return events, sessions


def prune_quietly():
    """The session-start prune: default retention, no output, no file creation, never raises."""
    try:
        if not db_path().exists():
            return
        conn = sqlite3.connect(str(db_path()), timeout=BUSY_TIMEOUT)
        try:
            ensure_schema(conn)
            prune(conn)
        finally:
            conn.close()
    except Exception:
        pass


def open_run(conn, project):
    """Slug of the project's most recently started, unfinished run, or None."""
    row = conn.execute(
        "SELECT slug FROM runs WHERE project = ? AND finished IS NULL ORDER BY started DESC LIMIT 1",
        (project,),
    ).fetchone()
    return row[0] if row else None


def summary(project):
    """(lessons for `project`, learned preferences) for the session-start notice, or None.

    Read-only and best-effort: a missing brain is None rather than a freshly created file, so
    merely starting a session never writes to the user's home.
    """
    try:
        if not db_path().exists():
            return None
        conn = sqlite3.connect(str(db_path()), timeout=BUSY_TIMEOUT)
        try:
            lessons = conn.execute("SELECT COUNT(*) FROM lessons WHERE project = ?", (project,)).fetchone()[0]
            topics = [t for (t,) in conn.execute("SELECT DISTINCT topic FROM decisions")]
            preferences = sum(1 for t in topics if learned_preference(conn, t) is not None)
        finally:
            conn.close()
        return lessons, preferences
    except Exception:
        return None


# --- eval scores (written by evals/run.py, read by `evals`) ------------------------------

def record_eval_run(cwd, suite, case_name, arm, run_index, model, cost_usd, turns, is_error, skipped, exhausted=0):
    """One row per headless eval session. Best-effort: returns the row id, or None."""
    try:
        project = project_key(cwd)
        if not project:
            return None
        conn = connect(timeout=1.0)
        try:
            cursor = conn.execute(
                "INSERT INTO eval_runs (ts, project, suite, case_name, arm, run_index, model, cost_usd,"
                " turns, is_error, skipped, exhausted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), project, suite, case_name, arm, int(run_index), model, float(cost_usd or 0),
                 int(turns or 0), int(bool(is_error)), int(bool(skipped)), int(bool(exhausted))),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    except Exception:
        return None


def record_eval_grader(run_id, name, type_, passed, detail):
    """One row per grader verdict. Best-effort: True when written, None otherwise."""
    try:
        conn = connect(timeout=1.0)
        try:
            conn.execute(
                "INSERT INTO eval_graders (run_id, name, type, passed, detail) VALUES (?,?,?,?,?)",
                (int(run_id), name, type_, int(bool(passed)), detail),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        return None


def eval_summary(conn, project, suite=None, every_project=False):
    """Per-case rows for one suite: {case: {arm: {"passed", "total", "rate", "cost", "skipped"}}}.

    Rate is the mean over runs of passed/total graders (a skipped or graderless run scores 0);
    cost is summed from eval_runs only, never from grader rows.
    """
    scope_sql, scope = ("", ()) if every_project else (" AND project = ?", (project,))
    if suite is None:
        row = conn.execute("SELECT suite FROM eval_runs WHERE 1=1" + scope_sql + " ORDER BY id DESC LIMIT 1", scope).fetchone()
        if not row:
            return None, {}
        suite = row[0]
    runs = conn.execute(
        "SELECT id, case_name, arm, cost_usd, skipped, exhausted FROM eval_runs WHERE suite = ?" + scope_sql + " ORDER BY id",
        (suite, *scope),
    ).fetchall()
    cases = {}
    for run_id, case_name, arm, cost, skipped, exhausted in runs:
        graders = conn.execute("SELECT passed FROM eval_graders WHERE run_id = ?", (run_id,)).fetchall()
        passed = sum(1 for (p,) in graders if p)
        total = len(graders)
        bucket = cases.setdefault(case_name, {}).setdefault(arm, {"passed": 0, "total": 0, "scores": [], "cost": 0.0,
                                                                  "skipped": 0, "exhausted": 0})
        bucket["cost"] += cost or 0
        bucket["exhausted"] += int(exhausted or 0)
        if skipped:
            bucket["skipped"] += 1
            continue
        bucket["passed"] += passed
        bucket["total"] += total
        bucket["scores"].append(passed / total if total else 0.0)
    for arms in cases.values():
        for bucket in arms.values():
            bucket["rate"] = sum(bucket["scores"]) / len(bucket["scores"]) if bucket["scores"] else 0.0
    return suite, cases


def cmd_evals(args, conn, project):
    suite, cases = eval_summary(conn, project, args.suite, args.all)
    if suite is None:
        print("no eval suites recorded")
        return 1
    print(f"suite {suite}")
    suite_rates = {}
    for case_name, arms in cases.items():
        parts = [f"{case_name:28}"]
        cost = 0.0
        for arm in ("with", "without"):
            bucket = arms.get(arm)
            if not bucket:
                continue
            cost += bucket["cost"]
            if bucket["skipped"] and not bucket["scores"]:
                parts.append(f"{arm} skipped: suite budget")
                continue
            flag = " exhausted" if bucket["exhausted"] else ""
            parts.append(f"{arm} {bucket['passed']}/{bucket['total']} ({bucket['rate']:.2f}){flag}")
            suite_rates.setdefault(arm, []).append(bucket["rate"])
        if "with" in arms and "without" in arms:
            parts.append(f"delta {arms['with']['rate'] - arms['without']['rate']:+.2f}")
        parts.append(f"${cost:.2f}")
        print("  ".join(parts))
    if suite_rates:
        means = {arm: sum(r) / len(r) for arm, r in suite_rates.items()}
        line = "  ".join(f"{arm} {rate:.2f}" for arm, rate in means.items())
        if len(means) == 2:
            line += f"  delta {means['with'] - means['without']:+.2f}"
        print(f"{'suite':28}{line}")
    return 0


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


def cmd_decide(args, conn, project):
    conn.execute(
        "INSERT INTO decisions (ts, project, run, topic, chosen, source) VALUES (?,?,?,?,?,?)",
        (time.time(), project, args.run, args.topic, " ".join(args.chosen), args.source),
    )
    conn.commit()
    return 0


def learned_preference(conn, topic):
    """The user's settled answer for `topic`, or None.

    Preferences describe the user, not a repository, so they are learned across projects. The
    most recent user-sourced decision wins, and only once that value has been chosen at least
    PREFERENCE_MIN times: one answer is an accident, two is a preference, and a changed mind
    resets the count. Defaults and learned rows never teach — the agent must not confirm its
    own guesses.
    """
    rows = conn.execute(
        "SELECT chosen FROM decisions WHERE topic = ? AND source = 'user' ORDER BY id DESC",
        (topic,),
    ).fetchall()
    if not rows:
        return None
    latest = rows[0][0]
    if sum(1 for (chosen,) in rows if chosen == latest) >= PREFERENCE_MIN:
        return latest
    return None


def cmd_preference(args, conn, project):
    value = learned_preference(conn, args.topic)
    if value is None:
        return 1
    print(value)
    return 0


def cmd_lesson(args, conn, project):
    conn.execute(
        "INSERT INTO lessons (ts, project, run, item, rung, points, caught_by, cause, note)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (time.time(), project, args.run, args.item, args.rung, args.points, args.caught_by,
         args.cause, args.note),
    )
    conn.commit()
    return 0


def scope_clause(args, project):
    if getattr(args, "all", False):
        return "", ()
    return " WHERE project = ?", (project,)


def cmd_lessons(args, conn, project):
    clause, params = scope_clause(args, project)
    rows = conn.execute(
        "SELECT id, ts, project, run, item, rung, points, caught_by, cause, note FROM lessons"
        + clause + " ORDER BY id DESC LIMIT ?", (*params, args.limit),
    ).fetchall()
    for row_id, ts, proj, run, item, rung, points, caught_by, cause, note in rows:
        where = f"{proj}/{run}" if run else proj
        line = f"#{row_id} {when(ts)} [{where}] {item} — rung {rung}, {points} pt, caught by {caught_by}: {cause}"
        if note:
            line += f" ({note})"
        print(line)
    return 0


def cmd_stats(args, conn, project):
    clause, params = scope_clause(args, project)
    print(f"project: {'all' if args.all else project}")
    total = conn.execute("SELECT COUNT(*), COALESCE(SUM(points), 0) FROM lessons" + clause, params).fetchone()
    print(f"lessons: {total[0]}")
    for caught_by, count in conn.execute(
        "SELECT caught_by, COUNT(*) FROM lessons" + clause + " GROUP BY caught_by ORDER BY 2 DESC, 1",
        params,
    ):
        print(f"  {caught_by}: {count}")
    print(f"points: {total[1]}")
    print(f"notes: {conn.execute('SELECT COUNT(*) FROM notes' + clause, params).fetchone()[0]}")
    topics = [t for (t,) in conn.execute("SELECT DISTINCT topic FROM decisions")]
    print(f"preferences: {sum(1 for t in topics if learned_preference(conn, t) is not None)}")
    print(f"events: {conn.execute('SELECT COUNT(*) FROM events' + clause, params).fetchone()[0]}")
    return 0


def cmd_prune(args, conn, project):
    events, sessions = prune(conn, args.events_days, args.sessions_days)
    print(f"pruned {events} event(s), {sessions} session(s)")
    return 0


def cmd_run(args, conn, project):
    now = time.time()
    if args.action == "start":
        conn.execute(
            "INSERT INTO runs (project, slug, goal, started) VALUES (?,?,?,?)"
            " ON CONFLICT(project, slug) DO UPDATE SET goal = excluded.goal, started = excluded.started",
            (project, args.slug, args.goal, now),
        )
    else:
        updated = conn.execute(
            "UPDATE runs SET finished = ?, outcome = ? WHERE project = ? AND slug = ?",
            (now, args.outcome, project, args.slug),
        ).rowcount
        if not updated:
            conn.execute(
                "INSERT INTO runs (project, slug, goal, started, finished, outcome) VALUES (?,?,?,?,?,?)",
                (project, args.slug, None, None, now, args.outcome),
            )
    conn.commit()
    return 0


def cmd_stamp(args, conn, project):
    now = time.time()
    for raw in args.paths:
        path = Path(raw)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            print(f"brain: cannot stamp {raw}: {exc}", file=sys.stderr)
            continue
        conn.execute(
            "INSERT INTO stamps (project, slug, path, sha, ts) VALUES (?,?,?,?,?)"
            " ON CONFLICT(project, slug, path) DO UPDATE SET sha = excluded.sha, ts = excluded.ts",
            (project, args.slug, str(path.resolve()), digest, now),
        )
    conn.commit()
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=None, help="override the project key")
    # Accepted after the subcommand too (`brain lesson ... --project x`); SUPPRESS keeps the
    # subparser from overwriting a value given before it.
    scoped = argparse.ArgumentParser(add_help=False)
    scoped.add_argument("--project", default=argparse.SUPPRESS, help="override the project key")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("note", parents=[scoped], help="store a free-form note")
    p.add_argument("key")
    p.add_argument("body", nargs="+")
    p.add_argument("--tags", default=None)
    p.add_argument("--run", default=None)
    p.set_defaults(fn=cmd_note)

    p = sub.add_parser("recall", parents=[scoped], help="full-text search over notes")
    p.add_argument("words", nargs="+")
    p.add_argument("--limit", type=int, default=RECALL_LIMIT)
    p.add_argument("--all", action="store_true", help="search every project")
    p.set_defaults(fn=cmd_recall)

    p = sub.add_parser("sql", parents=[scoped], help="run one SQL statement; SELECT rows print as JSON lines")
    p.add_argument("statement")
    p.set_defaults(fn=cmd_sql)

    p = sub.add_parser("decide", parents=[scoped], help="record a decision and where it came from")
    p.add_argument("topic")
    p.add_argument("chosen", nargs="+")
    p.add_argument("--source", choices=("user", "default", "learned"), required=True)
    p.add_argument("--run", default=None)
    p.set_defaults(fn=cmd_decide)

    p = sub.add_parser("preference", parents=[scoped], help="print the user's learned answer for a topic (exit 1 if none)")
    p.add_argument("topic")
    p.set_defaults(fn=cmd_preference)

    p = sub.add_parser("lesson", parents=[scoped], help="record what a failed Definition-of-Done item taught")
    p.add_argument("--item", required=True)
    p.add_argument("--rung", type=int, required=True)
    p.add_argument("--points", type=int, required=True)
    p.add_argument("--caught-by", required=True, dest="caught_by",
                   help="suite | live | review | critic | auditor | user")
    p.add_argument("--cause", required=True)
    p.add_argument("--note", default=None)
    p.add_argument("--run", default=None)
    p.set_defaults(fn=cmd_lesson)

    p = sub.add_parser("lessons", parents=[scoped], help="list lessons, newest first")
    p.add_argument("--all", action="store_true", help="every project")
    p.add_argument("--limit", type=int, default=21)
    p.set_defaults(fn=cmd_lessons)

    p = sub.add_parser("stats", parents=[scoped], help="counts for the current project")
    p.add_argument("--all", action="store_true", help="every project")
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("run", parents=[scoped], help="record a run's lifecycle")
    action = p.add_subparsers(dest="action", required=True)
    start = action.add_parser("start")
    start.add_argument("slug")
    start.add_argument("--goal", required=True)
    finish = action.add_parser("finish")
    finish.add_argument("slug")
    finish.add_argument("--outcome", choices=("done", "stopped"), required=True)
    p.set_defaults(fn=cmd_run)

    # Global by design: no `scoped` parent, no --project — retention crosses every project.
    p = sub.add_parser("prune", help="delete events and idle sessions past their retention (every project)")
    p.add_argument("--events-days", type=int, default=EVENT_DAYS, dest="events_days")
    p.add_argument("--sessions-days", type=int, default=SESSION_DAYS, dest="sessions_days")
    p.set_defaults(fn=cmd_prune)

    p = sub.add_parser("evals", parents=[scoped], help="scores of the latest (or named) eval suite")
    p.add_argument("--suite", default=None)
    p.add_argument("--all", action="store_true", help="every project")
    p.set_defaults(fn=cmd_evals)

    p = sub.add_parser("stamp", parents=[scoped], help="record sha256 of the skill/agent files a run used")
    p.add_argument("slug")
    p.add_argument("paths", nargs="+")
    p.set_defaults(fn=cmd_stamp)

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
