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

## Implementation summary

The core logic lives in [pawpal_system.py](pawpal_system.py) and is built from four dataclasses:

- **`Task`**: one activity (description, time, frequency, completed). A daily or weekly task can generate its next occurrence.
- **`Pet`**: pet details plus its own list of `Task`s.
- **`Owner`**: holds multiple `Pet`s. `get_all_tasks()` gathers every pet's tasks into one list.
- **`Scheduler`**: the brain. It is given an `Owner` and always reads tasks through `owner.get_all_tasks()`, so it works across all pets instead of one. It sorts by time, filters by day, pet, or pending status, flags tasks scheduled at the same time, and completes tasks (creating the next one for recurring tasks).

How they fit together: `Owner` → many `Pet` → many `Task`, with each child linking back to its parent. `Scheduler` sits on top of the `Owner` and holds no task data of its own. [main.py](main.py) is a demo script that builds an owner, two pets, and several tasks, then prints today's schedule. [tests/test_pawpal.py](tests/test_pawpal.py) holds the tests, and [diagrams/uml.mmd](diagrams/uml.mmd) has the class diagram.

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

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

[x] 07:30 AM  Rex    Morning walk (daily)
[ ] 07:30 AM  Luna   Breakfast (daily)
[ ] 12:15 PM  Luna   Flea medication (weekly)
[ ] 06:00 PM  Rex    Evening walk (daily)

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
- `get_conflict_warnings()` turns those pairs into readable messages, such as `Warning: Luna's 'Grooming' (09:00 AM-09:30 AM) overlaps Rex's 'Vet check' (09:00 AM-10:00 AM).` or `Warning: Luna has two tasks at the same time: ...` for the same pet.
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

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
