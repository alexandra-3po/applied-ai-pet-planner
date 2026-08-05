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

## Milestone 3: RAG (Retrieval-Augmented Generation)

**Required AI feature:** the schedule explanations are augmented with retrieved pet-care guidance —
not just printed alongside the plan, but selected per-task and folded into each schedule line.

- `knowledge/` — five markdown source documents, one per care topic (multi-source retrieval, for
  the stretch requirement): `dog_exercise.md`, `cat_enrichment.md`, `medication_routines.md`,
  `grooming_basics.md`, `feeding_basics.md`. Each file has multiple `##`-delimited sections.
- `src/pawpal/retrieval.py` — `load_knowledge_base()` parses all `.md` files into chunks
  (source + heading + text). `retrieve(query, chunks, k)` scores chunks with presence-based
  TF-IDF (`idf(token) = log((1+N)/(1+df)) + 1`, heading matches double-weighted) and light
  singular/plural stemming, so a query like `"dog Feeding feeding"` doesn't get swamped by the
  word "dog" appearing in nearly every doc — the distinctive word ("feeding") dominates instead.
- `app.py` integration: for each scheduled task, a query built from `{species} {task title}
  {task category}` retrieves the single most relevant chunk and appends its citation + first
  line directly onto that task's line in the plan. A "📚 All retrieved care guidance" expander
  also shows the top-5 chunks relevant to the whole day's tasks.
- `tests/test_retrieval.py` — 5 tests: multi-source loading, dog-exercise query ranks the
  dog-exercise chunk top, cat-litter-box query ranks the litter-box chunk top, an irrelevant
  query returns no matches, and `k` is respected.

### RAG before/after example

**Before (Milestone 2, no retrieval)** — a schedule line was just the mechanical scheduling reason:

```
08:10 - Morning walk (30 min) [high] - included: high priority, fits in remaining 80 min
```

**After (Milestone 3, retrieval-augmented)** — the same line now cites grounding guidance that
actually changes what's shown to the owner:

```
08:10 - Morning walk (30 min) [high] - included: high priority, fits in remaining 80 min
  -> Guidance (dog_exercise.md -> Daily walk requirements, score=13.61): Most adult dogs need
     30-60 minutes of physical exercise per day, split across one or two walks.
```

And for a feeding task, TF-IDF weighting (not naive keyword count) correctly grounds it in
`feeding_basics.md` rather than the dog-exercise doc, even though "dog" appears in both:

```
08:00 - Feeding (10 min) [high] - included: high priority, fits in remaining 90 min
  -> Guidance (feeding_basics.md -> Portion consistency, score=2.39): Feeding at consistent
     times and portions each day helps with house-training, digestion, ...
```

**Known limitation:** the knowledge base has no dog-specific play/enrichment doc, so a dog's
"Playtime" task currently retrieves `cat_enrichment.md -> Environmental enrichment`. The guidance
text itself (rotating toys reduce boredom-driven behavior) is still broadly applicable across
species, but it isn't species-precise — documented here rather than hidden, and a natural next
addition would be a `dog_enrichment.md` source.

### Run the retrieval tests

```bash
python -m pytest tests/test_retrieval.py -v
```

```
tests/test_retrieval.py::test_knowledge_base_loads_multiple_sources PASSED [ 20%]
tests/test_retrieval.py::test_dog_exercise_query_ranks_relevant_chunk_top PASSED [ 40%]
tests/test_retrieval.py::test_cat_litter_box_query_ranks_relevant_chunk_top PASSED [ 60%]
tests/test_retrieval.py::test_irrelevant_query_returns_no_matches PASSED [ 80%]
tests/test_retrieval.py::test_retrieve_respects_k_limit PASSED           [100%]
```
