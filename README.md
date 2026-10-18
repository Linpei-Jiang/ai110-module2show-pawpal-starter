# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Features

- **Multiple pets, one owner:** an owner manages any number of pets, and every feature below works across all of them.
- **Sorting by time:** tasks are always shown in chronological order, with ties broken by pet name so the order never shuffles (`Scheduler.sort_by_time()`).
- **Filtering:** narrow the list by pet name, pending or completed status, or day, alone or combined (`Scheduler.filter_tasks()`).
- **Conflict warnings:** two tasks conflict when their time windows overlap, whether they belong to the same pet or different pets. The app shows a readable warning and suggests the next free slot, and never blocks you from adding the task (`find_conflicts()`, `get_conflict_warnings()`, `conflict_warning_for()`, `find_next_free_slot()`).
- **Daily and weekly recurrence:** completing a repeating task automatically creates the next occurrence, optionally only on chosen weekdays, and never duplicates it (`Task.mark_complete()`, `Task.next_occurrence()`).
- **Cancel a whole series:** remove every repeat of a recurring task at once (`Scheduler.cancel_series()`).
- **Overdue tracking:** pending tasks whose time has passed are flagged (`Scheduler.get_overdue_tasks()`).
- **Input validation:** empty descriptions, zero durations, and times in the past are rejected with a clear message (`Scheduler.add_task()`).

Details for each algorithm are in [Smarter Scheduling](#-smarter-scheduling).

## Implementation summary

The core logic lives in [pawpal_system.py](pawpal_system.py) and is built from four dataclasses:

- **`Task`**: one activity (description, time, frequency, completed). A daily or weekly task can generate its next occurrence.
- **`Pet`**: pet details plus its own list of `Task`s.
- **`Owner`**: holds multiple `Pet`s. `get_all_tasks()` gathers every pet's tasks into one list.
- **`Scheduler`**: the brain. It is given an `Owner` and always reads tasks through `owner.get_all_tasks()`, so it works across all pets instead of one. It sorts by time, filters by day, pet, or pending status, warns about overlapping tasks, and completes tasks (creating the next one for recurring tasks).

How they fit together: `Owner` → many `Pet` → many `Task`, with each child linking back to its parent. `Scheduler` sits on top of the `Owner` and holds no task data of its own. [main.py](main.py) is a demo script that builds an owner, two pets, and several tasks, then prints today's schedule. [tests/test_pawpal.py](tests/test_pawpal.py) holds the tests, and [diagrams/uml_final.mmd](diagrams/uml_final.mmd) has the final class diagram (Mermaid).

```bash
python main.py
```

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Today's schedule as printed by `python main.py` (sorted by time, with conflict warnings below it). The full run is shown in the [Demo Walkthrough](#-demo-walkthrough).

```
Today's Schedule for Alex Rivera
[ ] 07:30 AM-08:00 AM  Rex    Morning walk (once)
[x] 07:40 AM-07:50 AM  Luna   Breakfast (once)
[ ] 09:00 AM-09:30 AM  Luna   Grooming (once)
[ ] 09:00 AM-10:00 AM  Rex    Vet check (once)
Warning: Luna's 'Grooming' (09:00 AM-09:30 AM) overlaps Rex's 'Vet check' (09:00 AM-10:00 AM).
```

## 🧪 Testing PawPal+

```bash
python -m pytest
```

(Run it from the project root with your virtual environment active, after `pip install -r requirements.txt`.)

The 41 tests in [tests/test_pawpal.py](tests/test_pawpal.py) cover the scheduler logic in [pawpal_system.py](pawpal_system.py):

- **Sorting:** tasks come back in chronological order across multiple pets, same-time ties are stable, midnight boundaries work, and sorting never modifies the original lists.
- **Filtering:** pet, pet name (case-insensitive), completion status and day filters, alone and combined.
- **Recurring tasks:** completing a daily or weekly task creates exactly one new task for the next occurrence on the same pet. Covered edge cases: year and leap-day boundaries, weekly tasks on chosen weekdays wrapping over the weekend, late completion skipping past dates, completing twice, one-off tasks, and tasks with no pet.
- **Conflict detection:** same-time tasks are flagged for one pet and for different pets, overlapping durations are caught, back-to-back tasks are not, three-way clashes give three pairs, and completing or cancelling a task clears its conflict. Warnings are plain messages that never raise.
- **Free slots, validation and cleanup:** next-free-slot search, rejection of bad input (empty description, bad duration, past time), cancelling a whole recurring series, and removing the exact task or pet when two look identical.
- **Empty states:** an owner with no pets and a pet with no tasks.

Writing these tests found one real bug: removing a task or pet used `list.remove()`, which matches by equality, so cancelling the second of two identical tasks removed the first and left the cancelled one orphaned in the list. Removal now matches by identity.

Sample test output:

```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/gingerjournal/Desktop/AI101-CodePath/ai110-module2show-pawpal-starter
collected 41 items

tests/test_pawpal.py .........................................           [100%]

============================== 41 passed in 0.04s ==============================
```

**Confidence level: ⭐⭐⭐⭐ (4 out of 5).** The core scheduling logic (sorting, filtering, recurrence and conflict detection) is covered by happy-path and edge-case tests that all pass. I held back the fifth star because the Streamlit UI in `app.py` has no automated tests (I only checked it by hand and with a short scripted run), conflicts are only compared within a single timeline with no time zone or daylight-saving handling, and nothing is saved between sessions.

## 📐 Smarter Scheduling

Everything below lives in [pawpal_system.py](pawpal_system.py). Every feature works across all of an owner's pets, because `Scheduler` always reads tasks through `Owner.get_all_tasks()`.

| Feature | Method(s) |
|---------|-----------|
| Sorting | `Scheduler.sort_by_time()` |
| Filtering | `Scheduler.filter_tasks()`, `get_tasks_for_day()`, `get_tasks_for_pet()`, `get_pending_tasks()`, `get_overdue_tasks()` |
| Conflict detection | `Scheduler.find_conflicts()`, `get_conflict_warnings()`, `conflict_warning_for()`, `conflicts_with()`, `find_next_free_slot()` |
| Recurring tasks | `Task.mark_complete()`, `Task.next_occurrence()`, `Scheduler.complete_task()`, `Scheduler.cancel_series()` |
| Validation | `Scheduler.add_task()` |

### Sorting
`Scheduler.sort_by_time()` returns tasks earliest first, using `sorted()` with a `(time, pet name)` key. Tasks at the same time are ordered by pet name, so the schedule never reshuffles between runs. It returns a new list and leaves the original alone.

### Filtering
`Scheduler.filter_tasks(pet=None, completed=None, day=None, pet_name=None)` keeps only the tasks that match every filter you pass, sorted by time. Filters left out are ignored, so they combine freely, for example `filter_tasks(pet_name="luna", completed=False)` for Luna's pending tasks. Pet names are matched case-insensitively. The convenience methods build on it: `get_tasks_for_day()`, `get_tasks_for_pet()`, `get_pending_tasks()`, and `get_overdue_tasks()` (pending tasks whose time has already passed).

### Conflict detection
Each task has a `duration_minutes`, so two tasks conflict when their time windows overlap, whether they belong to the same pet or different pets. A walk from 8:00 to 8:30 overlaps a feeding at 8:15, but a task that starts exactly when another ends is fine. Completed tasks are ignored.

- `find_conflicts()` finds every overlapping pair of pending tasks. It sorts once, then sweeps through the tasks keeping the ones still running, which avoids comparing every pair.
- `get_conflict_warnings()` turns those pairs into readable messages, such as `Warning: Luna's 'Grooming' (09:00 AM-09:30 AM) overlaps Rex's 'Vet check' (09:00 AM-10:00 AM).` or `Warning: Luna has overlapping tasks: ...` for the same pet.
- `conflict_warning_for(task, pet)` checks a task before it is added and returns a warning string or `None`.
- `find_next_free_slot(after, duration_minutes)` suggests the earliest time a task of that length fits.

Detection is deliberately lightweight: it returns warning messages and never raises or blocks. The owner decides what to do, and the Streamlit app shows the warning plus the next free slot when you add an overlapping task.

### Recurring tasks
A task can repeat `once`, `daily`, or `weekly` (weekly tasks can optionally run only on chosen weekdays). When `Task.mark_complete()` is called, which `Scheduler.complete_task()` also does, a repeating task creates its next occurrence on the same pet automatically.

- The new task keeps the same description, duration and weekdays, and shares a `series_id` with the original.
- Finishing a task late skips dates already in the past, so the next occurrence is always in the future.
- Completing the same task twice never creates a duplicate.
- `Scheduler.cancel_series()` removes every task in a series, while `cancel_task()` removes just one.

### Validation
`Scheduler.add_task()` rejects an empty description, a duration under 1 minute, and a time in the past by raising `ValueError`. Overlaps are not errors; they only produce warnings.

## 📸 Demo Walkthrough

### Run it

```bash
streamlit run app.py   # the web app
python main.py         # a command-line demo of the scheduler
```

### What the app lets you do

The Streamlit app ([app.py](app.py)) has four sections, top to bottom:

1. **Owner and pets:** set the owner's name and add pets (name and species). Duplicate names are rejected.
2. **Schedule a task:** choose a pet, a description, a date and time, a duration, and how often it repeats (once, daily, or weekly, with optional weekdays). Bad input such as a time in the past shows an error. If the new task overlaps another one, it is still added, and a warning appears with the next free slot.
3. **Today's schedule:** a time-sorted table of today's tasks with counts for tasks today, still to do, overdue, and conflicts. Overlapping tasks are marked with a warning icon, and a yellow warning box explains each clash in plain words and suggests a free time. If nothing clashes, a green message says so.
4. **Manage tasks:** filter by pet and by pending, completed, or all. Pick a task and mark it complete, cancel it, or cancel all of its repeats. Overdue tasks appear as red messages.

### Example workflow

1. Add two pets, for example **Rex** (dog) and **Luna** (cat).
2. Schedule Rex's **Morning walk** at 7:30 AM, repeating daily, for 30 minutes. (Pick today's date with a time later than now, or tomorrow's date, because the app rejects times in the past.)
3. Schedule Luna's **Breakfast** at 7:40 AM for 10 minutes. The app warns that it overlaps Rex's walk and suggests 8:00 AM as the next free slot; the task is still added.
4. Open **Today's schedule**. Both tasks appear in time order with a warning icon, the Conflicts counter shows 1, and the warning box describes the overlap.
5. Under **Manage tasks**, pick the Morning walk and press **Mark complete**. It is marked done, tomorrow's walk is created automatically, and the conflict disappears.
6. Filter by **Luna** or switch to **Completed** to see the filters in action.

### Scheduler behaviors on display

- **Sorting:** tasks entered out of order always appear earliest first.
- **Filtering:** by pet and by status, across all pets.
- **Conflict warnings:** same-pet and different-pet overlaps, as messages rather than errors.
- **Recurrence:** completing a daily or weekly task schedules the next one.
- **Validation:** past times and bad durations are rejected without crashing.

### Sample CLI output

`python main.py` adds tasks out of order, then prints them unsorted, sorted, filtered, and as today's schedule with conflict warnings. The date in the heading is the day you run it.

```
Warning: Rex's 'Morning walk' (07:30 AM-08:00 AM) overlaps Luna's 'Breakfast' (07:40 AM-07:50 AM).

Adding two tasks that clash with existing ones:
Warning: Luna's 'Grooming' (09:00 AM-09:30 AM) overlaps Rex's 'Vet check' (09:00 AM-10:00 AM).
Warning: Luna has overlapping tasks: 'Brush fur' (12:15 PM-12:25 PM) and 'Flea medication' (12:15 PM-12:20 PM).

Insertion order (unsorted, straight from the owner):
  [ ] 06:00 PM  Rex    Evening walk
  [ ] 07:30 AM  Rex    Morning walk
  [ ] 09:00 AM  Rex    Vet check
  [ ] 12:15 PM  Luna   Flea medication
  [x] 07:40 AM  Luna   Breakfast
  [ ] 04:00 PM  Luna   Play time
  [ ] 09:00 AM  Luna   Grooming
  [ ] 12:15 PM  Luna   Brush fur

Sorted by time:
  [ ] 07:30 AM  Rex    Morning walk
  [x] 07:40 AM  Luna   Breakfast
  [ ] 09:00 AM  Luna   Grooming
  [ ] 09:00 AM  Rex    Vet check
  [ ] 12:15 PM  Luna   Flea medication
  [ ] 12:15 PM  Luna   Brush fur
  [ ] 04:00 PM  Luna   Play time
  [ ] 06:00 PM  Rex    Evening walk

Filter: pet name 'rex':
  [ ] 07:30 AM  Rex    Morning walk
  [ ] 09:00 AM  Rex    Vet check
  [ ] 06:00 PM  Rex    Evening walk

Filter: pet name 'Luna':
  [x] 07:40 AM  Luna   Breakfast
  [ ] 09:00 AM  Luna   Grooming
  [ ] 12:15 PM  Luna   Flea medication
  [ ] 12:15 PM  Luna   Brush fur
  [ ] 04:00 PM  Luna   Play time

Filter: pending only:
  [ ] 07:30 AM  Rex    Morning walk
  [ ] 09:00 AM  Luna   Grooming
  [ ] 09:00 AM  Rex    Vet check
  [ ] 12:15 PM  Luna   Flea medication
  [ ] 12:15 PM  Luna   Brush fur
  [ ] 04:00 PM  Luna   Play time
  [ ] 06:00 PM  Rex    Evening walk

Filter: completed only:
  [x] 07:40 AM  Luna   Breakfast

Filter: Luna + pending:
  [ ] 09:00 AM  Luna   Grooming
  [ ] 12:15 PM  Luna   Flea medication
  [ ] 12:15 PM  Luna   Brush fur
  [ ] 04:00 PM  Luna   Play time

Today's Schedule for Alex Rivera (Sunday, October 18, 2026)
----------------------------------------------------------------
[ ] 07:30 AM-08:00 AM  Rex    Morning walk (once)
[x] 07:40 AM-07:50 AM  Luna   Breakfast (once)
[ ] 09:00 AM-09:30 AM  Luna   Grooming (once)
[ ] 09:00 AM-10:00 AM  Rex    Vet check (once)
[ ] 12:15 PM-12:20 PM  Luna   Flea medication (once)
[ ] 12:15 PM-12:25 PM  Luna   Brush fur (once)
[ ] 04:00 PM-04:20 PM  Luna   Play time (once)
[ ] 06:00 PM-06:45 PM  Rex    Evening walk (once)
Warning: Luna's 'Grooming' (09:00 AM-09:30 AM) overlaps Rex's 'Vet check' (09:00 AM-10:00 AM).
Warning: Luna has overlapping tasks: 'Flea medication' (12:15 PM-12:20 PM) and 'Brush fur' (12:15 PM-12:25 PM).
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
