import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pawpal.agent import PlannerAgent
from pawpal.guardrails import check_schedule_invariants, safe_schedule_or_fallback
from pawpal.models import Owner, Pet, ScheduledItem, Schedule, Task


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# --- Input validation ---

def test_empty_task_title_rejected():
    with pytest.raises(ValueError, match="title"):
        Task(title="   ", duration_minutes=10, priority="high")


def test_duration_over_max_rejected():
    with pytest.raises(ValueError, match="duration_minutes"):
        Task(title="Overnight boarding", duration_minutes=500, priority="medium")


def test_empty_owner_name_rejected():
    with pytest.raises(ValueError, match="owner name"):
        Owner(name="")


def test_empty_pet_name_rejected():
    with pytest.raises(ValueError, match="pet name"):
        Pet(name="   ")


# --- Output guardrail ---

def _task(title, duration, priority="high", category="general"):
    return Task(title=title, duration_minutes=duration, priority=priority, category=category)


def test_guardrail_catches_over_budget_schedule():
    # Construct an adversarial schedule directly (bypassing build_schedule's own
    # invariant) to prove the guardrail is an independent safety net, not just a
    # restatement of the scheduler's own logic.
    schedule = Schedule(items=[
        ScheduledItem(task=_task("A", 40), start_minute=480, included=True, reason="included"),
        ScheduledItem(task=_task("B", 40), start_minute=520, included=True, reason="included"),
    ])
    issues = check_schedule_invariants(schedule, available_minutes=60)
    assert any("Over budget" in issue for issue in issues)


def test_guardrail_catches_overlapping_tasks():
    schedule = Schedule(items=[
        ScheduledItem(task=_task("A", 30), start_minute=480, included=True, reason="included"),
        ScheduledItem(task=_task("B", 30), start_minute=490, included=True, reason="included"),
    ])
    issues = check_schedule_invariants(schedule, available_minutes=120)
    assert any("Overlapping" in issue for issue in issues)


def test_guardrail_passes_valid_schedule():
    schedule = Schedule(items=[
        ScheduledItem(task=_task("A", 30), start_minute=480, included=True, reason="included"),
        ScheduledItem(task=_task("B", 20), start_minute=510, included=True, reason="included"),
    ])
    assert check_schedule_invariants(schedule, available_minutes=60) == []


def test_safe_schedule_or_fallback_rejects_unsafe_schedule():
    unsafe = Schedule(items=[
        ScheduledItem(task=_task("A", 100), start_minute=480, included=True, reason="included"),
    ])
    safe, issues = safe_schedule_or_fallback(unsafe, available_minutes=30)
    assert issues
    assert safe.items == []  # empty-safe fallback, not the unsafe schedule


def test_safe_schedule_or_fallback_passes_through_valid_schedule():
    valid = Schedule(items=[
        ScheduledItem(task=_task("A", 20), start_minute=480, included=True, reason="included"),
    ])
    safe, issues = safe_schedule_or_fallback(valid, available_minutes=60)
    assert issues == []
    assert safe is valid


# --- Logging ---

def test_agent_run_emits_log_records(caplog):
    caplog.set_level(logging.INFO, logger="pawpal")
    pet = Pet(name="Mochi", species="dog")
    tasks = [Task("Morning walk", 30, priority="high", category="exercise")]
    PlannerAgent(max_iterations=1).run(pet, tasks, available_minutes=60)

    messages = [r.message for r in caplog.records]
    assert any("Agent run starting" in m for m in messages)
    assert any("Agent run finished" in m for m in messages)
    assert any("Guardrail passed" in m for m in messages)
