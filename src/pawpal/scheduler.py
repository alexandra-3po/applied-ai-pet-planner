from .models import Task, Schedule, ScheduledItem


def build_schedule(tasks: list[Task], available_minutes: int, start_minute: int = 8 * 60) -> Schedule:
    """Greedily order tasks by priority (high first) then duration (shorter first),
    filling the available time budget. Tasks that don't fit are recorded as skipped
    with a plain-language reason."""
    if available_minutes < 0:
        raise ValueError(f"available_minutes must be non-negative, got {available_minutes}")

    ordered = sorted(tasks, key=lambda t: (t.priority_weight, t.duration_minutes))

    schedule = Schedule()
    clock = start_minute
    remaining = available_minutes

    for task in ordered:
        if task.duration_minutes <= remaining:
            schedule.items.append(
                ScheduledItem(
                    task=task,
                    start_minute=clock,
                    included=True,
                    reason=(
                        f"included: {task.priority} priority, fits in remaining "
                        f"{remaining} min"
                    ),
                )
            )
            clock += task.duration_minutes
            remaining -= task.duration_minutes
        else:
            schedule.items.append(
                ScheduledItem(
                    task=task,
                    start_minute=-1,
                    included=False,
                    reason=(
                        f"skipped: needs {task.duration_minutes} min but only "
                        f"{remaining} min remain"
                    ),
                )
            )

    return schedule


def format_time(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes % (24 * 60), 60)
    return f"{hours:02d}:{minutes:02d}"
