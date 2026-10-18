from datetime import datetime, time

from pawpal_system import Frequency, Owner, Pet, Scheduler, Task


def at_today(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(datetime.today().date(), time(hour, minute))


def print_todays_schedule(owner: Owner, scheduler: Scheduler) -> None:
    today = datetime.today().date()
    print(f"Today's Schedule for {owner.name} ({today:%A, %B %d, %Y})")
    print("-" * 64)
    tasks = scheduler.get_tasks_for_day(today)
    if not tasks:
        print("Nothing scheduled today.")
        return
    for t in tasks:
        mark = "x" if t.completed else " "
        print(
            f"[{mark}] {t.time:%I:%M %p}-{t.end_time:%I:%M %p}  {t.pet.name:<6} "
            f"{t.description} ({t.frequency.value})"
        )
    for warning in scheduler.get_conflict_warnings():
        print(warning)


def show(title: str, tasks) -> None:
    print(f"\n{title}")
    if not tasks:
        print("  (none)")
    for t in tasks:
        mark = "x" if t.completed else " "
        print(f"  [{mark}] {t.time:%I:%M %p}  {t.pet.name:<6} {t.description}")


def main() -> None:
    owner = Owner("Alex Rivera", "alex@example.com", "555-0100")
    rex = owner.add_pet(Pet("Rex", "dog", "Labrador", 4))
    luna = owner.add_pet(Pet("Luna", "cat", "Siamese", 2))
    scheduler = Scheduler(owner)

    # allow_past keeps the demo working whatever time of day it is run.
    def add(pet, desc, when, freq=Frequency.ONCE, minutes=30):
        task = Task(desc, when, freq, duration_minutes=minutes)
        warning = scheduler.conflict_warning_for(task, pet)  # lightweight check: a message, never an exception
        scheduler.add_task(pet, task, allow_past=True)
        if warning:
            print(warning)
        return task

    # Added deliberately out of order.
    add(rex, "Evening walk", at_today(18, 0), minutes=45)
    add(luna, "Flea medication", at_today(12, 15), minutes=5)
    breakfast = add(luna, "Breakfast", at_today(7, 40), minutes=10)
    add(rex, "Morning walk", at_today(7, 30))
    add(luna, "Play time", at_today(16, 0), minutes=20)
    add(rex, "Vet check", at_today(9, 0), minutes=60)

    print("\nAdding two tasks that clash with existing ones:")
    add(luna, "Grooming", at_today(9, 0), minutes=30)  # same time as Rex's vet check (different pets)
    add(luna, "Brush fur", at_today(12, 15), minutes=10)  # same time as Luna's flea medication (same pet)

    scheduler.complete_task(breakfast)  # mark one task done so status filters have something to show

    show("Insertion order (unsorted, straight from the owner):", owner.get_all_tasks())
    show("Sorted by time:", scheduler.sort_by_time())
    show("Filter: pet name 'rex':", scheduler.filter_tasks(pet_name="rex"))
    show("Filter: pet name 'Luna':", scheduler.filter_tasks(pet_name="Luna"))
    show("Filter: pending only:", scheduler.filter_tasks(completed=False))
    show("Filter: completed only:", scheduler.filter_tasks(completed=True))
    show("Filter: Luna + pending:", scheduler.filter_tasks(pet_name="Luna", completed=False))

    print()
    print_todays_schedule(owner, scheduler)


if __name__ == "__main__":
    main()
