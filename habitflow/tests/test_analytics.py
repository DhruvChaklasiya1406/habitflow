"""Unit tests for every function in habit_tracker.analytics, using the
seeded 4-week test data as a realistic fixture (100% function coverage)."""

from datetime import datetime

import pytest

from habit_tracker import analytics
from habit_tracker.seed_data import build_seed_habits
from habit_tracker.tracker import HabitTracker


@pytest.fixture
def as_of():
    return datetime(2026, 6, 15, 12, 0)


@pytest.fixture
def seeded_tracker(as_of):
    tracker = HabitTracker(":memory:")
    for habit in build_seed_habits(as_of).values():
        tracker.habits[habit.id] = habit
    return tracker


def test_get_all_habits_returns_every_habit(seeded_tracker):
    habits = analytics.get_all_habits(seeded_tracker)
    assert len(habits) == 5
    assert {h.task for h in habits} == {
        "Brush teeth",
        "Workout",
        "Read 30min",
        "Dentist visit",
        "Team meeting",
    }


def test_get_all_habits_empty_tracker_returns_empty_list():
    empty_tracker = HabitTracker(":memory:")
    assert analytics.get_all_habits(empty_tracker) == []


def test_get_habits_by_period_daily(seeded_tracker):
    daily = analytics.get_habits_by_period(seeded_tracker, "daily")
    assert {h.task for h in daily} == {"Brush teeth", "Workout", "Read 30min"}


def test_get_habits_by_period_weekly(seeded_tracker):
    weekly = analytics.get_habits_by_period(seeded_tracker, "weekly")
    assert {h.task for h in weekly} == {"Dentist visit", "Team meeting"}


def test_get_longest_streak_habit_matches_seed_data(seeded_tracker):
    read_habit = next(h for h in seeded_tracker.list_habits() if h.task == "Read 30min")
    # Read 30min's current 14-day streak is also its longest ever.
    assert analytics.get_longest_streak_habit(read_habit) == 14


def test_get_longest_streak_all_matches_best_habit(seeded_tracker):
    # The single longest streak across ALL habits must equal the max of each
    # individual habit's longest streak (cross-checks get_longest_streak_habit).
    expected = max(h.get_longest_streak() for h in seeded_tracker.list_habits())
    assert analytics.get_longest_streak_all(seeded_tracker) == expected
    assert expected >= 14  # Read 30min's streak sets a known floor


def test_get_longest_streak_all_empty_tracker_is_zero():
    empty_tracker = HabitTracker(":memory:")
    assert analytics.get_longest_streak_all(empty_tracker) == 0


def test_struggled_habits_last_month_none_when_all_above_threshold(seeded_tracker, as_of):
    # Every seeded habit completes at least 50% of its recent periods, so
    # none of them should be reported as struggling.
    struggling = analytics.struggled_habits_last_month(seeded_tracker, as_of=as_of)
    assert struggling == []


def test_struggled_habits_last_month_detects_a_genuinely_struggling_habit(as_of):
    from habit_tracker.habit import Habit
    from datetime import timedelta

    tracker = HabitTracker(":memory:")
    lazy_habit = Habit(task="Floss", periodicity="daily")
    # Only 1 out of the last 4 days completed -> 25%, below the 50% threshold.
    lazy_habit.check_off(as_of - timedelta(days=3))
    tracker.habits[lazy_habit.id] = lazy_habit

    good_habit = Habit(task="Stretch", periodicity="daily")
    for offset in range(4):
        good_habit.check_off(as_of - timedelta(days=offset))
    tracker.habits[good_habit.id] = good_habit

    struggling = analytics.struggled_habits_last_month(tracker, as_of=as_of)
    struggling_tasks = {h.task for h in struggling}
    assert struggling_tasks == {"Floss"}


def test_habits_sorted_by_current_streak_descending(seeded_tracker, as_of):
    ordered = analytics.habits_sorted_by_current_streak(seeded_tracker, as_of=as_of)
    streaks = [h.get_streak(as_of=as_of) for h in ordered]
    assert streaks == sorted(streaks, reverse=True)
