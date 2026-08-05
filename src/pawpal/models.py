from dataclasses import dataclass, field
from typing import Literal

Priority = Literal["low", "medium", "high"]

_PRIORITY_WEIGHT = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Owner:
    name: str
    preferences: str = ""


@dataclass
class Pet:
    name: str
    species: str = "dog"


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = "medium"
    category: str = "general"

    def __post_init__(self):
        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")
        if self.priority not in _PRIORITY_WEIGHT:
            raise ValueError(f"priority must be one of {list(_PRIORITY_WEIGHT)}, got {self.priority!r}")

    @property
    def priority_weight(self) -> int:
        return _PRIORITY_WEIGHT[self.priority]


@dataclass
class ScheduledItem:
    task: Task
    start_minute: int
    included: bool
    reason: str


@dataclass
class Schedule:
    items: list[ScheduledItem] = field(default_factory=list)

    @property
    def included_items(self) -> list[ScheduledItem]:
        return [i for i in self.items if i.included]

    @property
    def skipped_items(self) -> list[ScheduledItem]:
        return [i for i in self.items if not i.included]

    @property
    def total_scheduled_minutes(self) -> int:
        return sum(i.task.duration_minutes for i in self.included_items)
