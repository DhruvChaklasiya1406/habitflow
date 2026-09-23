"""
habit.py
========

Object-oriented core of HabitFlow.

Defines the :class:`Habit` domain model. A ``Habit`` knows nothing about
how it is stored (that is the job of :mod:`habit_tracker.db`) or how
streaks are analysed in bulk (that is the job of
:mod:`habit_tracker.analytics`). It only knows how to represent itself
and how to answer questions about its *own* completion history.

Periodicity model
------------------
* ``"daily"``  -> the period is a single calendar day.
* ``"weekly"`` -> the period is an ISO week (Monday 00:00 -> following
  Monday 00:00).

A habit is considered "completed" for a given period if it has at
least one completion timestamp that falls inside that period.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

VALID_PERIODICITIES = ("daily", "weekly")

PeriodKey = Tuple[int, int]  # (iso_year, iso_week) for weekly, (ordinal, 0) for daily


def _period_key(dt: datetime, periodicity: str) -> PeriodKey:
    """Return a hashable, orderable key identifying the period `dt` falls in."""
    if periodicity == "daily":
        return (dt.toordinal(), 0)
    if periodicity == "weekly":
        iso_year, iso_week, _ = dt.isocalendar()
        return (iso_year, iso_week)
    raise ValueError(f"Unknown periodicity: {periodicity!r}")


def _period_start(dt: datetime, periodicity: str) -> datetime:
    """Return the start timestamp of the period that contains `dt`."""
    if periodicity == "daily":
        return datetime(dt.year, dt.month, dt.day)
    if periodicity == "weekly":
        monday = dt - timedelta(days=dt.weekday())
        return datetime(monday.year, monday.month, monday.day)
    raise ValueError(f"Unknown periodicity: {periodicity!r}")


def _previous_period_key(key: PeriodKey, periodicity: str) -> PeriodKey:
    """Return the key of the period immediately before `key`."""
    if periodicity == "daily":
        return (key[0] - 1, 0)
    if periodicity == "weekly":
        year, week = key
        # Step back 7 days from the Monday of `week` and recompute the ISO key.
        jan4 = datetime(year, 1, 4)
        monday_of_week = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week - 1)
        prev_monday = monday_of_week - timedelta(days=7)
        iso_year, iso_week, _ = prev_monday.isocalendar()
        return (iso_year, iso_week)
    raise ValueError(f"Unknown periodicity: {periodicity!r}")


@dataclass
class Habit:
    """A single habit and its full completion history.

    Attributes:
        id: Stable unique identifier (UUID4 hex string, auto-generated).
        task: Human-readable description of the habit, e.g. "Read 30min".
        periodicity: Either ``"daily"`` or ``"weekly"``.
        created_date: ISO-8601 timestamp of when the habit was created.
        completions: Chronologically-unordered list of completion
            timestamps (``datetime`` objects). The list is append-only;
            entries are never rewritten, which keeps a full audit trail
            and makes streak calculations reproducible.
    """

    task: str
    periodicity: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_date: datetime = field(default_factory=datetime.now)
    completions: List[datetime] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.periodicity not in VALID_PERIODICITIES:
            raise ValueError(
                f"periodicity must be one of {VALID_PERIODICITIES}, got {self.periodicity!r}"
            )
        if not self.task or not self.task.strip():
            raise ValueError("task must be a non-empty string")

    # ------------------------------------------------------------------
    # Mutating behaviour
    # ------------------------------------------------------------------
    def check_off(self, timestamp: Optional[datetime] = None) -> bool:
        """Record a completion for the current (or given) period.

        Returns:
            True if a new completion was recorded, False if the current
            period was already marked complete (no duplicate is stored).
        """
        timestamp = timestamp or datetime.now()
        if self.is_completed_in_period(timestamp):
            return False
        self.completions.append(timestamp)
        return True

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------
    def is_completed_in_period(self, dt: datetime) -> bool:
        """Return True if any completion falls in the same period as `dt`."""
        target = _period_key(dt, self.periodicity)
        return any(_period_key(c, self.periodicity) == target for c in self.completions)

    def get_current_period_start(self, as_of: Optional[datetime] = None) -> datetime:
        """Return the start timestamp of the period containing `as_of` (default: now)."""
        as_of = as_of or datetime.now()
        return _period_start(as_of, self.periodicity)

    def get_streak(self, as_of: Optional[datetime] = None) -> int:
        """Return the *current* streak length, in periods.

        Counts consecutive completed periods walking backwards from the
        period containing `as_of` (default: now). If the current period
        has not been completed yet, the streak is 0 -- an in-progress
        but not-yet-completed period does not count.
        """
        as_of = as_of or datetime.now()
        completed_keys = {_period_key(c, self.periodicity) for c in self.completions}
        key = _period_key(as_of, self.periodicity)

        streak = 0
        while key in completed_keys:
            streak += 1
            key = _previous_period_key(key, self.periodicity)
        return streak

    def get_longest_streak(self) -> int:
        """Return the longest run of consecutive completed periods ever achieved."""
        if not self.completions:
            return 0

        completed_keys = sorted({_period_key(c, self.periodicity) for c in self.completions})

        longest = 1
        current = 1
        for previous_key, key in zip(completed_keys, completed_keys[1:]):
            if _previous_period_key(key, self.periodicity) == previous_key:
                current += 1
            else:
                current = 1
            longest = max(longest, current)
        return longest

    def completion_rate(self, periods: int, as_of: Optional[datetime] = None) -> float:
        """Fraction of the last `periods` periods (ending at `as_of`) that were completed."""
        if periods <= 0:
            raise ValueError("periods must be a positive integer")
        as_of = as_of or datetime.now()
        completed_keys = {_period_key(c, self.periodicity) for c in self.completions}

        key = _period_key(as_of, self.periodicity)
        hits = 0
        for _ in range(periods):
            if key in completed_keys:
                hits += 1
            key = _previous_period_key(key, self.periodicity)
        return hits / periods

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover - cosmetic only
        return (
            f"Habit(id={self.id[:8]}..., task={self.task!r}, "
            f"periodicity={self.periodicity!r}, completions={len(self.completions)})"
        )
