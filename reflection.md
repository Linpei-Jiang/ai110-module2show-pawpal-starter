# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
    1. There should be a class to add/remove/edit pets information
    2. Add/edit owner information
    3. Schedule/edit a walk for the pet
    4. Cancel a scheduled walk, and edit or reschedule it
- What classes did you include, and what responsibilities did you assign to each?
    1. Owner: stores owner info (name, email, phone) and their pets; can be added, edited, or removed
    2. Pet: stores pet info (name, species, breed, age) and links back to its owner; can be added, edited, or removed
    3. Walk: a single scheduled walk for a pet (start time, duration, status); can be scheduled or cancelled
    4. WalkScheduler: manages all walks, with methods to schedule, cancel, reschedule, and edit them, and to look up walks by pet
    - Edit methods live on Owner and Pet themselves, since information is easy to enter by mistake and needs fixing.
    - (This first design was later simplified into Task, Pet, Owner, and Scheduler; see Design changes below.)

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

1. **Moved add/remove out of Owner and Pet into a new `PawPalSystem` class.** Methods like `Owner.add_owner()` made no sense because an object has to exist before it can add itself. `PawPalSystem` now creates and removes owners and pets, and `Owner` and `Pet` keep only their `edit_*` methods. This also gives one place to keep `Owner.pets` and `Pet.owner` in sync, since they describe the same relationship.
2. **Added `Pet.walks` and `Owner.get_walks()`.** Walks pointed to a pet, but a pet could not see its walks, and nothing connected an owner to their walks. The relationships now run in both directions.
3. **Replaced the free-form `status` string with a `WalkStatus` enum** (`SCHEDULED`, `COMPLETED`, `CANCELLED`) so a typo like "canceled" cannot silently break the logic.
4. **Switched the scheduler's `walks` and the system's `owners`/`pets` from lists to dictionaries keyed by id**, so looking up a walk, pet, or owner by id is no longer a scan of the whole list.
5. **Reworked the design into four classes: `Task`, `Pet`, `Owner`, and `Scheduler`.** Once I started implementing, the extra layers (`Walk`, `PawPalSystem`, `WalkScheduler`) were more structure than the app needs.
    - `Walk` became `Task`, a general activity (description, time, frequency, completed) so it can cover feeding and medication as well as walks.
    - `PawPalSystem` went away: `Owner.add_pet()` / `remove_pet()` now keep `Owner.pets` and `Pet.owner` in sync directly, and `Pet.add_task()` does the same for `Pet.tasks` and `Task.pet`.
    - The scheduler no longer keeps its own copy of the tasks. `Owner.get_all_tasks()` gathers every pet's tasks, and `Scheduler` reads from that, so there is one source of truth and it works across multiple pets.
    - The id fields and the id-keyed dictionaries are gone, because objects now reference each other directly. The `WalkStatus` enum became a simple `completed` flag plus a `Frequency` enum (`ONCE`, `DAILY`, `WEEKLY`).
    - Added recurring tasks: completing a daily or weekly task through `Scheduler.complete_task()` creates the next occurrence automatically.
6. **Added scheduling improvements after a second AI review of the logic.**
    - Tasks now have a `duration_minutes`, so conflicts mean overlapping time windows, not just the exact same minute. Conflict detection sorts once and sweeps instead of comparing every pair, and `find_next_free_slot()` suggests a clear time.
    - The three separate getters were folded into one `filter_tasks(pet, completed, day)` so filters can be combined.
    - Fixed a bug where completing the same recurring task twice created duplicate next occurrences, made late completions skip dates already in the past, and added `series_id` so `cancel_series()` can remove all repeats.
    - Added overdue tasks, optional weekly weekdays, and input validation in `Scheduler.add_task()`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Tradeoff: conflict detection only warns, and it only looks at time windows.** The scheduler flags two pending tasks when their start-to-end windows overlap (start time plus `duration_minutes`), whether they belong to the same pet or different pets. It returns a warning message and still lets the task be added. It does not block the task, move it, or decide which task should win. It also ignores things a real owner cares about, like travel time between tasks, and it treats back-to-back tasks (8:00-8:30 and 8:30-9:00) as fine.

I chose this because the owner is the only one who knows which task matters more. A walk that overlaps a feeding might be fine, since the owner can feed the cat and then leave. Auto-rescheduling would make decisions the app cannot justify, and raising an error would stop someone from entering a task they really do intend to do. A plain warning is also much simpler to build and test, and `find_next_free_slot()` gives the owner a one-step way to fix a clash if they want one.

**Related tradeoff from reviewing the algorithm (readability vs. performance):** I asked the AI how `find_conflicts()` could be simplified. It suggested replacing my sort-and-sweep loop with `itertools.combinations(tasks, 2)` and `Task.overlaps`, a one-line list comprehension. I checked it against my version on 300 random schedules and it returned the same pairs, and it is easier to read because it reuses `overlaps` instead of repeating the overlap rule. But it compares every pair of tasks: it took about 24 seconds for 5,000 tasks, against about 10 milliseconds for the sweep. At real household size (a few dozen tasks) either would be instant, so I kept the sweep, since it is already tested, scales better, and is short enough to read with its comment. If the app only ever handled a handful of tasks, I would switch to the shorter version.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code for most of the project: turning my brainstormed classes into a Mermaid UML diagram, generating dataclass stubs from that UML, reviewing the stubs for design problems, implementing the core classes, writing the demo script in `main.py`, drafting tests, and adding docstrings and README text. The most helpful prompt was asking it to check my skeleton for missing relationships and logic bottlenecks, because that review is what pushed the design forward. Prompts that gave concrete requirements (for example "the Scheduler must read from an Owner method that returns every pet's tasks") worked better than open-ended ones.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

**What AI suggested:** its review of my first skeleton suggested adding a `PawPalSystem` manager class, `Pet.walks`, a status enum, and id-keyed dictionaries.

**What I accepted and rejected:** I accepted the review's main points (add/remove methods did not belong on the objects themselves, and relationships needed to run in both directions). But I did not keep that design for long. I replaced `Walk`, `PawPalSystem`, and `WalkScheduler` with the simpler `Task`, `Pet`, `Owner`, `Scheduler` structure, dropped the manual ids and dictionaries, and required the `Scheduler` to read from `Owner.get_all_tasks()` instead of keeping its own list of walks. The AI's version had two copies of the data, and mine has one source of truth.

**How I verified it:** I ran `main.py` and checked that tasks added out of order printed sorted by time and that tasks from both pets appeared together. I also ran a quick script checking that conflicts are detected, that completing a daily task adds tomorrow's task, and that cancelling removes it. I wrote `pytest` tests for marking a task complete and for adding a task to a pet. I also compared the final code against the UML and updated the diagram to match.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
