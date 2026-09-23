"""
db.py
=====

Procedural persistence layer for HabitFlow.

Every function here takes an open ``sqlite3.Connection`` as its first
argument and performs one job. Nothing in this module knows about the
CLI or about analytics -- it is a thin, testable wrapper around SQLite
that turns :class:`~habit_tracker.habit.Habit` objects into rows and
back again.

Using ``:memory:`` as the database path gives a fully isolated,
disk-free database, which is what the unit tests use.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List

from .habit import Habit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    periodicity TEXT NOT NULL CHECK(periodicity IN ('daily', 'weekly')),
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS completions (
    habit_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (habit_id, timestamp),
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
);
"""


def get_connection(db_path: str = "habitflow.db") -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and return it."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the `habits` and `completions` tables if they do not exist yet."""
    conn.executescript(_SCHEMA)
    conn.commit()


def save_habit(conn: sqlite3.Connection, habit: Habit) -> None:
    """Insert or fully replace a habit row and rewrite its completion rows."""
    conn.execute(
        "INSERT OR REPLACE INTO habits (id, task, periodicity, created_date) "
        "VALUES (?, ?, ?, ?)",
        (habit.id, habit.task, habit.periodicity, habit.created_date.isoformat()),
    )
    conn.execute("DELETE FROM completions WHERE habit_id = ?", (habit.id,))
    conn.executemany(
        "INSERT OR IGNORE INTO completions (habit_id, timestamp) VALUES (?, ?)",
        [(habit.id, ts.isoformat()) for ts in habit.completions],
    )
    conn.commit()


def add_completion(conn: sqlite3.Connection, habit_id: str, timestamp: datetime) -> None:
    """Append a single completion row without rewriting the whole habit."""
    conn.execute(
        "INSERT OR IGNORE INTO completions (habit_id, timestamp) VALUES (?, ?)",
        (habit_id, timestamp.isoformat()),
    )
    conn.commit()


def load_habits(conn: sqlite3.Connection) -> List[Habit]:
    """Load every habit, together with its completion history, from the database."""
    habit_rows = conn.execute(
        "SELECT id, task, periodicity, created_date FROM habits"
    ).fetchall()

    habits: List[Habit] = []
    for habit_id, task, periodicity, created_date in habit_rows:
        completion_rows = conn.execute(
            "SELECT timestamp FROM completions WHERE habit_id = ? ORDER BY timestamp",
            (habit_id,),
        ).fetchall()
        completions = [datetime.fromisoformat(row[0]) for row in completion_rows]
        habits.append(
            Habit(
                id=habit_id,
                task=task,
                periodicity=periodicity,
                created_date=datetime.fromisoformat(created_date),
                completions=completions,
            )
        )
    return habits


def delete_habit(conn: sqlite3.Connection, habit_id: str) -> None:
    """Delete a habit and (via ON DELETE CASCADE) all of its completions."""
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
