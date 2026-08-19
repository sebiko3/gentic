"""Fixture for exercising the code-reviewer agent. Not imported by anything.

Contains two planted defects that a competent reviewer must report, and one decoy that it must
not. See seeded_defect.expected.md for the pass condition.
"""

import sqlite3


def load_user(conn, user_id):
    """PLANTED DEFECT 1 — SQL built by string interpolation.

    Violates the standing project rule "use parameterized queries". A user_id of
    ``1 OR 1=1`` returns every row; ``1; DROP TABLE users`` is reachable via executescript
    paths. Security, high confidence.
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT name, email FROM users WHERE id = {user_id}")
    return cursor.fetchone()


def record_login(conn, user_id):
    """PLANTED DEFECT 2 — swallowed exception.

    Any failure here is discarded: a disk-full error, a locked database, a schema mismatch.
    The caller is told the login was recorded when nothing was written. Silent failure, high
    confidence.
    """
    try:
        conn.execute("INSERT INTO logins (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception:
        pass


def get_usr_nm(conn, user_id):
    """DECOY — an abbreviated function name.

    Cosmetic only. No project rule forbids it, behaviour is correct, and reporting it would be
    a sub-threshold nitpick. A reviewer that flags this has a miscalibrated confidence gate.
    """
    row = load_user(conn, user_id)
    return row[0] if row else None


def open_database(path):
    return sqlite3.connect(path)
