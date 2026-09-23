"""
cli.py
======

Command-line interface for HabitFlow, built with Click.

This module is intentionally "thin": every command just parses its
arguments, delegates to :class:`~habit_tracker.tracker.HabitTracker` or
:mod:`habit_tracker.analytics`, and formats the result. No business
logic lives here.
"""

from __future__ import annotations

import click

from . import analytics
from .seed_data import seed_tracker
from .tracker import HabitTracker

DB_PATH = "habitflow.db"


def _short_id(habit_id: str) -> str:
    """Show only the first 8 characters of a UUID for readable output."""
    return habit_id[:8]


@click.group()
@click.option("--db", "db_path", default=DB_PATH, show_default=True, help="Path to the SQLite database file.")
@click.pass_context
def cli(ctx: click.Context, db_path: str) -> None:
    """HabitFlow -- a simple command-line habit tracker."""
    ctx.ensure_object(dict)
    ctx.obj["tracker"] = HabitTracker(db_path)


@cli.command()
@click.argument("task")
@click.option("--period", "periodicity", type=click.Choice(["daily", "weekly"]), default="daily", show_default=True)
@click.pass_context
def create(ctx: click.Context, task: str, periodicity: str) -> None:
    """Create a new habit, e.g. `habit-tracker create "Read 30min" --period daily`."""
    tracker: HabitTracker = ctx.obj["tracker"]
    habit = tracker.add_habit(task, periodicity)
    click.echo(f"✔ Created habit: {habit.task} ({habit.periodicity}) [id={_short_id(habit.id)}]")


@cli.command(name="list")
@click.pass_context
def list_habits(ctx: click.Context) -> None:
    """List every tracked habit with its current streak."""
    tracker: HabitTracker = ctx.obj["tracker"]
    habits = analytics.get_all_habits(tracker)
    if not habits:
        click.echo("No habits yet. Create one with `habit-tracker create \"<task>\"`.")
        return
    for habit in habits:
        click.echo(
            f"[{_short_id(habit.id)}] {habit.task:20s} {habit.periodicity:7s} "
            f"streak={habit.get_streak()} completions={len(habit.completions)}"
        )


@cli.command()
@click.argument("habit_id")
@click.pass_context
def checkoff(ctx: click.Context, habit_id: str) -> None:
    """Mark a habit as completed for the current period, e.g. `checkoff --id H3`."""
    tracker: HabitTracker = ctx.obj["tracker"]
    matches = [h for h in tracker.list_habits() if h.id.startswith(habit_id)]
    if not matches:
        raise click.ClickException(f"No habit found matching id {habit_id!r}")
    habit = matches[0]
    recorded = tracker.check_off(habit.id)
    if recorded:
        click.echo(f"✔ Habit {habit.task} completed — streak: {habit.get_streak()} 🔥")
    else:
        click.echo(f"Habit {habit.task} was already completed for this period.")


@cli.command()
@click.argument("habit_id")
@click.pass_context
def delete(ctx: click.Context, habit_id: str) -> None:
    """Delete a habit permanently."""
    tracker: HabitTracker = ctx.obj["tracker"]
    matches = [h for h in tracker.list_habits() if h.id.startswith(habit_id)]
    if not matches:
        raise click.ClickException(f"No habit found matching id {habit_id!r}")
    tracker.delete_habit(matches[0].id)
    click.echo(f"✔ Deleted habit {matches[0].task}")


@cli.command()
@click.option(
    "--metric",
    type=click.Choice(["all", "by-period", "longest", "struggling"]),
    default="all",
    show_default=True,
)
@click.option("--period", "periodicity", type=click.Choice(["daily", "weekly"]), default="daily")
@click.pass_context
def analytics_cmd(ctx: click.Context, metric: str, periodicity: str) -> None:
    """Run an analytics report over the tracked habits."""
    tracker: HabitTracker = ctx.obj["tracker"]

    if metric == "all":
        for habit in analytics.get_all_habits(tracker):
            click.echo(f"{habit.task}: streak={habit.get_streak()}")
    elif metric == "by-period":
        for habit in analytics.get_habits_by_period(tracker, periodicity):
            click.echo(f"{habit.task} ({periodicity})")
    elif metric == "longest":
        click.echo(f"Longest streak across all habits: {analytics.get_longest_streak_all(tracker)} periods")
    elif metric == "struggling":
        struggling = analytics.struggled_habits_last_month(tracker)
        if not struggling:
            click.echo("No struggling habits — nice work!")
        for habit in struggling:
            click.echo(f"⚠ {habit.task} — completion rate below 50% over the last 4 periods")


cli.add_command(analytics_cmd, name="analytics")


@cli.command()
@click.pass_context
def seed(ctx: click.Context) -> None:
    """Populate the database with 5 predefined habits and 4 weeks of test data."""
    tracker: HabitTracker = ctx.obj["tracker"]
    seed_tracker(tracker)
    click.echo("✔ Seeded 5 predefined habits with 4 weeks of history.")


def main() -> None:  # pragma: no cover - thin entry point
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()
