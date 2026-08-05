# Model Card

## Specialization: Baseline vs. "Coach Paws" persona

**What this is:** `src/pawpal/persona.py` renders the same schedule two ways: a plain mechanical
explanation (`explain_plain`, from the base agent) and a constrained-tone "Coach Paws" persona
(`explain_with_persona`) built from a fixed structure + two hand-written few-shot examples, sent
to Claude when `ANTHROPIC_API_KEY` is set, or produced by an equivalent deterministic template
otherwise (`tests/test_persona.py` covers both paths, the latter via a mocked `anthropic` module).

**Scenario:** dog "Rex", 60 available minutes, tasks: Grooming (40 min, high), Feeding (20 min,
high), Morning walk (30 min, low — later revised to high by the agentic loop in Milestone 4).

### Baseline (`explain_plain`)

```
Daily plan for Rex (dog):
08:00 - Feeding (20 min) [high] - included: high priority, fits in remaining 60 min
08:20 - Morning walk (30 min) [high] - included: high priority, fits in remaining 40 min
Skipped:
  - Grooming: skipped: needs 40 min but only 10 min remain
```

### Specialized (`explain_with_persona`, template fallback — no API key set)

```
Hi there, Coach Paws here for Rex! 🐾
Today's plan:
- Feeding (20 min)
- Morning walk (30 min)
Grooming didn't fit today, so it's pushed to tomorrow.
Sticking to this plan lines up with good practice: Most adult dogs need 30-60 minutes of physical exercise per day, split across one or two walks. Keep it up!
```

### Measurable differences

| Metric | Baseline | Specialized |
|---|---|---|
| Word count | 48 | 57 |
| Persona marker ("Coach Paws") present | No | Yes |
| Fixed 4-part structure (greeting / plan / skip note / motivational tie-in) | No | Yes |
| Cites a specific retrieved guideline in the closing line | No | Yes (dog_exercise.md, Daily walk requirements) |
| Tone | Mechanical, technical (`priority weight`, `reason` strings) | Warm, encouraging, owner-facing |

The specialized output isn't just re-worded — it restructures the same underlying data (from the
identical `Schedule` object) around a fixed persona contract (`PERSONA_SYSTEM_PROMPT`), and always
closes by tying back to one piece of retrieved guidance, which the baseline never does.

### A bug this comparison caught

The first version of the specialized template always cited `guidance[0]` — the retrieval result
for whichever task was listed *first* by the owner, regardless of whether that task was actually
included in the final schedule. In the Rex scenario, that meant citing the *Grooming* guideline
(`grooming_basics.md -> Bathing`) in a "keep it up!" sentence about a plan that didn't even include
grooming — and because `grooming_basics.md`'s bathing paragraph is hard-wrapped across two lines
in the source `.md` file, a `text.splitlines()[0]` truncation also cut the sentence off mid-clause
("...cats are largely Keep it up!"). Both were caught by actually running the comparison and
reading the output, not by the test suite (the tests only checked "differs from baseline" and
"has the right structure," neither of which would catch a citation of an unused sentence-fragment).
Fixed by adding `KnowledgeChunk.snippet` (collapses wrapped newlines, returns the first full
sentence) and picking the highest-scoring guidance chunk across the whole run, not
positionally-first.

## Reliability: Input Validation, Output Guardrail, Logging

**Input validation** (`src/pawpal/models.py`): `Owner`/`Pet` reject empty/whitespace-only names;
`Task` rejects an empty title, non-positive duration, duration over 240 minutes, and any priority
outside `low`/`medium`/`high` — all at construction time (`__post_init__`), so invalid data can
never reach the scheduler, retriever, or agent. `app.py` catches these as `ValueError` at both the
"Add task" button and the "Generate schedule" button, logs a warning, and shows `st.error` instead
of crashing.

**Output guardrail** (`src/pawpal/guardrails.py`): `check_schedule_invariants(schedule,
available_minutes)` independently re-verifies, after the fact, that (a) total scheduled minutes
never exceeds the available budget, and (b) no two included tasks overlap in time.
`safe_schedule_or_fallback()` applies this check and — if it ever fails — returns an empty,
safe schedule instead of showing the user something wrong, and logs the rejection at `ERROR`
level. This is a genuine safety net, not a restatement of the scheduler: the tests construct
adversarial `Schedule` objects by hand (bypassing `build_schedule` entirely) to prove the
guardrail catches problems independent of how they arose.

**Logging** (`src/pawpal/logging_utils.py`): every agent run and every guardrail decision is
logged to `logs/pawpal.log` (gitignored runtime artifact) via the standard `logging` module,
under the `pawpal` logger namespace so all submodules' records land in one file.

### Guardrail behavior, documented (input, behavior, result)

| Input | Behavior | Result |
|---|---|---|
| `Task(title="  ", duration_minutes=10)` | `Task.__post_init__` checks `title.strip()` | Rejected: `ValueError: task title must not be empty` |
| `Task(title="Overnight boarding", duration_minutes=500)` | Checked against `MAX_TASK_DURATION_MINUTES = 240` | Rejected: `ValueError: duration_minutes must be at most 240, got 500` |
| `Owner(name="")` | Checked in `Owner.__post_init__` | Rejected: `ValueError: owner name must not be empty` |
| Adversarial `Schedule` with 2 tasks totaling 80 min, budget 60 min (hand-built, bypassing the scheduler) | `check_schedule_invariants` sums included-item durations vs. `available_minutes` | Flagged: `"Over budget: 80 min scheduled but only 60 min available."`; `safe_schedule_or_fallback` returns an empty schedule, not the unsafe one |
| Adversarial `Schedule` with two tasks whose time ranges overlap (hand-built) | `check_schedule_invariants` sorts included items by start time and checks each pair for overlap | Flagged: `"Overlapping tasks: 'A' ends at minute 510 but 'B' starts at minute 490."` |
| Normal run: Rex, 3 tasks, 60 min budget | Guardrail checks pass | Logged: `Guardrail passed: 50 min scheduled / 60 min available, 2 task(s) included` |

Real log output from an actual run (`logs/pawpal.log`, not simulated):

```
2026-08-04 21:10:01,861 INFO pawpal.agent: Agent run starting: pet=Rex species=dog tasks=3 available_minutes=60
2026-08-04 21:10:01,862 INFO pawpal.guardrails: Guardrail passed: 50 min scheduled / 60 min available, 2 task(s) included
2026-08-04 21:10:01,862 INFO pawpal.agent: Agent run finished: pet=Rex iterations=2 guardrail_ok=True
```

## Testing Summary

**Automated tests:** 31/31 pytest tests passing across scheduler, retrieval, agent, persona, and
reliability modules (`python -m pytest -v`).

**End-to-end evaluation harness (`scripts/evaluate.py`):** 6 out of 6 predefined scenarios passed
— covering a well-covered schedule (no revision), an under-exercised schedule (revision fixes it),
correct RAG grounding for a cat scenario, a hand-built adversarial over-budget schedule (guardrail
catches it), an invalid-input scenario (rejected cleanly, no crash), and a tight-budget scenario
(clean skip reasoning). Full real output is in the README's Milestone 7 section.

**What worked:** the agentic critique-and-revise loop reliably fixes the one guideline it's
designed to check (dog exercise minutes) without ever violating the output guardrail's budget/
overlap invariants. RAG retrieval correctly grounds species- and category-specific queries after
switching to TF-IDF weighting (see Milestone 3).

**What didn't/limitations:** the rule-based critique fallback only checks one guideline
(exercise minutes) — it has no way to check medication timing, litter box frequency, or grooming
cadence without an LLM call, so those guidelines are only enforced when a real Claude API key is
present. The knowledge base has no dog-specific enrichment document (see Milestone 3), so a dog's
"Playtime" task retrieves cat-enrichment content instead.

## Reflection: AI Collaboration and System Design

**How AI was used during development:** this entire project was built through Claude Code, working
milestone-by-milestone: for each milestone, the rubric was quoted first, an implementation +
verification plan was proposed and approved before any code was written, then code was implemented,
actually run (not just described), and the real output fed back into documentation. AI was used
for: writing the domain logic and tests, drafting the RAG retriever and its scoring function,
designing the plan/act/critique/revise agent loop and its Claude API integration with a
deterministic fallback, and writing/maintaining all the documentation you're reading now
(`README.md`, `planning.md`, this file).

**A helpful AI suggestion:** switching the RAG retriever from naive term-frequency counting to
presence-based TF-IDF (Milestone 3). The naive version kept grounding a dog's "Feeding" task in the
`dog_exercise.md` document instead of `feeding_basics.md`, because the word "dog" appears in nearly
every document in the knowledge base and swamped the actually distinctive word ("feeding"). Down-
weighting common words and up-weighting rare ones (standard IDF) fixed this immediately and made
every subsequent retrieval-dependent feature (the agent's critique, the persona's guideline
citation, the evaluation harness) noticeably more correct. This wasn't a cosmetic fix — it changed
which document got cited in the user-facing output.

**A flawed AI suggestion:** the first version of the "Coach Paws" persona template cited
`guidance[0]` — the retrieval result for whichever task happened to be listed *first* by the owner
— instead of the most relevant guidance across the whole schedule. Combined with the knowledge base
being hard-wrapped prose and a naive `text.splitlines()[0]` extraction, this produced a real
user-facing bug: a sentence that cited an irrelevant, mid-sentence-truncated guideline (see
Milestone 5's "A bug this comparison caught" section above for the exact broken output). Neither
issue was caught by the automated tests, which only checked structural properties ("differs from
baseline," "has the right shape") — it was only caught by actually running the comparison and
reading the printed output line by line. That's the main lesson this project reinforced: passing
tests is necessary but not sufficient; a human (or an agent instructed to actually run and read
output, not just assert on it) still has to look at what the system produces.

**System limitations:**
- The rule-based critique fallback (used whenever `ANTHROPIC_API_KEY` isn't set — which is the
  default in this environment) only verifies one guideline structurally (dog exercise minutes).
  It cannot check medication timing, feeding frequency, or grooming cadence the way the real
  Claude-backed critique path can reason about arbitrary retrieved text.
- The knowledge base is small (5 documents, English-only, generic/US pet-care conventions) and has
  no dog-specific enrichment document, so some retrievals (a dog's "Playtime" task) fall back to
  the closest available match (cat enrichment content) rather than a precise one.
- The scheduler is priority-first, not globally time-optimal — documented in Milestone 2, but worth
  repeating here: a schedule can leave time unused if a slightly-too-long higher-priority task is
  tried before a shorter, lower-priority one that would have fit better in aggregate.
- Neither the RAG retriever nor the rule-based critique account for potential bias in what "good
  pet care" looks like — the knowledge base reflects one set of generic care guidelines and
  doesn't represent regional, cultural, or individual-animal variation (e.g., breed-specific or
  medically-necessary deviations from the stated exercise/feeding ranges).

**Future improvements:** expand the knowledge base (more species, more categories, cited external
sources); let the real Claude critique path check every retrieved guideline, not just the one the
rule-based fallback can verify structurally; add a confidence score to the agent's critique output;
support recurring/weekly tasks instead of single-day schedules only.
