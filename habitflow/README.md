# HabitFlow

A command-line habit tracker built for the *Object Oriented and Functional
Programming with Python* course (DLBDSOOFPP01) at IU International University
of Applied Sciences — Portfolio, Phase 3 (Finalization).

HabitFlow lets you define daily or weekly habits, check them off, and run
analytics (streaks, struggling habits, filters) over your history. It
combines three programming paradigms on purpose, as required by the
assignment:

| Layer                     | Paradigm    | File                         |
|---------------------------|-------------|------------------------------|
| Habit domain model         | OOP         | `habit_tracker/habit.py`     |
| Data persistence           | Procedural  | `habit_tracker/db.py`        |
| Streak / report analytics  | Functional  | `habit_tracker/analytics.py` |
| CLI                        | —           | `habit_tracker/cli.py`       |

## Features

- Create, edit, check off, and delete habits (`daily` or `weekly`).
- Append-only completion log stored in SQLite — full audit trail, no
  overwritten history.
- Streak calculation that respects each habit's own periodicity (a
  daily habit's "period" is a calendar day; a weekly habit's "period"
  is an ISO week, Monday–Sunday).
- A functional analytics module with 5 pure functions:
  - `get_all_habits`
  - `get_habits_by_period`
  - `get_longest_streak_all`
  - `get_longest_streak_habit`
  - `struggled_habits_last_month`
  - (plus `habits_sorted_by_current_streak` as a bonus report helper)
- 5 predefined habits pre-loaded with 4 weeks (28 days) of deterministic
  test data, exactly matching the table below — used both as a demo
  dataset and as a fixture for the unit tests.
- 41 automated tests (`pytest`), 92% overall coverage, **100% coverage
  of the analytics module**.

## Predefined habits & 4-week test data

| Habit         | Periodicity | Completions | Current streak |
|---------------|-------------|-------------|-----------------|
| Brush teeth   | daily       | 25 / 28     | 4 days          |
| Workout       | daily       | 18 / 28     | 0 days          |
| Read 30min    | daily       | 22 / 28     | 14 days         |
| Dentist visit | weekly      | 3 / 4       | 3 weeks         |
| Team meeting  | weekly      | 4 / 4       | 4 weeks         |

Load this data at any time with:

```bash
habit-tracker seed
```

## Project structure

```
habitflow/
├── habit_tracker/
│   ├── __init__.py
│   ├── habit.py         # Habit class (OOP)
│   ├── tracker.py       # HabitTracker: wires Habit <-> db.py together
│   ├── db.py             # SQLite persistence (procedural)
│   ├── analytics.py     # Pure functional analytics
│   ├── seed_data.py     # Predefined habits + 4-week test data generator
│   └── cli.py           # Click-based command line interface
├── tests/
│   ├── test_habit.py         # Habit creation, completion, streak logic
│   ├── test_persistence.py   # db.py + habit creation/editing/deletion via HabitTracker
│   ├── test_analytics.py     # Every analytics function individually
│   └── test_cli.py           # End-to-end CLI commands
├── screenshots/          # CLI run + pytest/coverage screenshots
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

Requires Python 3.9+.

```bash
git clone <this-repo-url>
cd habitflow
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

```bash
# Load the 5 predefined habits with 4 weeks of history
habit-tracker seed

# List every habit and its current streak
habit-tracker list

# Create a new habit
habit-tracker create "Drink 2L water" --period daily

# Mark a habit done for the current period (use the id shown by `list`)
habit-tracker checkoff <habit-id>

# Delete a habit
habit-tracker delete <habit-id>

# Run analytics
habit-tracker analytics --metric all          # streak per habit
habit-tracker analytics --metric by-period --period weekly
habit-tracker analytics --metric longest      # best streak across all habits
habit-tracker analytics --metric struggling   # habits below 50% completion recently
```

By default, all data is stored in `habitflow.db` in the current directory.
Pass `--db path/to/file.db` to use a different file.

## Running the tests

```bash
pytest -v --cov=habit_tracker --cov-report=term-missing
```

Current result: **41 passed**, 92% overall coverage, 100% on `analytics.py`
and `db.py`.

## Screenshots

`screenshots/01_cli_demo.png` — seeding data, listing habits, checking one
off, and running analytics.

`screenshots/02_pytest_coverage.png` — full test + coverage run.

`screenshots/03_pytest_verbose.png` — per-test detail for the habit and
analytics test modules.

## Design notes

- **Why an append-only completion log?** Overwriting a "last completed"
  timestamp would destroy history and make streak/analytics calculations
  unverifiable. Every check-off is a new row; nothing is ever deleted
  except when the whole habit is deleted.
- **Why SQLite?** Zero setup, ACID-safe, ships with Python's standard
  library, and supports an in-memory (`:memory:`) mode that makes the
  test suite fast and fully isolated from the real database file.
- **Why separate `db.py` (procedural) from `tracker.py` (OOP) from
  `analytics.py` (functional)?** This is a direct requirement of the
  assignment: the project must combine all three paradigms in a way
  where each concern lives in its own, independently testable module.

## Author

Dhruv Nareshbhai Chaklasiya — Matriculation 4242870 — DLBDSOOFPP01
