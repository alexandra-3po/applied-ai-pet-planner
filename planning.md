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
