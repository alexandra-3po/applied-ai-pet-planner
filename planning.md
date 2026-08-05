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
