# Applied AI Pet Planner

> This README grows with each milestone. See `planning.md` for a full log of what's been built and how it was verified. AI feature sections (RAG, agentic planning, specialization, reliability, evaluation) are filled in as those milestones land.

## Base project

This system extends **PawPal+** (AI110 Module 2), described in the starter scenario as: a Streamlit
app that helps a pet owner plan daily pet-care tasks (walks, feeding, meds, grooming, etc.) under
time and priority constraints, producing a schedule with an explanation for each choice.

The linked Module 2 starter repo (`ai110-module2show-pawpal-starter`) was an unimplemented
skeleton — a thin Streamlit stub and a placeholder UML diagram with no scheduling logic or tests.
Milestone 2 of this project implemented that scenario for real (see below), and that implementation
is the "original project" being extended into the full Applied AI System in later milestones.

## What's implemented so far (Milestone 2: base scheduler)

- `src/pawpal/models.py` — `Owner`, `Pet`, `Task`, `ScheduledItem`, `Schedule` data models.
- `src/pawpal/scheduler.py` — `build_schedule(tasks, available_minutes)`: orders tasks by priority
  (high → medium → low) then by duration (shorter first), greedily fills the time budget, and
  records a plain-language reason for every included or skipped task.
- `app.py` — Streamlit UI: enter owner/pet info, add tasks, set available minutes, click
  "Generate schedule" to see the ordered plan and skip reasons.
- `tests/test_scheduler.py` — 8 pytest cases covering priority ordering, duration tie-breaks,
  time-budget overflow/skipping, empty input, and invalid input (negative duration, bad priority,
  negative budget).
- `diagrams/uml.mmd` — class diagram matching the actual implementation.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the tests

```bash
python -m pytest -v
```

Sample test output:

```
tests/test_scheduler.py::test_priority_ordering PASSED                   [ 12%]
tests/test_scheduler.py::test_tie_break_by_duration PASSED               [ 25%]
tests/test_scheduler.py::test_time_budget_overflow_skips_task PASSED     [ 37%]
tests/test_scheduler.py::test_empty_task_list PASSED                     [ 50%]
tests/test_scheduler.py::test_invalid_task_duration_raises PASSED        [ 62%]
tests/test_scheduler.py::test_invalid_priority_raises PASSED             [ 75%]
tests/test_scheduler.py::test_negative_budget_raises PASSED              [ 87%]
tests/test_scheduler.py::test_format_time PASSED                         [100%]
============================== 8 passed in 0.04s ==============================
```

### Sample interaction (scheduling logic)

Input: owner "Jordan", pet "Mochi" (dog), 90 available minutes, tasks:
Morning walk (30 min, high), Feeding (10 min, high), Playtime (20 min, low), Grooming (60 min, medium).

Output:
```
Daily plan for Mochi (dog) - owner: Jordan
08:00 - Feeding (10 min) [high] - included: high priority, fits in remaining 90 min
08:10 - Morning walk (30 min) [high] - included: high priority, fits in remaining 80 min
08:40 - Playtime (20 min) [low] - included: low priority, fits in remaining 50 min
Skipped:
  - Grooming: skipped: needs 60 min but only 50 min remain
Total scheduled: 60 / 90 min
```

Note: scheduling is priority-first, not globally time-optimal — a low-priority task that fits can
be scheduled ahead of a medium-priority task that doesn't, because tasks are committed in priority
order without look-ahead. This is documented, intended behavior (matches the "priority-first" spec)
rather than a bug.
