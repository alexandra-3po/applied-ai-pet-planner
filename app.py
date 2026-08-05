import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st
from pawpal.models import Owner, Pet, Task
from pawpal.scheduler import build_schedule, format_time

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A pet care planning assistant that builds a daily task schedule from your constraints.")

with st.expander("How it works", expanded=False):
    st.markdown(
        """
Enter your pet's info and today's care tasks (duration + priority). PawPal+ orders tasks by
priority, then duration, and fills your available time budget — explaining why each task was
included or skipped.
"""
    )

st.divider()

col_a, col_b, col_c = st.columns(3)
with col_a:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_b:
    pet_name = st.text_input("Pet name", value="Mochi")
with col_c:
    species = st.selectbox("Species", ["dog", "cat", "other"])

available_minutes = st.slider("Available minutes today", min_value=15, max_value=480, value=90, step=5)

st.markdown("### Tasks")
if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"title": "Morning walk", "duration_minutes": 30, "priority": "high"},
        {"title": "Feeding", "duration_minutes": 10, "priority": "high"},
        {"title": "Playtime", "duration_minutes": 20, "priority": "low"},
    ]

col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
with col1:
    task_title = st.text_input("Task title", value="Grooming", key="new_title")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20, key="new_duration")
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="new_priority")
with col4:
    st.write("")
    st.write("")
    if st.button("Add"):
        st.session_state.tasks.append(
            {"title": task_title, "duration_minutes": int(duration), "priority": priority}
        )

if st.session_state.tasks:
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

if st.button("Generate schedule", type="primary"):
    owner = Owner(name=owner_name)
    pet = Pet(name=pet_name, species=species)
    tasks = [
        Task(title=t["title"], duration_minutes=t["duration_minutes"], priority=t["priority"])
        for t in st.session_state.tasks
    ]
    schedule = build_schedule(tasks, available_minutes=available_minutes)

    st.subheader(f"Daily plan for {pet.name} ({pet.species}) — owner: {owner.name}")
    for item in schedule.included_items:
        st.write(f"**{format_time(item.start_minute)}** — {item.task.title} "
                  f"({item.task.duration_minutes} min) [{item.task.priority}] — {item.reason}")

    if schedule.skipped_items:
        st.warning("Some tasks didn't fit in today's schedule:")
        for item in schedule.skipped_items:
            st.write(f"- {item.task.title}: {item.reason}")

    st.caption(f"Total scheduled: {schedule.total_scheduled_minutes} / {available_minutes} min")
