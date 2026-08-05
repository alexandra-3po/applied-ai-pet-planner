import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pawpal.agent import PlannerAgent
from pawpal.models import Pet, Task
from pawpal.persona import baseline_vs_specialized, explain_with_persona


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _sample_run():
    pet = Pet(name="Mochi", species="dog")
    tasks = [
        Task("Morning walk", 30, priority="high", category="exercise"),
        Task("Feeding", 10, priority="high", category="feeding"),
    ]
    agent = PlannerAgent(max_iterations=1)
    run = agent.run(pet, tasks, available_minutes=60)
    return pet, run


def test_specialized_output_differs_from_baseline():
    pet, run = _sample_run()
    result = baseline_vs_specialized(pet, run.schedule, run.guidance)
    assert result["baseline"] != result["specialized"]
    assert "Coach Paws" in result["specialized"]
    assert "Coach Paws" not in result["baseline"]


def test_specialized_output_has_constrained_structure():
    pet, run = _sample_run()
    narration, source = explain_with_persona(pet, run.schedule, run.guidance)
    assert narration.startswith("Hi")
    assert "Coach Paws" in narration
    assert "Today's plan:" in narration
    assert source.startswith("template")


def test_persona_claude_path_with_fake_client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    class FakeContentBlock:
        def __init__(self, text):
            self.text = text

    class FakeMessages:
        def create(self, model, max_tokens, system, messages):
            assert "Coach Paws" in system
            assert messages[-1]["role"] == "user"
            return types.SimpleNamespace(
                content=[FakeContentBlock("Hi Jordan, Coach Paws here for Mochi! 🐾\nToday's plan:\n- test")]
            )

    class FakeAnthropicClient:
        def __init__(self):
            self.messages = FakeMessages()

    fake_module = types.SimpleNamespace(Anthropic=FakeAnthropicClient)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    pet, run = _sample_run()
    narration, source = explain_with_persona(pet, run.schedule, run.guidance)
    assert source == "claude"
    assert "Coach Paws" in narration
