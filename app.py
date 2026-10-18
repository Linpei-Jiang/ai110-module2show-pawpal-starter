from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def task_rows(tasks, flagged=frozenset()):
    """Table rows for st.table; `flagged` holds ids of tasks that are part of a conflict."""
    return [
        {
            "": "⚠️" if id(t) in flagged else "",
            "When": f"{t.time:%a %I:%M %p} - {t.end_time:%I:%M %p}",
            "Pet": t.pet.name,
            "Task": t.description,
            "Repeats": t.frequency.value,
            "Status": "✅ done" if t.completed else "⏳ pending",
        }
        for t in tasks
    ]


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption(
    "Plan walks, meals, and medication for all your pets in one place. "
    "Tasks are sorted by time, overlaps are flagged, and repeating tasks reschedule themselves."
)

# Keep one Owner alive across Streamlit reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
owner = st.session_state.owner
scheduler = Scheduler(owner)

# A message queued by an action (complete, cancel, ...) just before st.rerun().
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

# --- Owner and pets ------------------------------------------------------------------

st.subheader("1. Owner and pets")
owner_name = st.text_input("Owner name", value=owner.name)
if owner_name != owner.name:
    owner.edit_owner(owner_name, owner.email, owner.phone)

col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    if not pet_name.strip():
        st.error("Please enter a pet name.")
    elif any(p.name.lower() == pet_name.strip().lower() for p in owner.pets):
        st.warning(f"{pet_name.strip()} is already on your list.")
    else:
        owner.add_pet(Pet(pet_name.strip(), species))
        st.success(f"Added {pet_name.strip()}.")

if owner.pets:
    st.write("Your pets: " + ", ".join(f"**{p.name}** ({p.species})" for p in owner.pets))
else:
    st.info("No pets yet. Add one above to start scheduling.")

# --- Schedule a task -----------------------------------------------------------------

st.subheader("2. Schedule a task")

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
        chosen_days = st.multiselect("Only on these days (optional)", WEEKDAYS)
        weekdays = [WEEKDAYS.index(d) for d in chosen_days]

    if st.button("Add task"):
        pet = next(p for p in owner.pets if p.name == task_pet)
        task = Task(
            task_title,
            datetime.combine(task_date, task_time),
            Frequency(task_freq),
            duration_minutes=int(task_duration),
            weekdays=weekdays,
        )
        warning = scheduler.conflict_warning_for(task, pet)  # checked before adding
        try:
            scheduler.add_task(pet, task)
        except ValueError as err:
            st.error(f"Could not add the task: {err}")
        else:
            st.success(f"Scheduled '{task.description}' for {pet.name}, {task.time:%a %I:%M %p}.")
            if warning:
                free = scheduler.find_next_free_slot(task.time, task.duration_minutes)
                st.warning(
                    f"{warning}\n\nThe task was still added. If you'd rather avoid the overlap, "
                    f"the next free {task.duration_minutes}-minute slot is **{free:%a %I:%M %p}**."
                )
else:
    st.info("Add a pet before scheduling tasks.")

# --- Today's schedule ----------------------------------------------------------------

st.subheader("3. Today's schedule")

today = date.today()
todays = scheduler.get_tasks_for_day(today)  # sorted by time
conflicts = scheduler.find_conflicts()
conflict_messages = scheduler.get_conflict_warnings()
todays_conflicts = [
    (pair, msg) for pair, msg in zip(conflicts, conflict_messages) if pair[0].time.date() == today
]
flagged = {id(t) for (a, b), _ in todays_conflicts for t in (a, b)}
overdue = scheduler.get_overdue_tasks()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tasks today", len(todays))
m2.metric("Still to do", sum(1 for t in todays if not t.completed))
m3.metric("Overdue", len(overdue))
m4.metric("Conflicts", len(todays_conflicts))

if todays_conflicts:
    lines = []
    for (a, b), msg in todays_conflicts:
        free = scheduler.find_next_free_slot(b.time, b.duration_minutes)
        lines.append(f"- {msg.removeprefix('Warning: ')} Next free slot: **{free:%I:%M %p}**.")
    st.warning(
        "**Heads up: some tasks overlap.** Move one of each pair, or do them one after the other.\n\n"
        + "\n".join(lines)
    )
elif todays:
    st.success("No scheduling conflicts today.")

if len(conflicts) > len(todays_conflicts):
    st.caption(f"{len(conflicts) - len(todays_conflicts)} more conflict(s) on other days.")

if todays:
    st.table(task_rows(todays, flagged))
    st.caption("⚠️ marks a task that overlaps another pending task.")
else:
    st.info("Nothing scheduled for today.")

# --- All tasks -------------------------------------------------------------------------

st.subheader("4. Manage tasks")

col1, col2 = st.columns(2)
with col1:
    pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
with col2:
    status_filter = st.radio("Show", ["Pending", "Completed", "All"], horizontal=True)

visible = scheduler.filter_tasks(
    pet_name=None if pet_filter == "All pets" else pet_filter,
    completed={"Pending": False, "Completed": True, "All": None}[status_filter],
)

for t in overdue:
    if pet_filter in ("All pets", t.pet.name):
        st.error(f"Overdue: {t.pet.name} - {t.description} was due {t.time:%a %I:%M %p}.")

if visible:
    all_flagged = {id(t) for pair in conflicts for t in pair}
    st.table(task_rows(visible, all_flagged))

    labels = {
        f"{t.pet.name} - {t.description} ({t.time:%a %I:%M %p})": t for t in visible if not t.completed
    }
    if labels:
        picked = labels[st.selectbox("Pick a task", list(labels))]
        col1, col2, col3 = st.columns(3)
        if col1.button("Mark complete"):
            following = scheduler.complete_task(picked)
            st.session_state.flash = (
                f"Done. The next one is scheduled for {following.time:%a %I:%M %p}."
                if following
                else "Done."
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
    st.info("No tasks match.")
