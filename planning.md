# Planning Log — Applied AI Pet Planner (AI110 Project 4)

This file tracks milestone-by-milestone progress: what was planned, what was built, and how it was verified. Updated as part of each milestone, not backfilled at the end.

## Milestone 1: Repo & Environment Setup

**Goal:** Stand up the project skeleton required by the submission checklist (public repo, `assets/`, `diagrams/` folders) before any feature code is written.

**What was done:**
- Created new public GitHub repo `alexandra-3po/applied-ai-pet-planner`.
- Initialized local git repo, added `.gitignore`, `assets/`, `diagrams/` folders, and placeholder `README.md` / `model_card.md` / `ai_interactions.md`.
- Note on base project: the linked starter (`ai110-module2show-pawpal-starter`) was an unimplemented skeleton (thin Streamlit shell, template UML with placeholder classes, no scheduling logic, no tests). Rather than extend an empty template, Milestone 2 builds a real, working PawPal+ core from the starter's scenario/spec, and that becomes the documented "base project" for rubric item 1. This is disclosed explicitly in the README.

**Verification:**
- `gh repo view alexandra-3po/applied-ai-pet-planner --json isPrivate,url` confirmed public.
- `git log --oneline` and `git remote -v` confirmed initial commit pushed to `main`.

**Status:** Complete.

## Milestone 2: Base PawPal+ Core

**Rubric link:** "Clear Identification of the Base Project and Its Original Scope" (3pts) — this
milestone produces the real implementation that the README's base-project section (identification +
description + accurate context) points to.

**What was done:**
- `src/pawpal/models.py`: `Owner`, `Pet`, `Task` (validated duration/priority), `ScheduledItem`, `Schedule`.
- `src/pawpal/scheduler.py`: `build_schedule()` — priority-then-duration greedy scheduler with
  plain-language include/skip reasons; `format_time()` helper.
- `app.py`: real Streamlit UI replacing the stub — owner/pet form, task list, "Generate schedule"
  button wired to `build_schedule`, displays plan + skip reasons.
- `tests/test_scheduler.py`: 8 tests (priority ordering, duration tie-break, budget overflow,
  empty input, invalid duration/priority/budget, time formatting).
- `diagrams/uml.mmd`: real class diagram matching the implementation (replaced the placeholder).
- `requirements.txt`: `streamlit`, `pytest`.

**Verification:**
- `python -m pytest -v` → 8/8 passed (output pasted in README).
- Headless Streamlit boot check: `streamlit run app.py --server.headless true` on port 8502,
  `curl` returned HTTP 200, no import/runtime errors in server log.
- Directly ran the exact scheduling call path (`Owner`/`Pet`/`Task` → `build_schedule`) with sample
  data matching what the UI would produce; verified correct priority ordering and skip reasoning
  (output pasted in README "Sample interaction").

**Divergence from spec:** None significant. Noted one design decision explicitly in the README:
scheduling is priority-first (no look-ahead/optimal packing), so a lower-priority task that fits
can be scheduled before a higher-priority task that doesn't — intended, not a bug.

**Status:** Complete.

## Milestone 3: RAG Knowledge Base + Retrieval

**Rubric link:** "Substantial New AI Feature Added ... RAG" (3pts, required) + "RAG Enhancement:
Custom Indexing or Multi-Source Retrieval" (+2pts stretch).

**What was done:**
- `knowledge/`: 5 markdown source docs (`dog_exercise.md`, `cat_enrichment.md`,
  `medication_routines.md`, `grooming_basics.md`, `feeding_basics.md`), each with multiple
  `##` sections — satisfies "multi-source" for the stretch criterion.
- `src/pawpal/retrieval.py`: `load_knowledge_base()` chunks all docs by heading;
  `retrieve(query, chunks, k)` scores with presence-based TF-IDF (idf computed from document
  frequency across the corpus, heading matches weighted 2x) plus a light plural/singular
  stemmer (`_normalize`).
- `app.py`: retrieval is wired into the actual schedule output — each included task's line gets
  a citation + guidance snippet from the single best-matching chunk (not printed separately), and
  an expander shows the top-5 chunks for the whole day.
- `tests/test_retrieval.py`: 5 tests (multi-source load, dog-exercise query ranks correctly,
  cat-litter-box query ranks correctly, irrelevant query returns nothing, k is respected).

**Verification:**
- `python -m pytest -v` → 13/13 passed (5 new retrieval tests + 8 existing).
- Ran the real integrated code path (schedule + per-task retrieval) with sample dog tasks —
  confirmed Morning walk correctly grounds in `dog_exercise.md` (score 13.61) and Feeding
  correctly grounds in `feeding_basics.md` (score 2.39) rather than both defaulting to whichever
  doc mentions "dog" most, which is what a naive keyword-count version did before the TF-IDF fix.
- Headless Streamlit boot check on port 8503 → HTTP 200, no errors.
- README updated with a documented before/after example (mechanical reason-only line vs.
  retrieval-augmented line) per the stretch requirement to document impact on output quality.

**Divergence from spec / issues hit and fixed:**
- Initial naive term-frequency scoring (no IDF) caused ties/wrong matches because "dog" appears
  in nearly every document — fixed by switching to presence-based TF-IDF so distinctive terms
  dominate.
- Citation originally used a unicode arrow (`→`) which crashed printing on the Windows cp1252
  console (`UnicodeEncodeError`) — switched to plain ASCII `->` everywhere.
- Known, documented limitation: no dog-specific enrichment doc, so a dog's "Playtime" task
  currently retrieves the cat-enrichment chunk (content is still generically applicable, but not
  species-precise). Captured in README rather than hidden.

**Status:** Complete.

## Milestone 4: Agentic Planning Loop

**Rubric link:** "Substantial New AI Feature Added ... Agentic Workflow" (3pts, required, this is
in addition to RAG which already covers the required-feature bar) + "Agentic Workflow Enhancement"
(+2pts stretch, requires reasoning traces saved to `ai_interactions.md`, not just printed).

**What was done:**
- `src/pawpal/agent.py`: `PlannerAgent.run(pet, tasks, available_minutes)` implements
  plan (retrieve guidance) -> act (`build_schedule`) -> critique -> revise, up to
  `max_iterations` (default 2). `_critique()` dispatches to `_critique_with_claude()` (real
  Anthropic API call, model `claude-haiku-4-5-20251001`, JSON-only response contract) when
  `ANTHROPIC_API_KEY` is set, else `_critique_with_rules()` (deterministic: flags dog schedules
  with <30 min of `category="exercise"` tasks, matching `knowledge/dog_exercise.md`). Any
  exception from the Claude call falls back to rules automatically.
- `format_trace_markdown()` renders a run's `TraceEntry` list + final explanation as markdown.
- `app.py`: replaced the direct `build_schedule()` call with `AGENT.run(...)`; added a task
  category selector to the UI (categories feed both retrieval queries and the exercise-minutes
  critique); added an "Agent reasoning trace" expander.
- `ai_interactions.md`: rewritten with a real, non-templated trace from an actual run (an
  under-exercised dog schedule that gets revised), plus the exact command used to produce it and
  a plain-language walkthrough — satisfies "traces saved... not just printed to terminal."
- `tests/test_agent.py`: 5 tests — loop terminates and produces a schedule; an engineered
  under-exercised-dog scenario triggers exactly the expected revision and the final schedule
  meets the guideline; a well-covered schedule needs no revision; trace markdown structure is
  correct; the real Claude code path is exercised end-to-end via a fake `anthropic` module
  injected into `sys.modules` (no network call or real key needed, but the request/response
  handling code actually runs).

**Verification:**
- `python -m pytest -v` → 18/18 passed (5 new agent tests + 13 prior).
- Real end-to-end run via `python -c` for the under-exercised-dog scenario, full trace pasted
  into README and `ai_interactions.md` — shows the schedule actually changes (Grooming gets
  bumped for Morning walk) after critique, not a cosmetic difference.
- Headless Streamlit boot check on port 8504 → HTTP 200, no import/runtime errors with the agent
  wired into `app.py`.

**Divergence from spec:** None. Design choice made explicit in README/model_card: only one
guideline (dog exercise minutes) is currently checked by the rule-based fallback, since it's the
one guideline verifiable from purely structured data (category + duration) without an LLM call;
the real Claude critique path can reason about any of the retrieved guidance text, not just this
one rule, which is the intended division of labor between the deterministic fallback and the
real model.

**Status:** Complete.

## Milestone 5: Specialization/Tone Layer ("Coach Paws" persona)

**Rubric link:** "Fine-Tuning or Specialization Behavior" (+2pts stretch) — specialized model
behavior via few-shot patterns/constrained tone, with a baseline-vs-specialized comparison in
`model_card.md`.

**What was done:**
- Renamed `agent._explain` to public `explain_plain` so it can be reused as the baseline.
- `src/pawpal/persona.py`: `PERSONA_SYSTEM_PROMPT` + 2 few-shot example pairs define a fixed
  4-part "Coach Paws" structure. `explain_with_persona()` dispatches to `_persona_with_claude()`
  (real Claude call with the few-shot messages) when `ANTHROPIC_API_KEY` is set, else
  `_persona_template()` (deterministic, same structure). `baseline_vs_specialized()` returns both
  renderings of the same schedule for direct comparison.
- `app.py`: added a "Plain" / "Coach Paws" radio toggle so both outputs are visible in the running
  app for the same generated schedule.
- `model_card.md`: Specialization section with the real baseline vs. specialized text, a
  measurable-differences table (word count, persona marker, structure, guideline citation), and a
  documented bug this comparison caught (see below).
- `tests/test_persona.py`: 3 tests — specialized output differs from baseline and contains the
  persona marker while baseline doesn't; specialized output has the constrained structure; the
  real Claude few-shot code path is exercised via a mocked `anthropic` module.

**Verification:**
- `python -m pytest -v` → 21/21 passed (3 new persona tests + 18 prior).
- Real run via `python -c` (with `PYTHONIOENCODING=utf-8` to avoid the Windows console crash)
  printing baseline vs. specialized side by side, plus word counts — pasted into `model_card.md`.
- Headless Streamlit boot check on port 8505 with the tone toggle wired in → HTTP 200.

**Bug found and fixed during verification (not just described as a divergence):** the first
`_persona_template()` cited `guidance[0]` — the retrieval result for whichever task the owner
listed *first*, not necessarily one that ended up in the final schedule. In the demo scenario this
cited the Grooming guideline in a closing "keep it up!" line about a plan that didn't include
grooming. Separately, because `knowledge/grooming_basics.md`'s prose is hard-wrapped across lines,
`chunk.text.splitlines()[0]` cut that citation off mid-sentence ("...cats are largely Keep it
up!"). Both were only caught by actually printing and reading the real output — the persona tests
(structure + "differs from baseline") wouldn't have caught either. Fixed by adding
`KnowledgeChunk.snippet` (`src/pawpal/retrieval.py`, collapses wrapped newlines and returns the
first full sentence) and selecting the highest-scoring guidance chunk across the whole run instead
of the positionally-first one. Re-verified after the fix (see `model_card.md`).

**Status:** Complete.

## Milestone 6: Reliability — Input Validation, Output Guardrail, Logging

**Rubric link:** "Reliability, Evaluation, or Guardrail Component" (3pts, required) — mechanism
functional + meaningfully improves reliability + markdown examples showing input/behavior/result.

**What was done:**
- `src/pawpal/models.py`: added `MAX_TASK_DURATION_MINUTES = 240`; `Task.__post_init__` now also
  rejects empty/whitespace titles and over-240-min durations; new `Owner.__post_init__` and
  `Pet.__post_init__` reject empty/whitespace names.
- `src/pawpal/guardrails.py`: `check_schedule_invariants()` (budget + no-overlap checks,
  independent of how the schedule was produced) and `safe_schedule_or_fallback()` (returns an
  empty safe schedule + logs at ERROR if either check fails, otherwise logs INFO and passes
  through unchanged).
- `src/pawpal/logging_utils.py`: `get_logger()` configures a single `pawpal`-namespaced file
  handler writing to `logs/pawpal.log` (added to `.gitignore` — runtime artifact, not committed).
- `src/pawpal/agent.py`: `PlannerAgent.run()` now logs run start/end and applies
  `safe_schedule_or_fallback` to the final schedule before returning it (adds a `"guardrail"`
  trace step).
- `app.py`: both the "Add task" and "Generate schedule" buttons catch `ValueError` from the model
  validation, log a warning, and show `st.error` instead of crashing.
- `tests/test_reliability.py`: 10 tests — 4 input-validation rejections (empty title, over-max
  duration, empty owner/pet name), 3 guardrail checks (over-budget caught, overlap caught, valid
  schedule passes), 2 `safe_schedule_or_fallback` behavior tests (rejects unsafe / passes through
  valid), 1 logging test using pytest's `caplog` fixture.

**Verification:**
- `python -m pytest -v` → 31/31 passed (10 new reliability tests + 21 prior).
- Real rejected-input demo via `python -c`: empty title, over-max duration, empty owner name all
  produced clear `ValueError` messages, not crashes (output pasted in `model_card.md`).
- Real adversarial-schedule demo: hand-built over-budget and overlapping `Schedule` objects
  (bypassing `build_schedule` entirely) both correctly flagged by `check_schedule_invariants`,
  exact message text verified and pasted into `model_card.md`.
- Ran a real `PlannerAgent.run()` and inspected the actual `logs/pawpal.log` contents afterward —
  pasted real (not simulated) log lines into `model_card.md`.
- Headless Streamlit boot check on port 8506 with validation wired into both buttons → HTTP 200.
- `model_card.md` updated with the required input/behavior/result markdown table.

**Divergence from spec:** None. Note: the 240-minute task duration cap matches the existing UI
slider bound from Milestone 2 rather than being a new arbitrary limit — documented as intentional.

**Status:** Complete.

## Milestone 7: Evaluation Harness

**Rubric link:** "Test Harness or Evaluation Script" (+2pts stretch) — a script evaluating
multiple predefined inputs, printing a pass/fail summary.

**What was done:**
- `scripts/evaluate.py`: standalone script (run directly, not via pytest) with 6 scenarios that
  exercise the real system end-to-end: well-covered dog schedule (no revision expected),
  under-exercised dog (revision expected + verified), cat litter-box RAG grounding, hand-built
  adversarial over-budget schedule (guardrail expected to catch it), empty-title input (expected
  clean rejection), and a too-small time budget (expected clean skip reasoning). Each scenario
  returns `(passed: bool, detail: str)`; the script prints a `[PASS]`/`[FAIL]` line + detail per
  scenario, then a summary line in the spec's requested format ("N out of M scenarios passed"),
  and exits with code 1 if anything failed.

**Verification:**
- Ran `python scripts/evaluate.py` directly → `6 out of 6 scenarios passed.`, exit code 0. Full
  real output pasted into README.
- Proved the harness actually detects failures, not just prints PASS unconditionally: in a
  throwaway `python -c` session (the committed `scripts/evaluate.py` file itself was never
  edited), monkey-patched `evaluate.SCENARIOS[0]` to a deliberately-broken variant and reran
  `evaluate.main()` → correctly printed `[FAIL] ... DELIBERATELY BROKEN FOR VERIFICATION: ...`,
  `5 out of 6 scenarios passed.`, and returned exit code 1. Reran the real, unmodified script
  afterward to confirm it was untouched and still reports `6 out of 6`.
- `model_card.md` updated with a Testing Summary section in the spec's requested prose format
  ("X out of Y tests passed; ..."), plus what worked / what didn't / limitations.

**Divergence from spec:** None.

**Status:** Complete.

## Milestone 8: Architecture Diagram

**Rubric link:** "System Architecture Diagram" (3pts, required) — Mermaid source file, clear data
flow (input -> processing -> output), matches actual implementation.

**What was done:**
- `diagrams/architecture.mmd`: a system-level Mermaid flowchart (distinct from `diagrams/uml.mmd`,
  the M2 class diagram) showing: UI input -> validation -> agentic plan/act/critique/revise loop
  -> output guardrail -> specialization/narration -> UI output, plus logging and the pytest/
  evaluation-harness testing checkpoints as dotted-line side paths.
- Cross-checked every diagram node against the actual file/function it represents (see
  verification below) rather than drawing an aspirational/theoretical diagram.
- README updated with a "Milestone 8: Architecture Overview" section: a plain-language,
  step-by-step walkthrough matching the diagram, and a link to the `.mmd` source.

**Verification:**
- No Mermaid renderer is available in this development environment, so instead of only manually
  checking bracket/subgraph balance, the diagram was actually rendered server-side via kroki.io's
  Mermaid engine: `curl -X POST --data-binary @diagrams/architecture.mmd https://kroki.io/mermaid/svg`
  returned a valid SVG flowchart (HTTP 200, real flowchart SVG content) both before and after a
  later accuracy fix — genuine syntax validation, not just eyeballing.
- Node-by-node cross-check against real code: Input/Validate/Reject -> `app.py` +
  `models.py.__post_init__`; Plan/Act/Critique/Revise -> `agent.py PlannerAgent.run()`; KB/Retrieve
  -> `retrieval.py`; Check/Fallback -> `guardrails.py`; Baseline/Specialized -> `agent.explain_plain`
  / `persona.explain_with_persona`; LogFile -> `logging_utils.py`; Traces -> `ai_interactions.md`;
  Pytest/Harness -> the actual test suite and `scripts/evaluate.py`. Every node maps to a real,
  already-built file/function — nothing in the diagram is aspirational.
- Structural check: 8 `subgraph`/8 `end`, balanced `[`/`]` (27/27), balanced quotes (54, even).

**Issue caught and fixed during verification:** the first draft had `Plan`/`Act`/`Critique`/
`Revise` each drawing a dotted "trace" edge directly into `ai_interactions.md`, implying every
single run automatically appends its trace there. That's not what the code does — only one real,
manually-captured example run is committed to `ai_interactions.md` (Milestone 4); the live
per-run trace only appears in the Streamlit "Agent reasoning trace" expander and `logs/pawpal.log`.
Fixed by replacing those 4 edges with a single accurate edge (`Agent -. format_trace_markdown .->
Traces`) and relabeling the node to say "captured example run", not "saved reasoning traces"
(which read as automatic/comprehensive). Re-rendered via kroki.io after the fix to confirm it
still parses.

**Divergence from spec:** None, after the fix above.

**Status:** Complete.

## Milestone 9: Final Documentation + Submission Checklist

**Rubric link:** "Documentation: README and Setup Instructions" (3pts), "Reflection on AI
Collaboration and System Design" (3pts) — both largely built incrementally across milestones;
this milestone fills the one remaining gap (the graded reflection) and does a final consistency
pass, plus the 8-item submission checklist from the Requirements PDF.

**What was done:**
- `model_card.md`: added the "Reflection: AI Collaboration and System Design" section — how AI
  was used during development, one concrete helpful AI suggestion (the TF-IDF retrieval fix) and
  one concrete flawed one (the `guidance[0]`/truncated-citation persona bug), system limitations
  (rule-based critique's single-guideline coverage, small/English-only knowledge base, priority-
  first scheduling, no bias-awareness in the guidelines), and future improvements. Removed the
  now-stale "work in progress" banner from the top of the file.
- `README.md`: added a real Title/Summary opening paragraph (previously just a "grows with each
  milestone" note), a consolidated "Design Decisions" section pulling together the trade-offs
  already discussed per-milestone, and an explicit "Reflection" section that points to
  `model_card.md` rather than duplicating content there (per the spec's explicit instruction that
  reflection content only in the README doesn't earn the reflection points).
- Submission checklist verified with real commands, not assumed:
  1. Code pushed — `git log` shows 9 commits on `main`, this milestone adds a 10th.
  2. Repo public — `gh repo view` confirms `isPrivate: false`.
  3. Required files present — `README.md`, `model_card.md`, `diagrams/uml.mmd`,
     `diagrams/architecture.mmd` all confirmed present via `ls`.
  4. Reproducible execution evidence — every milestone's README/model_card section has real
     pasted command output, not screenshots (verified throughout M2-M8).
  5. Commit history — 9 commits, each with a descriptive milestone-scoped message.
  6. Standardized documentation — README's "Base project" section identifies PawPal+ explicitly;
     `model_card.md` now answers all reflection prompts (AI collaboration, biases, testing).
  7. Demo evidence — README has well over 2-3 example input/output pairs as fenced code blocks
     across the RAG, agent, persona, reliability, and evaluation-harness sections.
  8. Final changes committed and pushed — this commit.

**Verification:**
- Final full run: `python -m pytest -v` → 31/31 passed; `python scripts/evaluate.py` → 6/6
  scenarios passed. Clean end-of-project snapshot, both pasted above in this entry's context.
- Re-read README and model_card.md top-to-bottom as a first-time reader to check nothing
  contradicts earlier milestones (no stale "work in progress" banners left, no orphaned TODOs).

**Divergence from spec:** None.

**Status:** Complete. All 9 milestones (M1-M9) done; project targets full required (21pts) +
all stretch (8pts) = 29pts against the grading rubric.
