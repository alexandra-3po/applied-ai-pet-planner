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

## Milestone 4: Agentic Planning Loop

**Required AI feature:** a real plan → act → critique → revise loop, not a one-shot call.
`src/pawpal/agent.py`'s `PlannerAgent.run()`:

1. **Plan** — retrieves care guidance (Milestone 3's `retrieve()`) for every task.
2. **Act** — calls `build_schedule()` (a tool call) to produce a candidate schedule.
3. **Critique** — checks the candidate against the retrieved guidance and flags problems
   (e.g., a dog getting under 30 minutes of exercise, per `knowledge/dog_exercise.md`).
4. **Revise** — if the critique flags an issue, raises the affected task's priority and rebuilds
   the schedule; repeats up to `max_iterations` (default 2).
5. **Explain** — produces the final natural-language plan once the loop settles.

### Real Claude call with automatic fallback

The critique step calls the **Anthropic API** (`claude-haiku-4-5-20251001`) when
`ANTHROPIC_API_KEY` is set in the environment, sending the candidate schedule and retrieved
guidance and asking for a structured JSON verdict. If no key is set, or the API call fails for
any reason, it falls back to a deterministic rule-based critique automatically — the system is
always runnable and gradeable without an API key, while the real LLM code path exists and is
exercised by `tests/test_agent.py::test_claude_critique_path_with_fake_client` (a mocked client,
no network/key needed).

```bash
export ANTHROPIC_API_KEY=sk-...   # optional — omit to use the rule-based critique
streamlit run app.py
```

### Reasoning traces are saved, not just printed

Every run's plan/act/critique/revise steps are recorded as structured `TraceEntry` objects and
rendered via `format_trace_markdown()`. The Streamlit app shows them in an "🤖 Agent reasoning
trace" expander, and a concrete real run is committed to `ai_interactions.md` (not templated
placeholder text) — see that file for the full example below.

### Sample interaction: under-exercised dog gets revised

Input: dog "Rex", 60 available minutes, tasks: Grooming (40 min, high, grooming), Feeding
(20 min, high, feeding), Morning walk (30 min, **low**, exercise).

```
1. plan -- Gathering care guidance for dog across 3 task(s)
2. plan -- Retrieved 3 guidance snippet(s): grooming_basics.md -> Bathing; feeding_basics.md -> Portion consistency; dog_exercise.md -> Daily walk requirements
3. act -- Built candidate schedule: 2 included, 1 skipped
4. critique -- [rules (no ANTHROPIC_API_KEY set)] ok=False issues=['Only 0 min of exercise scheduled; guidelines recommend 30-60 min/day for dogs.']
5. revise -- Applied priority overrides: {'Morning walk': 'high'}
6. act -- Rebuilt schedule after revision: 2 included, 1 skipped
7. critique -- [rules (no ANTHROPIC_API_KEY set)] ok=True issues=[]

Final explanation:
Daily plan for Rex (dog):
08:00 - Feeding (20 min) [high] - included: high priority, fits in remaining 60 min
08:20 - Morning walk (30 min) [high] - included: high priority, fits in remaining 40 min
Skipped:
  - Grooming: skipped: needs 40 min but only 10 min remain
```

The walk started out low priority and would have been skipped entirely; the agent's critique
step caught the exercise shortfall against the retrieved guideline and revised the plan to
include it, at the cost of the lower-value grooming task. This is a meaningful behavior change,
not cosmetic — the initial and final schedules differ.

### Run the agent tests

```bash
python -m pytest tests/test_agent.py -v
```

```
tests/test_agent.py::test_agent_loop_terminates_and_produces_schedule PASSED [ 20%]
tests/test_agent.py::test_under_exercised_dog_triggers_revision_and_fixes_it PASSED [ 40%]
tests/test_agent.py::test_well_covered_schedule_needs_no_revision PASSED [ 60%]
tests/test_agent.py::test_format_trace_markdown_structure PASSED         [ 80%]
tests/test_agent.py::test_claude_critique_path_with_fake_client PASSED   [100%]
```

## Milestone 5: Specialization — "Coach Paws" persona

**Stretch feature:** `src/pawpal/persona.py` narrates the same schedule in a fixed, constrained
tone ("Coach Paws") via few-shot prompting, alongside the plain baseline explanation, so the
difference is directly comparable.

- `PERSONA_SYSTEM_PROMPT` + two hand-written few-shot examples define a fixed 4-part structure:
  greeting → today's plan → skip note (if any) → one motivational line tied to a retrieved
  guideline. Under 80 words, always this shape.
- `explain_with_persona()` calls Claude (`claude-haiku-4-5-20251001`) with the few-shot messages
  when `ANTHROPIC_API_KEY` is set; otherwise a deterministic template produces the same fixed
  structure without a model call — same fallback pattern as Milestone 4.
- The Streamlit app has a "Plain" / "Coach Paws" toggle so both renderings of the exact same
  schedule are visible side by side in the running app, not just in docs.
- Full baseline-vs-specialized comparison, with measurable differences and a bug this comparison
  caught, is in `model_card.md`.

### Run the persona tests

```bash
python -m pytest tests/test_persona.py -v
```

```
tests/test_persona.py::test_specialized_output_differs_from_baseline PASSED [ 33%]
tests/test_persona.py::test_specialized_output_has_constrained_structure PASSED [ 66%]
tests/test_persona.py::test_persona_claude_path_with_fake_client PASSED  [100%]
```

## Milestone 6: Reliability — Input Validation, Output Guardrail, Logging

**Required rubric item:** a functional reliability mechanism, demonstrated with markdown examples
(input, behavior, result).

- **Input validation** (`src/pawpal/models.py`): `Owner`/`Pet` reject empty names; `Task` rejects
  an empty title, non-positive or over-240-minute duration, and invalid priority — all at
  construction time, so bad data can't reach the scheduler/retriever/agent. `app.py` catches this
  at the UI boundary (both "Add task" and "Generate schedule") and shows a clear error instead of
  crashing.
- **Output guardrail** (`src/pawpal/guardrails.py`): `check_schedule_invariants()` independently
  re-checks that a schedule never exceeds its time budget and has no overlapping tasks;
  `safe_schedule_or_fallback()` swaps in an empty, safe schedule if either check fails, rather than
  showing the user something wrong. Tested against hand-built adversarial `Schedule` objects that
  bypass the scheduler entirely, so it's a genuine independent safety net.
- **Logging** (`src/pawpal/logging_utils.py`): every agent run and guardrail decision is logged to
  `logs/pawpal.log` (gitignored) under the shared `pawpal` logger namespace.
- Full input/behavior/result table and a real captured log excerpt are in `model_card.md`.

### Run the reliability tests

```bash
python -m pytest tests/test_reliability.py -v
```

```
tests/test_reliability.py::test_empty_task_title_rejected PASSED         [ 10%]
tests/test_reliability.py::test_duration_over_max_rejected PASSED        [ 20%]
tests/test_reliability.py::test_empty_owner_name_rejected PASSED         [ 30%]
tests/test_reliability.py::test_empty_pet_name_rejected PASSED           [ 40%]
tests/test_reliability.py::test_guardrail_catches_over_budget_schedule PASSED [ 50%]
tests/test_reliability.py::test_guardrail_catches_overlapping_tasks PASSED [ 60%]
tests/test_reliability.py::test_guardrail_passes_valid_schedule PASSED   [ 70%]
tests/test_reliability.py::test_safe_schedule_or_fallback_rejects_unsafe_schedule PASSED [ 80%]
tests/test_reliability.py::test_safe_schedule_or_fallback_passes_through_valid_schedule PASSED [ 90%]
tests/test_reliability.py::test_agent_run_emits_log_records PASSED       [100%]
```

## Milestone 7: Evaluation Harness

**Stretch feature:** `scripts/evaluate.py` is a standalone script (not part of the pytest suite)
that runs the real system — scheduler, RAG retrieval, agentic loop, guardrails, validation — against
6 predefined scenarios and prints a pass/fail summary, matching the spec's example format ("5 out
of 6 tests passed..."). Exits with code 1 if anything fails, so it can gate CI.

```bash
python scripts/evaluate.py
```

Real output:

```
Applied AI Pet Planner -- Evaluation Harness
============================================================
[PASS] Well-covered dog schedule needs no revision
       45 exercise min scheduled, no revision needed (correct)
[PASS] Under-exercised dog schedule gets revised
       revised as expected, final exercise minutes = 30
[PASS] Cat litter-box query grounds in the right document
       correctly grounded in cat_enrichment.md -> Litter box maintenance (score=20.3)
[PASS] Guardrail catches an over-budget adversarial schedule
       guardrail correctly rejected and fell back to empty schedule: Over budget: 80 min scheduled but only 60 min available.
[PASS] Empty task title is rejected cleanly, not a crash
       empty title cleanly rejected: task title must not be empty
[PASS] Tight budget forces a task to be skipped with a clear reason
       correctly skipped with reason: skipped: needs 40 min but only 15 min remain
============================================================
6 out of 6 scenarios passed.
```

The harness was verified to actually detect failures (not just print PASS unconditionally): a
scenario's expectation was deliberately corrupted in a throwaway in-memory test, which correctly
produced `[FAIL]`, `5 out of 6 scenarios passed.`, and exit code 1 — see `planning.md` Milestone 7
for the full verification transcript. The real `scripts/evaluate.py` file was never modified for
that check.
