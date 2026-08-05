import json
import os
from dataclasses import dataclass, field

from .models import Pet, Schedule, Task
from .retrieval import KnowledgeChunk, load_knowledge_base, retrieve
from .scheduler import build_schedule, format_time

DEFAULT_MAX_ITERATIONS = 2
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class TraceEntry:
    step: str  # "plan" | "act" | "critique" | "revise"
    detail: str


@dataclass
class AgentRun:
    trace: list[TraceEntry] = field(default_factory=list)
    schedule: Schedule | None = None
    guidance: list[tuple[KnowledgeChunk, float]] = field(default_factory=list)
    explanation: str = ""
    iterations: int = 0

    def log(self, step: str, detail: str) -> None:
        self.trace.append(TraceEntry(step=step, detail=detail))


def _critique_with_rules(species: str, schedule: Schedule) -> dict:
    """Deterministic fallback critique: currently checks the one guideline we can
    verify purely from structured data — daily dog exercise minutes (30-60 min,
    per knowledge/dog_exercise.md). Used when no ANTHROPIC_API_KEY is set, or if
    the Claude call fails, so the agent loop always completes."""
    issues = []
    overrides: dict[str, str] = {}

    if species == "dog":
        exercise_minutes = sum(
            i.task.duration_minutes for i in schedule.included_items if i.task.category == "exercise"
        )
        if exercise_minutes < 30:
            issues.append(
                f"Only {exercise_minutes} min of exercise scheduled; guidelines recommend "
                f"30-60 min/day for dogs."
            )
            for item in schedule.items:
                if item.task.category == "exercise" and not item.included:
                    overrides[item.task.title] = "high"

    return {"ok": len(issues) == 0, "issues": issues, "priority_overrides": overrides}


def _critique_with_claude(species: str, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> dict:
    import anthropic

    client = anthropic.Anthropic()

    schedule_desc = "\n".join(
        f"- {i.task.title} ({i.task.duration_minutes} min, priority={i.task.priority}, "
        f"category={i.task.category}): {'included' if i.included else 'skipped'}"
        for i in schedule.items
    ) or "(no tasks)"
    guidance_desc = "\n".join(f"- [{c.citation}] {c.text}" for c, _ in guidance) or "(no guidance retrieved)"

    prompt = f"""You are reviewing a daily pet-care schedule for a {species}.

Schedule:
{schedule_desc}

Relevant care guidelines retrieved from the knowledge base:
{guidance_desc}

Check whether the schedule adequately follows the guidelines (e.g., enough exercise time,
litter box cleaned, medication timing/spacing). Respond with ONLY a JSON object, no other text:
{{"ok": true|false, "issues": ["..."], "priority_overrides": {{"<task title>": "low"|"medium"|"high"}}}}

priority_overrides should raise the priority of skipped or under-scheduled tasks that the
guidelines say matter. If the schedule is fine, return {{"ok": true, "issues": [], "priority_overrides": {{}}}}.
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def _critique(species: str, schedule: Schedule, guidance: list[tuple[KnowledgeChunk, float]]) -> tuple[dict, str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _critique_with_claude(species, schedule, guidance), "claude"
        except Exception as exc:  # network/parsing/auth failures all fall back safely
            return _critique_with_rules(species, schedule), f"rules (claude call failed: {exc})"
    return _critique_with_rules(species, schedule), "rules (no ANTHROPIC_API_KEY set)"


class PlannerAgent:
    """Agentic loop: plan (retrieve guidance) -> act (build schedule) ->
    critique (check against guidance) -> revise (raise priorities, rebuild) ->
    repeat up to max_iterations, then explain the final plan."""

    def __init__(self, max_iterations: int = DEFAULT_MAX_ITERATIONS, knowledge_base=None):
        self.max_iterations = max_iterations
        self.kb = knowledge_base if knowledge_base is not None else load_knowledge_base()

    def run(self, pet: Pet, tasks: list[Task], available_minutes: int) -> AgentRun:
        run = AgentRun()
        working_tasks = list(tasks)

        run.log("plan", f"Gathering care guidance for {pet.species} across {len(working_tasks)} task(s)")
        guidance: list[tuple[KnowledgeChunk, float]] = []
        for t in working_tasks:
            query = f"{pet.species} {t.title} {t.category}"
            guidance.extend(retrieve(query, self.kb, k=1))
        run.guidance = guidance
        citations = "; ".join(c.citation for c, _ in guidance) or "none"
        run.log("plan", f"Retrieved {len(guidance)} guidance snippet(s): {citations}")

        schedule = build_schedule(working_tasks, available_minutes)
        run.log(
            "act",
            f"Built candidate schedule: {len(schedule.included_items)} included, "
            f"{len(schedule.skipped_items)} skipped",
        )

        for i in range(1, self.max_iterations + 1):
            run.iterations = i
            critique, source = _critique(pet.species, schedule, guidance)
            run.log("critique", f"[{source}] ok={critique['ok']} issues={critique['issues']}")

            overrides = critique.get("priority_overrides") or {}
            if critique["ok"] or not overrides:
                break

            for title, new_priority in overrides.items():
                for t in working_tasks:
                    if t.title == title:
                        t.priority = new_priority
            run.log("revise", f"Applied priority overrides: {overrides}")

            schedule = build_schedule(working_tasks, available_minutes)
            run.log(
                "act",
                f"Rebuilt schedule after revision: {len(schedule.included_items)} included, "
                f"{len(schedule.skipped_items)} skipped",
            )

        run.schedule = schedule
        run.explanation = explain_plain(pet, schedule)
        return run


def explain_plain(pet: Pet, schedule: Schedule) -> str:
    lines = [f"Daily plan for {pet.name} ({pet.species}):"]
    for item in schedule.included_items:
        lines.append(
            f"{format_time(item.start_minute)} - {item.task.title} "
            f"({item.task.duration_minutes} min) [{item.task.priority}] - {item.reason}"
        )
    if schedule.skipped_items:
        lines.append("Skipped:")
        for item in schedule.skipped_items:
            lines.append(f"  - {item.task.title}: {item.reason}")
    return "\n".join(lines)


def format_trace_markdown(run: AgentRun, run_label: str = "Agent Run") -> str:
    lines = [f"### {run_label}", ""]
    for i, entry in enumerate(run.trace, 1):
        lines.append(f"{i}. **{entry.step}** -- {entry.detail}")
    lines.append("")
    lines.append("**Final explanation:**")
    lines.append("```")
    lines.append(run.explanation)
    lines.append("```")
    return "\n".join(lines)
