import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pawpal.agent import PlannerAgent, format_trace_markdown
from pawpal.models import Pet, Task


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Force the rule-based critique path unless a test explicitly opts into a
    fake Claude client."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_agent_loop_terminates_and_produces_schedule():
    pet = Pet(name="Mochi", species="dog")
    tasks = [
        Task("Morning walk", 30, priority="medium", category="exercise"),
        Task("Feeding", 10, priority="high", category="feeding"),
    ]
    agent = PlannerAgent(max_iterations=2)
    run = agent.run(pet, tasks, available_minutes=60)

    assert run.schedule is not None
    assert run.iterations <= 2
    steps = [entry.step for entry in run.trace]
    assert "plan" in steps
    assert "act" in steps
    assert "critique" in steps


def test_under_exercised_dog_triggers_revision_and_fixes_it():
    pet = Pet(name="Rex", species="dog")
    # Exercise task is low priority and long; two high-priority non-exercise tasks
    # crowd it out of the first pass, leaving < 30 min of exercise scheduled.
    tasks = [
        Task("Grooming", 40, priority="high", category="grooming"),
        Task("Feeding", 20, priority="high", category="feeding"),
        Task("Morning walk", 30, priority="low", category="exercise"),
    ]
    agent = PlannerAgent(max_iterations=2)
    run = agent.run(pet, tasks, available_minutes=60)

    revise_steps = [e for e in run.trace if e.step == "revise"]
    assert revise_steps, "expected a revision to have occurred for under-exercised dog"

    exercise_minutes = sum(
        i.task.duration_minutes for i in run.schedule.included_items if i.task.category == "exercise"
    )
    assert exercise_minutes >= 30


def test_well_covered_schedule_needs_no_revision():
    pet = Pet(name="Mochi", species="dog")
    tasks = [Task("Morning walk", 45, priority="high", category="exercise")]
    agent = PlannerAgent(max_iterations=2)
    run = agent.run(pet, tasks, available_minutes=60)

    revise_steps = [e for e in run.trace if e.step == "revise"]
    assert not revise_steps
    assert run.iterations == 1


def test_format_trace_markdown_structure():
    pet = Pet(name="Mochi", species="dog")
    tasks = [Task("Morning walk", 30, priority="high", category="exercise")]
    agent = PlannerAgent(max_iterations=1)
    run = agent.run(pet, tasks, available_minutes=60)

    md = format_trace_markdown(run, run_label="Test Run")
    assert md.startswith("### Test Run")
    assert "**plan**" in md
    assert "**act**" in md
    assert "**critique**" in md
    assert "Final explanation:" in md
    assert "Morning walk" in md


def test_claude_critique_path_with_fake_client(monkeypatch):
    """Exercises _critique_with_claude's request/response handling without a real
    network call or API key, by injecting a fake `anthropic` module."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    fake_response_payload = {"ok": True, "issues": [], "priority_overrides": {}}

    class FakeContentBlock:
        def __init__(self, text):
            self.text = text

    class FakeMessages:
        def create(self, model, max_tokens, messages):
            assert model
            assert messages[0]["role"] == "user"
            return types.SimpleNamespace(content=[FakeContentBlock(json.dumps(fake_response_payload))])

    class FakeAnthropicClient:
        def __init__(self):
            self.messages = FakeMessages()

    fake_module = types.SimpleNamespace(Anthropic=FakeAnthropicClient)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    pet = Pet(name="Mochi", species="dog")
    tasks = [Task("Morning walk", 45, priority="high", category="exercise")]
    agent = PlannerAgent(max_iterations=1)
    run = agent.run(pet, tasks, available_minutes=60)

    critique_entries = [e for e in run.trace if e.step == "critique"]
    assert critique_entries
    assert critique_entries[0].detail.startswith("[claude]")
