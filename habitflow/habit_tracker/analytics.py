"""
analytics.py
============

Functional-programming analytics layer for HabitFlow.

Every function in this module is **pure**: given the same inputs it
always returns the same output, it never mutates its arguments, and it
has no side effects (no I/O, no printing, no writes to the database).
This makes the whole module trivial to unit test and safe to compose.

The functions are deliberately built out of `filter`, `map`, `max` and
`sorted` rather than hand-rolled loops, to keep the functional style
explicit.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .habit import Habit
from .tracker import HabitTracker

# Number of periods considered "last month" when checking for struggling
# habits: 4 weeks regardless of periodicity, so daily and weekly habits are
# judged on a comparable recent window.
_STRUGGLE_WINDOW_PERIODS = 4
_STRUGGLE_THRESHOLD = 0.5


def get_all_habits(tracker: HabitTracker) -> List[Habit]:
    """Return every habit currently tracked, as a new list."""
    return list(tracker.list_habits())


def get_habits_by_period(tracker: HabitTracker, period: str) -> List[Habit]:
    """Return only the habits whose periodicity matches `period` ('daily'/'weekly')."""
    return list(filter(lambda h: h.periodicity == period, get_all_habits(tracker)))


def get_longest_streak_habit(habit: Habit) -> int:
    """Return the longest streak, in periods, ever achieved by a single habit."""
    return habit.get_longest_streak()


def get_longest_streak_all(tracker: HabitTracker) -> int:
    """Return the single longest streak achieved across all tracked habits.

    Returns 0 if there are no habits at all.
    """
    habits = get_all_habits(tracker)
    if not habits:
        return 0
    return max(map(get_longest_streak_habit, habits))


def struggled_habits_last_month(
    tracker: HabitTracker, as_of: Optional[datetime] = None
) -> List[Habit]:
    """Return habits whose completion rate over the last 4 periods is below 50%.

    "Struggled" is defined as: over the most recent `_STRUGGLE_WINDOW_PERIODS`
    periods (of that habit's own periodicity) ending at `as_of` (default:
    now), fewer than `_STRUGGLE_THRESHOLD` of them were completed.
    """
    habits = get_all_habits(tracker)

    def _is_struggling(habit: Habit) -> bool:
        return habit.completion_rate(_STRUGGLE_WINDOW_PERIODS, as_of=as_of) < _STRUGGLE_THRESHOLD

    return list(filter(_is_struggling, habits))


def habits_sorted_by_current_streak(
    tracker: HabitTracker, as_of: Optional[datetime] = None, descending: bool = True
) -> List[Habit]:
    """Return all habits sorted by their current streak length.

    A fifth, convenience analytics function used by the CLI's report view.
    """
    habits = get_all_habits(tracker)
    return sorted(habits, key=lambda h: h.get_streak(as_of=as_of), reverse=descending)
