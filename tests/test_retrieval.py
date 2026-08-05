import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pawpal.retrieval import load_knowledge_base, retrieve

KB = load_knowledge_base()


def test_knowledge_base_loads_multiple_sources():
    sources = {chunk.source for chunk in KB}
    assert {"dog_exercise.md", "cat_enrichment.md", "medication_routines.md",
            "grooming_basics.md", "feeding_basics.md"}.issubset(sources)
    assert len(KB) >= 10  # multiple sections per file


def test_dog_exercise_query_ranks_relevant_chunk_top():
    results = retrieve("how much daily walk exercise does my dog need", KB, k=3)
    assert results, "expected at least one match"
    top_chunk, _ = results[0]
    assert top_chunk.source == "dog_exercise.md"
    assert "walk" in top_chunk.heading.lower() or "exercise" in top_chunk.heading.lower()


def test_cat_litter_box_query_ranks_relevant_chunk_top():
    results = retrieve("cat litter box cleaning schedule", KB, k=3)
    assert results
    top_chunk, _ = results[0]
    assert top_chunk.source == "cat_enrichment.md"
    assert "litter" in top_chunk.heading.lower()


def test_irrelevant_query_returns_no_matches():
    results = retrieve("spaceship rocket launch countdown", KB, k=3)
    assert results == []


def test_retrieve_respects_k_limit():
    results = retrieve("pet daily care schedule", KB, k=2)
    assert len(results) <= 2
