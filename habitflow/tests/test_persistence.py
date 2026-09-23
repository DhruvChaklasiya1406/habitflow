"""Tests for db.py and the HabitTracker CRUD flows: creation, editing,
deletion, and round-tripping through SQLite (using an in-memory DB)."""

from datetime import datetime

import pytest

from habit_tracker import db
from habit_tracker.habit import Habit
from habit_tracker.tracker import HabitTracker


@pytest.fixture
def conn():
    connection = db.get_connection(":memory:")
    db.init_db(connection)
    yield connection
    connection.close()


def test_init_db_creates_tables(conn):
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert {"habits", "completions"}.issubset(tables)


def test_save_and_load_habit_round_trip(conn):
    habit = Habit(task="Read 30min", periodicity="daily")
    habit.check_off(datetime(2026, 1, 1, 9, 0))
    habit.check_off(datetime(2026, 1, 2, 9, 0))

    db.save_habit(conn, habit)
    loaded = db.load_habits(conn)

    assert len(loaded) == 1
    assert loaded[0].id == habit.id
    assert loaded[0].task == "Read 30min"
    assert loaded[0].periodicity == "daily"
    assert len(loaded[0].completions) == 2


def test_add_completion_appends_without_rewriting_habit(conn):
    habit = Habit(task="Workout", periodicity="daily")
    db.save_habit(conn, habit)

    db.add_completion(conn, habit.id, datetime(2026, 1, 1, 9, 0))
    loaded = db.load_habits(conn)[0]
    assert len(loaded.completions) == 1


def test_delete_habit_cascades_to_completions(conn):
    habit = Habit(task="Read 30min", periodicity="daily")
    habit.check_off(datetime(2026, 1, 1, 9, 0))
    db.save_habit(conn, habit)

    db.delete_habit(conn, habit.id)

    assert db.load_habits(conn) == []
    remaining_completions = conn.execute(
        "SELECT * FROM completions WHERE habit_id = ?", (habit.id,)
    ).fetchall()
    assert remaining_completions == []


# ----------------------------------------------------------------------
# HabitTracker CRUD (creation / editing / deletion) with a live in-memory DB
# ----------------------------------------------------------------------

@pytest.fixture
def tracker():
    t = HabitTracker(":memory:")
    yield t
    t.close()


def test_tracker_add_habit_persists_immediately(tracker):
    habit = tracker.add_habit("Meditate", "daily")
    reloaded = db.load_habits(tracker.conn)
    assert any(h.id == habit.id for h in reloaded)


def test_tracker_edit_habit_updates_task_and_periodicity(tracker):
    habit = tracker.add_habit("Meditate", "daily")
    updated = tracker.edit_habit(habit.id, task="Meditate 10min", periodicity="weekly")
    assert updated.task == "Meditate 10min"
    assert updated.periodicity == "weekly"

    reloaded = next(h for h in db.load_habits(tracker.conn) if h.id == habit.id)
    assert reloaded.task == "Meditate 10min"
    assert reloaded.periodicity == "weekly"


def test_tracker_edit_habit_rejects_invalid_periodicity(tracker):
    habit = tracker.add_habit("Meditate", "daily")
    with pytest.raises(ValueError):
        tracker.edit_habit(habit.id, periodicity="yearly")


def test_tracker_delete_habit_removes_from_memory_and_db(tracker):
    habit = tracker.add_habit("Meditate", "daily")
    tracker.delete_habit(habit.id)
    assert habit.id not in tracker.habits
    assert db.load_habits(tracker.conn) == []


def test_tracker_delete_unknown_habit_raises_keyerror(tracker):
    with pytest.raises(KeyError):
        tracker.delete_habit("does-not-exist")


def test_tracker_check_off_persists_completion(tracker):
    habit = tracker.add_habit("Meditate", "daily")
    recorded = tracker.check_off(habit.id, timestamp=datetime(2026, 1, 1, 9, 0))
    assert recorded is True

    reloaded = next(h for h in db.load_habits(tracker.conn) if h.id == habit.id)
    assert len(reloaded.completions) == 1


def test_tracker_reloads_existing_data_on_reconnect(tmp_path):
    db_path = str(tmp_path / "habitflow_test.db")

    tracker1 = HabitTracker(db_path)
    habit = tracker1.add_habit("Stretch", "daily")
    tracker1.check_off(habit.id, timestamp=datetime(2026, 1, 1, 9, 0))
    tracker1.close()

    tracker2 = HabitTracker(db_path)
    reloaded = tracker2.get_habit(habit.id)
    assert reloaded.task == "Stretch"
    assert len(reloaded.completions) == 1
    tracker2.close()
