import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pawpal.models import Task
from pawpal.scheduler import build_schedule, format_time


def test_priority_ordering():
    tasks = [
        Task("Play", 15, priority="low"),
        Task("Morning walk", 20, priority="high"),
        Task("Feeding", 10, priority="medium"),
    ]
    schedule = build_schedule(tasks, available_minutes=100)
    included_titles = [i.task.title for i in schedule.included_items]
    assert included_titles == ["Morning walk", "Feeding", "Play"]


def test_tie_break_by_duration():
    tasks = [
        Task("Long walk", 40, priority="high"),
        Task("Short walk", 10, priority="high"),
    ]
    schedule = build_schedule(tasks, available_minutes=100)
    included_titles = [i.task.title for i in schedule.included_items]
    assert included_titles == ["Short walk", "Long walk"]


def test_time_budget_overflow_skips_task():
    tasks = [
        Task("Morning walk", 30, priority="high"),
        Task("Grooming", 60, priority="low"),
    ]
    schedule = build_schedule(tasks, available_minutes=40)
    assert len(schedule.included_items) == 1
    assert schedule.included_items[0].task.title == "Morning walk"
    assert len(schedule.skipped_items) == 1
    assert schedule.skipped_items[0].task.title == "Grooming"
    assert "needs 60 min" in schedule.skipped_items[0].reason


def test_empty_task_list():
    schedule = build_schedule([], available_minutes=60)
    assert schedule.items == []
    assert schedule.total_scheduled_minutes == 0


def test_invalid_task_duration_raises():
    with pytest.raises(ValueError):
        Task("Bad task", 0, priority="high")


def test_invalid_priority_raises():
    with pytest.raises(ValueError):
        Task("Bad task", 10, priority="urgent")


def test_negative_budget_raises():
    with pytest.raises(ValueError):
        build_schedule([Task("Walk", 10)], available_minutes=-5)


def test_format_time():
    assert format_time(8 * 60) == "08:00"
    assert format_time(8 * 60 + 30) == "08:30"
