import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st
from pawpal.models import Owner, Pet, Task
from pawpal.scheduler import format_time
from pawpal.retrieval import load_knowledge_base, retrieve
from pawpal.agent import PlannerAgent, format_trace_markdown
from pawpal.persona import baseline_vs_specialized
from pawpal.logging_utils import get_logger

KNOWLEDGE_BASE = load_knowledge_base()
AGENT = PlannerAgent(knowledge_base=KNOWLEDGE_BASE)
logger = get_logger("pawpal.app")

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

TASK_CATEGORIES = ["exercise", "feeding", "grooming", "medication", "enrichment", "general"]

st.markdown("### Tasks")
if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {"title": "Morning walk", "duration_minutes": 30, "priority": "high", "category": "exercise"},
        {"title": "Feeding", "duration_minutes": 10, "priority": "high", "category": "feeding"},
        {"title": "Playtime", "duration_minutes": 20, "priority": "low", "category": "enrichment"},
    ]

col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
with col1:
    task_title = st.text_input("Task title", value="Grooming", key="new_title")
with col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20, key="new_duration")
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="new_priority")
with col4:
    category = st.selectbox("Category", TASK_CATEGORIES, index=2, key="new_category")
with col5:
    st.write("")
    st.write("")
    if st.button("Add"):
        try:
            Task(title=task_title, duration_minutes=int(duration), priority=priority, category=category)
        except ValueError as exc:
            logger.warning("Rejected invalid task input: %s", exc)
            st.error(f"Couldn't add task: {exc}")
        else:
            st.session_state.tasks.append(
                {"title": task_title, "duration_minutes": int(duration), "priority": priority, "category": category}
            )

if st.session_state.tasks:
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

if st.button("Generate schedule", type="primary"):
    try:
        owner = Owner(name=owner_name)
        pet = Pet(name=pet_name, species=species)
        tasks = [
            Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=t["priority"],
                category=t.get("category", "general"),
            )
            for t in st.session_state.tasks
        ]
    except ValueError as exc:
        logger.warning("Rejected invalid input: %s", exc)
        st.error(f"Couldn't build a schedule: {exc}")
        st.stop()

    run = AGENT.run(pet, tasks, available_minutes=available_minutes)
    schedule = run.schedule

    st.subheader(f"Daily plan for {pet.name} ({pet.species}) — owner: {owner.name}")
    if any(e.step == "revise" for e in run.trace):
        st.info(f"The planning agent revised this schedule {run.iterations - 1} time(s) after self-critique.")

    for item in schedule.included_items:
        guidance_query = f"{pet.species} {item.task.title} {item.task.category}"
        matches = retrieve(guidance_query, KNOWLEDGE_BASE, k=1)
        line = (f"**{format_time(item.start_minute)}** — {item.task.title} "
                f"({item.task.duration_minutes} min) [{item.task.priority}] — {item.reason}")
        if matches:
            chunk, _score = matches[0]
            line += f"  \n  -> *Care guidance ({chunk.citation}): {chunk.snippet}*"
        st.write(line)

    if schedule.skipped_items:
        st.warning("Some tasks didn't fit in today's schedule:")
        for item in schedule.skipped_items:
            st.write(f"- {item.task.title}: {item.reason}")

    st.caption(f"Total scheduled: {schedule.total_scheduled_minutes} / {available_minutes} min")

    st.divider()
    tone = st.radio("Narration style", ["Plain", "Coach Paws"], horizontal=True, key="tone_choice")
    comparison = baseline_vs_specialized(pet, schedule, run.guidance)
    if tone == "Plain":
        st.code(comparison["baseline"])
    else:
        st.markdown(comparison["specialized"])
        st.caption(f"Specialized narration source: {comparison['specialized_source']}")

    with st.expander("📚 All retrieved care guidance for this pet/tasks"):
        overall_query = f"{pet.species} " + " ".join(t.title for t in tasks)
        overall_matches = retrieve(overall_query, KNOWLEDGE_BASE, k=5)
        if overall_matches:
            for chunk, score in overall_matches:
                st.markdown(f"**{chunk.citation}** (relevance score: {score})\n\n{chunk.text}")
        else:
            st.write("No matching guidance found for these tasks.")

    with st.expander("🤖 Agent reasoning trace (plan → act → critique → revise)"):
        st.markdown(format_trace_markdown(run, run_label="Live Agent Run"))
