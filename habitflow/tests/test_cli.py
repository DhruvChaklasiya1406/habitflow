"""Tests for the CLI layer, using Click's CliRunner against a temp SQLite file."""

import pytest
from click.testing import CliRunner

from habit_tracker.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "cli_test.db")


def test_create_and_list(runner, db_path):
    create_result = runner.invoke(cli, ["--db", db_path, "create", "Read 30min", "--period", "daily"])
    assert create_result.exit_code == 0
    assert "Created habit" in create_result.output

    list_result = runner.invoke(cli, ["--db", db_path, "list"])
    assert list_result.exit_code == 0
    assert "Read 30min" in list_result.output


def test_list_with_no_habits(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "list"])
    assert result.exit_code == 0
    assert "No habits yet" in result.output


def test_checkoff_marks_habit_complete(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "create", "Workout", "--period", "daily"])
    list_output = runner.invoke(cli, ["--db", db_path, "list"]).output
    habit_id = list_output.split("[")[1].split("]")[0]

    result = runner.invoke(cli, ["--db", db_path, "checkoff", habit_id])
    assert result.exit_code == 0
    assert "completed" in result.output


def test_checkoff_unknown_id_fails_cleanly(runner, db_path):
    result = runner.invoke(cli, ["--db", db_path, "checkoff", "doesnotexist"])
    assert result.exit_code != 0
    assert "No habit found" in result.output


def test_delete_habit(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "create", "Workout", "--period", "daily"])
    list_output = runner.invoke(cli, ["--db", db_path, "list"]).output
    habit_id = list_output.split("[")[1].split("]")[0]

    result = runner.invoke(cli, ["--db", db_path, "delete", habit_id])
    assert result.exit_code == 0
    assert "Deleted habit" in result.output

    list_after = runner.invoke(cli, ["--db", db_path, "list"]).output
    assert "No habits yet" in list_after


def test_seed_command_populates_five_habits(runner, db_path):
    seed_result = runner.invoke(cli, ["--db", db_path, "seed"])
    assert seed_result.exit_code == 0

    list_result = runner.invoke(cli, ["--db", db_path, "list"])
    for task in ["Brush teeth", "Workout", "Read 30min", "Dentist visit", "Team meeting"]:
        assert task in list_result.output


def test_analytics_longest_metric(runner, db_path):
    runner.invoke(cli, ["--db", db_path, "seed"])
    result = runner.invoke(cli, ["--db", db_path, "analytics", "--metric", "longest"])
    assert result.exit_code == 0
    assert "Longest streak" in result.output
