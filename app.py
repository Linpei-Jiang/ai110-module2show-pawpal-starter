from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def task_rows(tasks):
    """Table rows for st.table."""
    return [
        {
            "when": t.time.strftime("%a %I:%M %p"),
            "pet": t.pet.name,
            "task": t.description,
            "minutes": t.duration_minutes,
            "repeats": t.frequency.value,
            "done": t.completed,
        }
        for t in tasks
    ]


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# Keep one Owner alive across Streamlit reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
owner = st.session_state.owner

st.subheader("Owner")
owner_name = st.text_input("Owner name", value=owner.name)
if owner_name != owner.name:
    owner.edit_owner(owner_name, owner.email, owner.phone)

st.subheader("Add a Pet")
col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    if not pet_name.strip():
        st.error("Please enter a pet name.")
    elif any(p.name == pet_name.strip() for p in owner.pets):
        st.warning(f"{pet_name} is already on your list.")
    else:
        owner.add_pet(Pet(pet_name.strip(), species))
        st.success(f"Added {pet_name}.")

if owner.pets:
    st.write("Your pets: " + ", ".join(f"{p.name} ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

scheduler = Scheduler(owner)

st.markdown("### Schedule a Task")

if owner.pets:
    col1, col2, col3 = st.columns(3)
    with col1:
        task_pet = st.selectbox("Pet", [p.name for p in owner.pets])
        task_title = st.text_input("Task", value="Morning walk")
    with col2:
        task_date = st.date_input("Date", value=date.today())
        task_time = st.time_input("Time", value=time(8, 0))
    with col3:
        task_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=30)
        task_freq = st.selectbox("Repeats", [f.value for f in Frequency])

    weekdays: list[int] = []
    if task_freq == Frequency.WEEKLY.value:
        chosen = st.multiselect("On these days (optional)", WEEKDAYS)
        weekdays = [WEEKDAYS.index(d) for d in chosen]

    if st.button("Add task"):
        pet = next(p for p in owner.pets if p.name == task_pet)
        task = Task(
            task_title,
            datetime.combine(task_date, task_time),
            Frequency(task_freq),
            duration_minutes=int(task_duration),
            weekdays=weekdays,
        )
        clashes = scheduler.conflicts_with(task)
        try:
            scheduler.add_task(pet, task)
        except ValueError as err:
            st.error(str(err))
        else:
            st.success(f"Scheduled '{task_title}' for {pet.name} at {task.time:%a %I:%M %p}.")
            if clashes:
                free = scheduler.find_next_free_slot(task.time, task.duration_minutes)
                st.warning(
                    "That overlaps: "
                    + ", ".join(f"{c.pet.name} - {c.description} ({c.time:%I:%M %p})" for c in clashes)
                    + f". Next free slot: {free:%a %I:%M %p}."
                )
else:
    st.info("Add a pet before scheduling tasks.")

st.markdown("### Your Tasks")
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))
col1, col2 = st.columns(2)
with col1:
    pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
with col2:
    show_done = st.checkbox("Show completed", value=False)

chosen_pet = next((p for p in owner.pets if p.name == pet_filter), None)
visible = scheduler.filter_tasks(pet=chosen_pet, completed=None if show_done else False)

for t in scheduler.get_overdue_tasks():
    if chosen_pet is None or t.pet is chosen_pet:
        st.error(f"Overdue: {t.pet.name} - {t.description} was due {t.time:%a %I:%M %p}")

if visible:
    st.table(task_rows(visible))

    labels = {f"{t.pet.name} - {t.description} ({t.time:%a %I:%M %p})": t for t in visible if not t.completed}
    if labels:
        picked = labels[st.selectbox("Pick a task", list(labels))]
        col1, col2, col3 = st.columns(3)
        if col1.button("Mark complete"):
            following = scheduler.complete_task(picked)
            st.session_state.flash = (
                f"Done. Next one scheduled for {following.time:%a %I:%M %p}." if following else "Done."
            )
            st.rerun()
        if col2.button("Cancel task"):
            scheduler.cancel_task(picked)
            st.session_state.flash = "Task removed."
            st.rerun()
        if col3.button("Cancel all repeats"):
            st.session_state.flash = f"Removed {scheduler.cancel_series(picked)} task(s)."
            st.rerun()
else:
    st.info("No tasks to show.")

st.divider()

st.subheader("Build Schedule")

if st.button("Generate schedule"):
    todays = scheduler.get_tasks_for_day()
    if not todays:
        st.info("Nothing scheduled today.")
    else:
        st.write(f"Today's Schedule for {owner.name}")
        st.table(task_rows(todays))
    for a, b in scheduler.find_conflicts():
        st.warning(
            f"Conflict: {a.pet.name} - {a.description} ({a.time:%a %I:%M %p}-{a.end_time:%I:%M %p}) "
            f"overlaps {b.pet.name} - {b.description} ({b.time:%I:%M %p}-{b.end_time:%I:%M %p})"
        )
