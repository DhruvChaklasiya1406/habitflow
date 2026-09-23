"""
tracker.py
==========

:class:`HabitTracker` ties the OOP domain model (:mod:`habit_tracker.habit`)
to the persistence layer (:mod:`habit_tracker.db`). It is the single
object the CLI and the analytics module talk to; neither of them needs
to know that SQLite exists.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from . import db
from .habit import Habit


class HabitTracker:
    """In-memory habit registry backed by a SQLite database.

    Attributes:
        habits: Mapping of habit id -> :class:`Habit`, kept in sync with
            the database on every mutating call.
        conn: The underlying SQLite connection.
    """

    def __init__(self, db_path: str = "habitflow.db"):
        self.db_path = db_path
        self.conn: sqlite3.Connection = db.get_connection(db_path)
        db.init_db(self.conn)
        self.habits: Dict[str, Habit] = {h.id: h for h in db.load_habits(self.conn)}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_habit(self, task: str, periodicity: str) -> Habit:
        """Create, persist and register a new habit."""
        habit = Habit(task=task, periodicity=periodicity)
        self.habits[habit.id] = habit
        db.save_habit(self.conn, habit)
        return habit

    def edit_habit(
        self,
        habit_id: str,
        task: Optional[str] = None,
        periodicity: Optional[str] = None,
    ) -> Habit:
        """Rename a habit and/or change its periodicity without losing history."""
        habit = self.get_habit(habit_id)
        if task is not None:
            habit.task = task
        if periodicity is not None:
            if periodicity not in ("daily", "weekly"):
                raise ValueError("periodicity must be 'daily' or 'weekly'")
            habit.periodicity = periodicity
        db.save_habit(self.conn, habit)
        return habit

    def delete_habit(self, habit_id: str) -> None:
        """Remove a habit (and its completions) permanently."""
        self.get_habit(habit_id)  # raises KeyError with a clear message if missing
        del self.habits[habit_id]
        db.delete_habit(self.conn, habit_id)

    def get_habit(self, habit_id: str) -> Habit:
        """Look up a habit by id, raising a clear error if it does not exist."""
        try:
            return self.habits[habit_id]
        except KeyError as exc:
            raise KeyError(f"No habit with id {habit_id!r}") from exc

    def list_habits(self) -> List[Habit]:
        """Return all tracked habits."""
        return list(self.habits.values())

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------
    def check_off(self, habit_id: str, timestamp: Optional[datetime] = None) -> bool:
        """Mark a habit as done for the current period.

        Returns:
            True if a new completion was recorded, False if that period
            was already complete.
        """
        habit = self.get_habit(habit_id)
        timestamp = timestamp or datetime.now()
        recorded = habit.check_off(timestamp)
        if recorded:
            db.add_completion(self.conn, habit_id, timestamp)
        return recorded

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def save_all(self) -> None:
        """Persist every in-memory habit back to the database."""
        for habit in self.habits.values():
            db.save_habit(self.conn, habit)

    def close(self) -> None:
        """Flush and close the underlying database connection."""
        self.save_all()
        self.conn.close()

    def __enter__(self) -> "HabitTracker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
