from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class Task:
    """A single activity for a pet (walk, feeding, medication, ...)."""

    description: str
    time: datetime
    frequency: Frequency = Frequency.ONCE
    completed: bool = False
    pet: Optional[Pet] = field(default=None, repr=False, compare=False)
    duration_minutes: int = 30
    weekdays: list[int] = field(default_factory=list)  # weekly only; Monday=0 ... Sunday=6
    series_id: Optional[str] = None  # shared by every occurrence of one recurring task

    def __post_init__(self) -> None:
        """Give recurring tasks a series id so the whole series can be cancelled together."""
        if self.frequency is not Frequency.ONCE and self.series_id is None:
            self.series_id = uuid4().hex

    @property
    def end_time(self) -> datetime:
        """When this task finishes (start time plus duration)."""
        return self.time + timedelta(minutes=self.duration_minutes)

    def overlaps(self, other: Task) -> bool:
        """True if the two tasks' time windows overlap.

        Windows are half-open [start, end), so a task that starts exactly when another
        ends (8:00-8:30 then 8:30-9:00) is not an overlap.
        """
        return self.time < other.end_time and other.time < self.end_time

    def mark_complete(self, now: Optional[datetime] = None) -> Optional[Task]:
        """Flag this task as done and, if it repeats, schedule the next occurrence.

        For a daily or weekly task attached to a pet, a new Task is created for the next
        future date (see next_occurrence), added to the same pet, and returned. Returns
        None when nothing new is created: the task was already completed (so repeated
        calls never duplicate), it is a one-off, it has no pet, or the pet already has a
        task with the same description and time.

        Args:
            now: Moment of completion, used to skip occurrences already in the past.
                Defaults to the current time.
        """
        if self.completed:
            return None
        self.completed = True
        if self.pet is None:
            return None
        following = self.next_occurrence(after=now or datetime.now())
        if following is None:
            return None
        already_there = any(
            t.description == following.description and t.time == following.time
            for t in self.pet.tasks
        )
        return None if already_there else self.pet.add_task(following)

    def reschedule(self, new_time: datetime) -> None:
        """Move this task to a new date and time."""
        self.time = new_time

    def _step(self, start: datetime) -> datetime:
        """One recurrence step after `start`.

        Daily tasks move forward one day. Weekly tasks with chosen weekdays move to the
        next chosen weekday (searching up to 7 days ahead); otherwise they move exactly
        one week.
        """
        if self.frequency is Frequency.DAILY:
            return start + timedelta(days=1)
        if self.weekdays:
            for days in range(1, 8):
                candidate = start + timedelta(days=days)
                if candidate.weekday() in self.weekdays:
                    return candidate
        return start + timedelta(weeks=1)

    def next_occurrence(self, after: Optional[datetime] = None) -> Optional[Task]:
        """Build the next occurrence of a recurring task, or None for a one-off task.

        The copy keeps the description, frequency, duration, weekdays and series id, and
        starts uncompleted and unattached. If `after` is given, the recurrence steps
        forward until it lands strictly after that moment, so finishing a daily task two
        days late schedules the next one in the future, not in the past.
        """
        if self.frequency is Frequency.ONCE:
            return None
        next_time = self._step(self.time)
        while after is not None and next_time <= after:
            next_time = self._step(next_time)
        return Task(
            self.description,
            next_time,
            self.frequency,
            duration_minutes=self.duration_minutes,
            weekdays=list(self.weekdays),
            series_id=self.series_id,
        )


@dataclass
class Pet:
    """Stores pet details and that pet's list of tasks."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    owner: Optional[Owner] = field(default=None, repr=False, compare=False)
    tasks: list[Task] = field(default_factory=list)

    def edit_pet(self, name: str, species: str, breed: str, age: int) -> None:
        """Overwrite this pet's details."""
        self.name, self.species, self.breed, self.age = name, species, breed, age

    def add_task(self, task: Task) -> Task:
        """Attach a task to this pet and link the task back to the pet."""
        task.pet = self
        self.tasks.append(task)
        return task

    def remove_task(self, task: Task) -> None:
        """Detach a task from this pet (matched by identity, since equal-looking tasks can exist)."""
        self.tasks = [t for t in self.tasks if t is not task]
        task.pet = None


@dataclass
class Owner:
    """Manages multiple pets and gives access to all of their tasks."""

    name: str
    email: str = ""
    phone: str = ""
    pets: list[Pet] = field(default_factory=list)

    def edit_owner(self, name: str, email: str, phone: str) -> None:
        """Overwrite this owner's contact details."""
        self.name, self.email, self.phone = name, email, phone

    def add_pet(self, pet: Pet) -> Pet:
        """Add a pet to this owner and link the pet back to the owner."""
        pet.owner = self
        self.pets.append(pet)
        return pet

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner (matched by identity, not by equal-looking fields)."""
        self.pets = [p for p in self.pets if p is not pet]
        pet.owner = None

    def get_all_tasks(self) -> list[Task]:
        """Every pet's tasks combined into one list."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Scheduler:
    """The brain: organizes and manages tasks across all of an owner's pets."""

    owner: Owner

    def get_all_tasks(self) -> list[Task]:
        """Fetch every task for every pet via the owner."""
        return self.owner.get_all_tasks()

    @staticmethod
    def _sort_key(task: Task) -> tuple[datetime, str]:
        """Sort key: (time, pet name), so tasks at the same time always list in the same order."""
        return task.time, task.pet.name if task.pet else ""

    def sort_by_time(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """Return tasks ordered by time, earliest first.

        Args:
            tasks: Tasks to sort. Defaults to every task across all of the owner's pets.

        Returns:
            A new sorted list; the input list is not modified. Ties are broken by pet name.
        """
        tasks = self.get_all_tasks() if tasks is None else tasks
        return sorted(tasks, key=self._sort_key)

    def filter_tasks(
        self,
        pet: Optional[Pet] = None,
        completed: Optional[bool] = None,
        day: Optional[date] = None,
        pet_name: Optional[str] = None,
    ) -> list[Task]:
        """Return tasks that match every filter given, sorted by time.

        Filters left as None are ignored, so they can be combined freely, for example
        filter_tasks(pet_name="luna", completed=False) for Luna's pending tasks.

        Args:
            pet: Keep only this pet's tasks (matched by identity).
            completed: True for finished tasks, False for pending ones.
            day: Keep only tasks starting on this date.
            pet_name: Keep only tasks for the pet with this name (case-insensitive).
        """
        tasks = self.get_all_tasks()
        if pet is not None:
            tasks = [t for t in tasks if t.pet is pet]
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet and t.pet.name.lower() == pet_name.lower()]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        if day is not None:
            tasks = [t for t in tasks if t.time.date() == day]
        return self.sort_by_time(tasks)

    def get_tasks_for_day(self, day: Optional[date] = None, include_completed: bool = True) -> list[Task]:
        """Return one day's tasks (default: today) sorted by time."""
        return self.filter_tasks(day=day or date.today(), completed=None if include_completed else False)

    def get_tasks_for_pet(self, pet: Pet) -> list[Task]:
        """Return the given pet's tasks sorted by time."""
        return self.filter_tasks(pet=pet)

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks not yet completed, sorted by time."""
        return self.filter_tasks(completed=False)

    def get_overdue_tasks(self, now: Optional[datetime] = None) -> list[Task]:
        """Pending tasks whose start time is before `now` (default: the current time), sorted by time."""
        now = now or datetime.now()
        return [t for t in self.get_pending_tasks() if t.time < now]

    def find_conflicts(self) -> list[tuple[Task, Task]]:
        """Find every pair of pending tasks whose time windows overlap, across all pets.

        Sweep algorithm: walk the pending tasks in time order, keeping a list of earlier
        tasks that are still running when the current one starts. Each task overlaps
        exactly those active tasks. This costs one sort plus the work of reporting the
        overlaps, instead of comparing every pair. Completed tasks are ignored, and
        back-to-back tasks are not conflicts.

        Returns:
            (earlier, later) pairs in start-time order; empty if the schedule is clear.
        """
        conflicts: list[tuple[Task, Task]] = []
        active: list[Task] = []  # earlier tasks still running when the current one starts
        for task in self.get_pending_tasks():
            active = [a for a in active if a.end_time > task.time]
            conflicts.extend((a, task) for a in active)
            active.append(task)
        return conflicts

    def conflicts_with(self, task: Task) -> list[Task]:
        """Pending tasks whose windows overlap `task`, for checking a task before adding it."""
        return [t for t in self.get_pending_tasks() if t is not task and t.overlaps(task)]

    @staticmethod
    def _warning(a: Task, b: Task, pet_a: Optional[Pet] = None) -> str:
        """Human-readable warning for two overlapping tasks (same pet or different pets).

        `pet_a` names a's pet when `a` is not attached to one yet.
        """
        def span(t: Task) -> str:
            return f"{t.time:%I:%M %p}-{t.end_time:%I:%M %p}"

        pet_a = pet_a or a.pet
        name_a = pet_a.name if pet_a else "(no pet)"
        name_b = b.pet.name if b.pet else "(no pet)"
        if pet_a is b.pet:
            return f"Warning: {name_a} has two tasks at the same time: '{a.description}' ({span(a)}) and '{b.description}' ({span(b)})."
        return (
            f"Warning: {name_a}'s '{a.description}' ({span(a)}) overlaps "
            f"{name_b}'s '{b.description}' ({span(b)})."
        )

    def get_conflict_warnings(self) -> list[str]:
        """Turn each overlapping pair from find_conflicts() into a readable warning string.

        This is the lightweight conflict strategy: it reports problems as messages and
        never raises or blocks anything. Returns an empty list when nothing overlaps.
        """
        return [self._warning(a, b) for a, b in self.find_conflicts()]

    def conflict_warning_for(self, task: Task, pet: Optional[Pet] = None) -> Optional[str]:
        """Warning text if a not-yet-added task would overlap pending tasks, else None.

        Args:
            task: The candidate task (it need not be attached to a pet yet).
            pet: The pet the task is for, used to word same-pet vs different-pet warnings.

        Never raises; the caller decides whether to add the task anyway.
        """
        clashes = self.conflicts_with(task)
        if not clashes:
            return None
        return " ".join(self._warning(task, other, pet_a=pet) for other in clashes)

    def find_next_free_slot(self, after: datetime, duration_minutes: int = 30) -> datetime:
        """Find the earliest start at or after `after` where a task of this length fits.

        Walks the pending tasks in time order with a moving candidate start. A task that
        ends before the candidate is skipped; if the new task fits before the next
        pending task starts, the candidate is returned; otherwise the candidate moves to
        the end of that task.

        Args:
            after: Earliest acceptable start.
            duration_minutes: Length of the task that needs a slot.
        """
        candidate = after
        length = timedelta(minutes=duration_minutes)
        for t in self.get_pending_tasks():
            if t.end_time <= candidate:
                continue
            if candidate + length <= t.time:
                break
            candidate = t.end_time
        return candidate

    def add_task(self, pet: Pet, task: Task, allow_past: bool = False) -> Task:
        """Validate a task and add it to the pet.

        Raises:
            ValueError: If the description is empty, the duration is under 1 minute, or
                the time is in the past (unless `allow_past` is True).
        Overlaps are not an error here; use conflict_warning_for() to check for them.
        """
        if not task.description.strip():
            raise ValueError("Task description cannot be empty.")
        if task.duration_minutes < 1:
            raise ValueError("Duration must be at least 1 minute.")
        if not allow_past and task.time < datetime.now():
            raise ValueError("Task time is in the past.")
        return pet.add_task(task)

    def complete_task(self, task: Task, now: Optional[datetime] = None) -> Optional[Task]:
        """Mark a task done and return its new next occurrence if it repeats, else None.

        The recurrence logic lives in Task.mark_complete; see it for the details.
        """
        return task.mark_complete(now)

    def cancel_task(self, task: Task) -> None:
        """Remove a task from its pet's list."""
        if task.pet is not None:
            task.pet.remove_task(task)

    def cancel_series(self, task: Task) -> int:
        """Cancel a whole recurring series: remove every task sharing this task's series id.

        A one-off task (no series id) just removes itself.

        Returns:
            How many tasks were removed.
        """
        if task.pet is None:
            return 0
        if task.series_id is None:
            self.cancel_task(task)
            return 1
        pet = task.pet
        doomed = [t for t in pet.tasks if t.series_id == task.series_id]
        for t in doomed:
            pet.remove_task(t)
        return len(doomed)
