"""Unit tests for the Habit domain class: creation, completion, streaks."""

from datetime import datetime, timedelta

import pytest

from habit_tracker.habit import Habit


def test_create_habit_defaults():
    habit = Habit(task="Meditate", periodicity="daily")
    assert habit.task == "Meditate"
    assert habit.periodicity == "daily"
    assert habit.completions == []
    assert habit.id  # auto-generated, non-empty


def test_create_habit_rejects_bad_periodicity():
    with pytest.raises(ValueError):
        Habit(task="Meditate", periodicity="monthly")


def test_create_habit_rejects_empty_task():
    with pytest.raises(ValueError):
        Habit(task="   ", periodicity="daily")


def test_check_off_records_completion():
    habit = Habit(task="Read", periodicity="daily")
    now = datetime(2026, 1, 10, 8, 0)
    assert habit.check_off(now) is True
    assert len(habit.completions) == 1


def test_check_off_is_idempotent_within_same_period():
    habit = Habit(task="Read", periodicity="daily")
    now = datetime(2026, 1, 10, 8, 0)
    later_same_day = datetime(2026, 1, 10, 20, 0)
    assert habit.check_off(now) is True
    assert habit.check_off(later_same_day) is False
    assert len(habit.completions) == 1


def test_is_completed_in_period_daily():
    habit = Habit(task="Read", periodicity="daily")
    habit.check_off(datetime(2026, 1, 10, 8, 0))
    assert habit.is_completed_in_period(datetime(2026, 1, 10, 23, 0)) is True
    assert habit.is_completed_in_period(datetime(2026, 1, 11, 0, 1)) is False


def test_is_completed_in_period_weekly_crosses_days_within_same_week():
    habit = Habit(task="Dentist", periodicity="weekly")
    # Monday 2026-01-05
    habit.check_off(datetime(2026, 1, 5, 8, 0))
    # Sunday of the same ISO week
    assert habit.is_completed_in_period(datetime(2026, 1, 11, 23, 0)) is True
    # Next Monday -> different week
    assert habit.is_completed_in_period(datetime(2026, 1, 12, 0, 1)) is False


def test_get_streak_zero_when_current_period_incomplete():
    habit = Habit(task="Workout", periodicity="daily")
    as_of = datetime(2026, 1, 10)
    habit.check_off(as_of - timedelta(days=1))
    habit.check_off(as_of - timedelta(days=2))
    assert habit.get_streak(as_of=as_of) == 0


def test_get_streak_counts_consecutive_days():
    habit = Habit(task="Workout", periodicity="daily")
    as_of = datetime(2026, 1, 10)
    for offset in range(4):  # today, yesterday, ... 3 days ago
        habit.check_off(as_of - timedelta(days=offset))
    habit.check_off(as_of - timedelta(days=10))  # isolated, older completion
    assert habit.get_streak(as_of=as_of) == 4


def test_get_streak_weekly():
    habit = Habit(task="Team meeting", periodicity="weekly")
    as_of = datetime(2026, 1, 20)  # Tuesday
    for weeks_back in range(3):
        habit.check_off(as_of - timedelta(weeks=weeks_back))
    assert habit.get_streak(as_of=as_of) == 3


def test_get_longest_streak_finds_best_run_even_if_not_current():
    habit = Habit(task="Read", periodicity="daily")
    base = datetime(2026, 1, 1)
    # A 5-day run early on...
    for offset in range(5):
        habit.check_off(base + timedelta(days=offset))
    # ...then a gap, then only a 2-day run more recently.
    habit.check_off(base + timedelta(days=20))
    habit.check_off(base + timedelta(days=21))
    assert habit.get_longest_streak() == 5
    assert habit.get_streak(as_of=base + timedelta(days=21)) == 2


def test_get_longest_streak_with_no_completions_is_zero():
    habit = Habit(task="Read", periodicity="daily")
    assert habit.get_longest_streak() == 0


def test_completion_rate():
    habit = Habit(task="Workout", periodicity="daily")
    as_of = datetime(2026, 1, 10)
    for offset in [0, 1, 3]:  # 3 out of the last 4 days
        habit.check_off(as_of - timedelta(days=offset))
    assert habit.completion_rate(4, as_of=as_of) == pytest.approx(0.75)
