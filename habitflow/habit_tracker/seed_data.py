"""
seed_data.py
============

Builds the 5 predefined habits with 4 weeks (28 days) of deterministic
completion history, matching the specification from the Phase 1
portfolio submission:

    Habit ID  Task           Periodicity  Completions  Current Streak
    H1        Brush teeth    daily        25/28        4 days
    H2        Workout        daily        18/28        0 days
    H3        Read 30min     daily        22/28        14 days
    H4        Dentist visit  weekly       3/4          3 weeks
    H5        Team meeting   weekly       4/4          4 weeks

This data exists purely so unit tests have a realistic, reproducible
fixture to verify streak and completion-rate calculations against. The
generator is deterministic relative to a supplied `as_of` timestamp
(default: now), so tests can pin `as_of` and get identical results
every run.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from .habit import Habit
from .tracker import HabitTracker


def _daily_completions(
    as_of: datetime, total_days: int, completed_today_streak: int, extra_completions_needed: int
) -> list:
    """Build a list of daily completion timestamps.

    The most recent `completed_today_streak` days (today included) are
    completed. Day `completed_today_streak` (the day right after that
    streak) is deliberately left incomplete so the streak does not run
    longer. The remaining `extra_completions_needed` completions are
    then filled in, oldest days first, from the days that follow.
    """
    completions = []
    today = datetime(as_of.year, as_of.month, as_of.day, 9, 0, 0)

    # Recent, unbroken streak.
    for offset in range(completed_today_streak):
        completions.append(today - timedelta(days=offset))

    # The day immediately after the streak is left empty on purpose
    # (offset == completed_today_streak), so we start filling extra
    # completions from the day after *that*.
    fill_start = completed_today_streak + 1
    remaining_days = total_days - fill_start
    if extra_completions_needed > remaining_days:
        raise ValueError("Not enough remaining days to place the required completions")

    for i in range(extra_completions_needed):
        offset = fill_start + i
        completions.append(today - timedelta(days=offset))

    return completions


def _weekly_completions(as_of: datetime, completed_recent_weeks: int, gap_before_next: bool):
    """Build weekly completion timestamps: the most recent `completed_recent_weeks`
    weeks (this week included) are completed; the week(s) before that are not,
    if `gap_before_next` is True.
    """
    monday_this_week = as_of - timedelta(days=as_of.weekday())
    completions = []
    for w in range(completed_recent_weeks):
        completions.append(monday_this_week - timedelta(weeks=w, days=-1))  # Tuesday of that week
    return completions


def build_seed_habits(as_of: Optional[datetime] = None) -> Dict[str, Habit]:
    """Return the 5 predefined habits (keyed by short id H1..H5) with seeded history."""
    as_of = as_of or datetime.now()

    habits: Dict[str, Habit] = {}

    # H1: Brush teeth - daily - 25/28 - current streak 4 days
    h1 = Habit(task="Brush teeth", periodicity="daily")
    h1.completions = _daily_completions(
        as_of, total_days=28, completed_today_streak=4, extra_completions_needed=21
    )
    habits["H1"] = h1

    # H2: Workout - daily - 18/28 - current streak 0 days (today not done)
    h2 = Habit(task="Workout", periodicity="daily")
    today_start = datetime(as_of.year, as_of.month, as_of.day, 9, 0, 0)
    h2.completions = [
        today_start - timedelta(days=offset) for offset in range(1, 19)
    ]  # days 1..18 done, day 0 (today) NOT done -> streak 0
    habits["H2"] = h2

    # H3: Read 30min - daily - 22/28 - current streak 14 days
    h3 = Habit(task="Read 30min", periodicity="daily")
    h3.completions = _daily_completions(
        as_of, total_days=28, completed_today_streak=14, extra_completions_needed=8
    )
    habits["H3"] = h3

    # H4: Dentist visit - weekly - 3/4 - current streak 3 weeks
    # (most recent 3 weeks completed, the oldest of the 4 weeks missed)
    h4 = Habit(task="Dentist visit", periodicity="weekly")
    h4.completions = _weekly_completions(as_of, completed_recent_weeks=3, gap_before_next=True)
    habits["H4"] = h4

    # H5: Team meeting - weekly - 4/4 - current streak 4 weeks
    h5 = Habit(task="Team meeting", periodicity="weekly")
    h5.completions = _weekly_completions(as_of, completed_recent_weeks=4, gap_before_next=False)
    habits["H5"] = h5

    return habits


def seed_tracker(tracker: HabitTracker, as_of: Optional[datetime] = None) -> None:
    """Populate an existing HabitTracker with the 5 predefined habits, then persist them."""
    for habit in build_seed_habits(as_of).values():
        tracker.habits[habit.id] = habit
    tracker.save_all()


if __name__ == "__main__":  # pragma: no cover
    tracker = HabitTracker(":memory:")
    seed_tracker(tracker)
    for short_id, habit in zip(("H1", "H2", "H3", "H4", "H5"), tracker.list_habits()):
        print(
            f"{short_id}: {habit.task:15s} {habit.periodicity:7s} "
            f"completions={len(habit.completions):2d}  current_streak={habit.get_streak()}"
        )
