from datetime import date, datetime, timedelta

import pytest

from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

DAY = datetime(2030, 1, 7, 0, 0)  # a Monday, safely in the future


def at(hour: int, minute: int = 0) -> datetime:
    return DAY.replace(hour=hour, minute=minute)


@pytest.fixture
def setup():
    owner = Owner("Alex")
    rex = owner.add_pet(Pet("Rex", "dog"))
    luna = owner.add_pet(Pet("Luna", "cat"))
    return owner, rex, luna, Scheduler(owner)


def test_mark_complete_changes_status():
    task = Task("Morning walk", at(8))
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Rex", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Breakfast", at(7, 30)))

    assert len(pet.tasks) == 1


# --- sorting ---------------------------------------------------------------

def test_sort_by_time_across_pets_with_stable_ties(setup):
    owner, rex, luna, s = setup
    rex.add_task(Task("Evening walk", at(18)))
    rex.add_task(Task("Walk", at(8)))
    luna.add_task(Task("Breakfast", at(8)))

    ordered = [(t.pet.name, t.description) for t in s.sort_by_time()]

    assert ordered == [("Luna", "Breakfast"), ("Rex", "Walk"), ("Rex", "Evening walk")]


# --- filtering ---------------------------------------------------------------

def test_filter_combines_pet_status_and_day(setup):
    owner, rex, luna, s = setup
    done = rex.add_task(Task("Walk", at(8)))
    rex.add_task(Task("Dinner", at(18)))
    rex.add_task(Task("Tomorrow", at(8) + timedelta(days=1)))
    luna.add_task(Task("Breakfast", at(8)))
    done.mark_complete()

    result = s.filter_tasks(pet=rex, completed=False, day=DAY.date())

    assert [t.description for t in result] == ["Dinner"]
    assert len(s.filter_tasks()) == 4


def test_get_tasks_for_day_can_hide_completed(setup):
    owner, rex, luna, s = setup
    t = rex.add_task(Task("Walk", at(8)))
    rex.add_task(Task("Dinner", at(18)))
    t.mark_complete()

    assert len(s.get_tasks_for_day(DAY.date())) == 2
    assert len(s.get_tasks_for_day(DAY.date(), include_completed=False)) == 1


# --- conflicts -----------------------------------------------------------------

def test_overlapping_tasks_conflict_even_at_different_start_times(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), duration_minutes=30))
    meal = luna.add_task(Task("Breakfast", at(8, 15), duration_minutes=10))

    assert s.find_conflicts() == [(walk, meal)]


def test_back_to_back_tasks_do_not_conflict(setup):
    owner, rex, luna, s = setup
    rex.add_task(Task("Walk", at(8), duration_minutes=30))
    luna.add_task(Task("Breakfast", at(8, 30), duration_minutes=10))

    assert s.find_conflicts() == []


def test_completed_tasks_are_ignored_by_conflicts(setup):
    owner, rex, luna, s = setup
    a = rex.add_task(Task("Walk", at(8)))
    luna.add_task(Task("Breakfast", at(8)))
    a.mark_complete()

    assert s.find_conflicts() == []


def test_conflicts_with_checks_a_candidate_before_adding(setup):
    owner, rex, luna, s = setup
    existing = rex.add_task(Task("Walk", at(8), duration_minutes=30))

    assert s.conflicts_with(Task("Vet", at(8, 20))) == [existing]
    assert s.conflicts_with(Task("Vet", at(9))) == []


def test_find_next_free_slot_skips_busy_blocks(setup):
    owner, rex, luna, s = setup
    rex.add_task(Task("Walk", at(8), duration_minutes=30))
    luna.add_task(Task("Meds", at(8, 30), duration_minutes=15))

    assert s.find_next_free_slot(at(8), 20) == at(8, 45)
    assert s.find_next_free_slot(at(7), 30) == at(7)  # fits before the walk
    assert s.find_next_free_slot(at(7, 45), 30) == at(8, 45)  # does not fit before the walk


# --- recurring tasks -----------------------------------------------------------------

def test_completing_daily_task_adds_next_day(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), Frequency.DAILY, duration_minutes=20))

    nxt = s.complete_task(walk, now=at(8, 5))

    assert walk.completed
    assert nxt.time == at(8) + timedelta(days=1)
    assert nxt.duration_minutes == 20
    assert nxt.series_id == walk.series_id
    assert nxt in rex.tasks


def test_completing_twice_does_not_duplicate_next_occurrence(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), Frequency.DAILY))

    s.complete_task(walk, now=at(8))
    assert s.complete_task(walk, now=at(8)) is None

    assert len(rex.tasks) == 2


def test_late_completion_skips_past_occurrences(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), Frequency.DAILY))

    nxt = s.complete_task(walk, now=at(8) + timedelta(days=2, hours=1))

    assert nxt.time == at(8) + timedelta(days=3)


def test_weekly_with_chosen_weekdays_jumps_to_next_chosen_day(setup):
    owner, rex, luna, s = setup
    task = rex.add_task(Task("Bath", at(9), Frequency.WEEKLY, weekdays=[0, 2, 4]))  # Mon/Wed/Fri

    nxt = s.complete_task(task, now=at(9))

    assert nxt.time == at(9) + timedelta(days=2)  # Wednesday


def test_one_off_task_has_no_next_occurrence(setup):
    owner, rex, luna, s = setup
    task = rex.add_task(Task("Vet", at(10)))

    assert s.complete_task(task, now=at(10)) is None
    assert len(rex.tasks) == 1


def test_cancel_series_removes_all_occurrences(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), Frequency.DAILY))
    s.complete_task(walk, now=at(8))
    rex.add_task(Task("Vet", at(10)))

    removed = s.cancel_series(walk)

    assert removed == 2
    assert [t.description for t in rex.tasks] == ["Vet"]


# --- overdue and validation ----------------------------------------------------------------

def test_overdue_lists_only_pending_past_tasks(setup):
    owner, rex, luna, s = setup
    old = rex.add_task(Task("Walk", at(8)))
    rex.add_task(Task("Dinner", at(18)))
    done = luna.add_task(Task("Meds", at(7)))
    done.mark_complete()

    assert s.get_overdue_tasks(now=at(12)) == [old]


def test_add_task_validation(setup):
    owner, rex, luna, s = setup

    with pytest.raises(ValueError):
        s.add_task(rex, Task("  ", at(8)))
    with pytest.raises(ValueError):
        s.add_task(rex, Task("Walk", at(8), duration_minutes=0))
    with pytest.raises(ValueError):
        s.add_task(rex, Task("Walk", datetime(2000, 1, 1)))

    assert rex.tasks == []
    s.add_task(rex, Task("Walk", datetime(2000, 1, 1)), allow_past=True)
    assert len(rex.tasks) == 1


def test_filter_by_pet_name_is_case_insensitive_and_combines_with_status(setup):
    owner, rex, luna, s = setup
    done = rex.add_task(Task("Walk", at(8)))
    rex.add_task(Task("Dinner", at(18)))
    luna.add_task(Task("Breakfast", at(8)))
    done.mark_complete()

    assert [t.description for t in s.filter_tasks(pet_name="rex")] == ["Walk", "Dinner"]
    assert [t.description for t in s.filter_tasks(pet_name="REX", completed=False)] == ["Dinner"]
    assert s.filter_tasks(pet_name="Nobody") == []


def test_task_mark_complete_alone_creates_next_occurrence(setup):
    owner, rex, luna, s = setup
    walk = rex.add_task(Task("Walk", at(8), Frequency.DAILY))
    bath = luna.add_task(Task("Bath", at(9), Frequency.WEEKLY))

    next_walk = walk.mark_complete(now=at(8))
    next_bath = bath.mark_complete(now=at(9))

    assert next_walk.time == at(8) + timedelta(days=1)
    assert next_bath.time == at(9) + timedelta(weeks=1)
    assert next_walk in rex.tasks and next_bath in luna.tasks
    assert next_walk.pet is rex and not next_walk.completed
    assert walk.mark_complete(now=at(8)) is None  # no duplicate on a second call
    assert len(rex.tasks) == 2


def test_warning_messages_for_same_pet_and_different_pets(setup):
    owner, rex, luna, s = setup
    rex.add_task(Task("Vet check", at(9), duration_minutes=60))
    luna.add_task(Task("Grooming", at(9)))  # different pets, same time
    luna.add_task(Task("Brush fur", at(9)))  # same pet as Grooming, same time

    warnings = s.get_conflict_warnings()

    assert len(warnings) == 3
    assert any("Luna has two tasks at the same time" in w for w in warnings)
    assert any("Rex's 'Vet check'" in w and "Luna's 'Grooming'" in w for w in warnings)


def test_no_warnings_when_clear_and_candidate_check_never_raises(setup):
    owner, rex, luna, s = setup
    rex.add_task(Task("Walk", at(8)))

    assert s.get_conflict_warnings() == []
    assert s.conflict_warning_for(Task("Dinner", at(18))) is None
    vet = Task("Vet", at(8))  # not attached to a pet yet, same time as Rex's walk
    assert "Luna's 'Vet'" in s.conflict_warning_for(vet, luna)
    assert "Rex has two tasks at the same time" in s.conflict_warning_for(vet, rex)
