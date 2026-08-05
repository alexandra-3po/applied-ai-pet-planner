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
