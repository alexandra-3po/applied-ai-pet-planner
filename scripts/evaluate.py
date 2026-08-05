"""Standalone evaluation harness for the Applied AI Pet Planner.

Runs the real system (scheduler, RAG retrieval, agentic loop, guardrails) against a
set of predefined scenarios and prints a pass/fail summary. Not part of the pytest
suite -- this exercises end-to-end behavior and is meant to be read by a human.

Usage:
    python scripts/evaluate.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pawpal.agent import PlannerAgent
from pawpal.guardrails import safe_schedule_or_fallback
from pawpal.models import Pet, ScheduledItem, Schedule, Task
from pawpal.retrieval import load_knowledge_base, retrieve

KB = load_knowledge_base()


def scenario_well_covered_dog():
    pet = Pet(name="Mochi", species="dog")
    tasks = [Task("Morning walk", 45, priority="high", category="exercise")]
    run = PlannerAgent(max_iterations=2, knowledge_base=KB).run(pet, tasks, available_minutes=60)
    exercise_minutes = sum(
        i.task.duration_minutes for i in run.schedule.included_items if i.task.category == "exercise"
    )
    revised = any(e.step == "revise" for e in run.trace)
    if revised:
        return False, "expected no revision for an already-sufficient exercise schedule"
    if exercise_minutes < 30:
        return False, f"expected >=30 exercise minutes, got {exercise_minutes}"
    return True, f"{exercise_minutes} exercise min scheduled, no revision needed (correct)"


def scenario_under_exercised_dog_gets_revised():
    pet = Pet(name="Rex", species="dog")
    tasks = [
        Task("Grooming", 40, priority="high", category="grooming"),
        Task("Feeding", 20, priority="high", category="feeding"),
        Task("Morning walk", 30, priority="low", category="exercise"),
    ]
    run = PlannerAgent(max_iterations=2, knowledge_base=KB).run(pet, tasks, available_minutes=60)
    revised = any(e.step == "revise" for e in run.trace)
    exercise_minutes = sum(
        i.task.duration_minutes for i in run.schedule.included_items if i.task.category == "exercise"
    )
    if not revised:
        return False, "expected the agent to revise an under-exercised dog schedule"
    if exercise_minutes < 30:
        return False, f"expected revision to reach >=30 exercise minutes, got {exercise_minutes}"
    return True, f"revised as expected, final exercise minutes = {exercise_minutes}"


def scenario_cat_litter_box_grounding():
    results = retrieve("cat litter box cleaning schedule", KB, k=1)
    if not results:
        return False, "expected at least one retrieval match"
    chunk, score = results[0]
    if chunk.source != "cat_enrichment.md" or "litter" not in chunk.heading.lower():
        return False, f"expected cat_enrichment.md litter section, got {chunk.citation}"
    return True, f"correctly grounded in {chunk.citation} (score={score})"


def scenario_over_budget_adversarial_guardrail():
    unsafe = Schedule(items=[
        ScheduledItem(task=Task("A", 40, priority="high"), start_minute=480, included=True, reason="included"),
        ScheduledItem(task=Task("B", 40, priority="high"), start_minute=520, included=True, reason="included"),
    ])
    safe, issues = safe_schedule_or_fallback(unsafe, available_minutes=60)
    if not issues:
        return False, "expected the guardrail to flag an over-budget adversarial schedule"
    if safe.items:
        return False, "expected an empty fallback schedule when guardrail rejects"
    return True, f"guardrail correctly rejected and fell back to empty schedule: {issues[0]}"


def scenario_invalid_input_rejected_cleanly():
    try:
        Task(title="   ", duration_minutes=10)
    except ValueError as exc:
        return True, f"empty title cleanly rejected: {exc}"
    return False, "expected a ValueError for an empty task title, but none was raised"


def scenario_tight_budget_forces_skip():
    pet = Pet(name="Biscuit", species="dog")
    tasks = [Task("Grooming", 40, priority="high", category="grooming")]
    run = PlannerAgent(max_iterations=1, knowledge_base=KB).run(pet, tasks, available_minutes=15)
    if run.schedule.included_items:
        return False, "expected Grooming to be skipped when the budget is too small"
    if not run.schedule.skipped_items:
        return False, "expected exactly one skipped item"
    reason = run.schedule.skipped_items[0].reason
    if "15 min" not in reason:
        return False, f"expected skip reason to reference the 15-minute budget, got: {reason}"
    return True, f"correctly skipped with reason: {reason}"


SCENARIOS = [
    ("Well-covered dog schedule needs no revision", scenario_well_covered_dog),
    ("Under-exercised dog schedule gets revised", scenario_under_exercised_dog_gets_revised),
    ("Cat litter-box query grounds in the right document", scenario_cat_litter_box_grounding),
    ("Guardrail catches an over-budget adversarial schedule", scenario_over_budget_adversarial_guardrail),
    ("Empty task title is rejected cleanly, not a crash", scenario_invalid_input_rejected_cleanly),
    ("Tight budget forces a task to be skipped with a clear reason", scenario_tight_budget_forces_skip),
]


def main() -> int:
    results = []
    for name, fn in SCENARIOS:
        try:
            passed, detail = fn()
        except Exception as exc:  # a scenario itself crashing is a failure, not a script error
            passed, detail = False, f"scenario raised unexpectedly: {exc!r}"
        results.append((name, passed, detail))

    print("Applied AI Pet Planner -- Evaluation Harness")
    print("=" * 60)
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}")
        print(f"       {detail}")

    passed_count = sum(1 for _, passed, _ in results if passed)
    total = len(results)
    print("=" * 60)
    print(f"{passed_count} out of {total} scenarios passed.")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
