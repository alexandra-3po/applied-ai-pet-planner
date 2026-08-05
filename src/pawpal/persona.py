import os

from .agent import explain_plain
from .models import Pet, Schedule
from .retrieval import KnowledgeChunk

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

PERSONA_SYSTEM_PROMPT = """You are "Coach Paws", an upbeat but concise pet-care coach. You always
narrate a pet's daily plan in exactly this structure, and nothing else:
1. A one-line greeting to the owner, using the pet's name, with exactly one paw emoji (🐾).
2. "Today's plan:" followed by one short bullet per included task (time, task, duration).
3. If tasks were skipped, one short line noting it plainly (no guilt-tripping).
4. Exactly one closing motivational sentence that ties back to a specific piece of retrieved
   care guidance (cite the guideline's idea in plain language, not the raw citation).
Keep the whole thing under 80 words. Do not add extra sections, emoji beyond the one paw, or
disclaimers."""

_FEW_SHOT_EXAMPLES = [
    (
        "Pet: Mochi (cat). Plan: 08:00 Litter box cleaning (10 min, high). "
        "Guidance: cat_enrichment.md -> Litter box maintenance -- Litter boxes should be scooped "
        "at least once daily.",
        "Hi Jordan, Coach Paws here for Mochi! 🐾\n"
        "Today's plan:\n"
        "- 08:00 Litter box cleaning (10 min)\n"
        "Nothing was skipped today.\n"
        "Keeping that box scooped daily is exactly what keeps Mochi happy and avoiding accidents — nice work staying consistent!",
    ),
    (
        "Pet: Rex (dog). Plan: 08:00 Feeding (20 min, high); 08:20 Morning walk (30 min, high). "
        "Skipped: Grooming (needs 40 min but only 10 min remain). "
        "Guidance: dog_exercise.md -> Daily walk requirements -- Most adult dogs need 30-60 minutes "
        "of physical exercise per day.",
        "Hi Jordan, Coach Paws here for Rex! 🐾\n"
        "Today's plan:\n"
        "- 08:00 Feeding (20 min)\n"
        "- 08:20 Morning walk (30 min)\n"
        "Grooming didn't fit today, so it's pushed to tomorrow.\n"
        "That 30-minute walk hits the daily exercise range dogs need — Rex is set up for a good day!",
    ),
]


def _schedule_summary_for_prompt(pet: Pet, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> str:
    included = "; ".join(
        f"{i.task.title} ({i.task.duration_minutes} min, {i.task.priority})" for i in schedule.included_items
    ) or "none"
    skipped = "; ".join(f"{i.task.title} ({i.reason})" for i in schedule.skipped_items) or "none"
    guidance_desc = "; ".join(f"{c.citation} -- {c.snippet}" for c, _ in guidance[:2]) or "none"
    return (
        f"Pet: {pet.name} ({pet.species}). Included: {included}. Skipped: {skipped}. "
        f"Guidance: {guidance_desc}."
    )


def _persona_with_claude(pet: Pet, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> str:
    import anthropic

    client = anthropic.Anthropic()
    messages = []
    for example_input, example_output in _FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example_input})
        messages.append({"role": "assistant", "content": example_output})
    messages.append({"role": "user", "content": _schedule_summary_for_prompt(pet, schedule, guidance)})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=PERSONA_SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text.strip()


def _persona_template(pet: Pet, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> str:
    """Deterministic fallback: same fixed structure as the LLM persona, without a model call."""
    lines = [f"Hi there, Coach Paws here for {pet.name}! \U0001f43e", "Today's plan:"]
    for item in schedule.included_items:
        lines.append(f"- {item.task.title} ({item.task.duration_minutes} min)")
    if schedule.skipped_items:
        skipped_titles = ", ".join(i.task.title for i in schedule.skipped_items)
        lines.append(f"{skipped_titles} didn't fit today, so it's pushed to tomorrow.")
    else:
        lines.append("Nothing was skipped today.")
    if guidance:
        chunk, _score = max(guidance, key=lambda pair: pair[1])
        lines.append(f"Sticking to this plan lines up with good practice: {chunk.snippet} Keep it up!")
    else:
        lines.append("Staying consistent with a daily routine is one of the best things you can do. Keep it up!")
    return "\n".join(lines)


def explain_with_persona(pet: Pet, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> tuple[str, str]:
    """Returns (narration, source) where source is 'claude' or 'template'."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _persona_with_claude(pet, schedule, guidance), "claude"
        except Exception:
            return _persona_template(pet, schedule, guidance), "template (claude call failed)"
    return _persona_template(pet, schedule, guidance), "template (no ANTHROPIC_API_KEY set)"


def baseline_vs_specialized(pet: Pet, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> dict:
    baseline = explain_plain(pet, schedule)
    specialized, source = explain_with_persona(pet, schedule, guidance)
    return {
        "baseline": baseline,
        "specialized": specialized,
        "specialized_source": source,
    }
