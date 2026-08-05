# Model Card

> This file will accumulate the graded responsible-AI reflection (AI collaboration, helpful vs.
> flawed AI suggestions, limitations, biases, testing results) as milestones land. The
> Specialization section below is filled in now (Milestone 5); the full reflection section is
> completed in the final milestone once all features exist to reflect on.

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
