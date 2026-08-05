from .logging_utils import get_logger
from .models import Schedule

logger = get_logger(__name__)


def check_schedule_invariants(schedule: Schedule, available_minutes: int) -> list[str]:
    """Output guardrail: verify the schedule the system is about to show a user is actually
    safe, independent of however it was produced. Returns a list of issue strings (empty if
    the schedule is fine). This is a safety net -- `build_schedule` should never violate these,
    but the guardrail checks it explicitly rather than assuming."""
    issues: list[str] = []

    if schedule.total_scheduled_minutes > available_minutes:
        issues.append(
            f"Over budget: {schedule.total_scheduled_minutes} min scheduled but only "
            f"{available_minutes} min available."
        )

    included = sorted(schedule.included_items, key=lambda i: i.start_minute)
    for prev, curr in zip(included, included[1:]):
        prev_end = prev.start_minute + prev.task.duration_minutes
        if curr.start_minute < prev_end:
            issues.append(
                f"Overlapping tasks: '{prev.task.title}' ends at minute {prev_end} but "
                f"'{curr.task.title}' starts at minute {curr.start_minute}."
            )

    return issues


def safe_schedule_or_fallback(schedule: Schedule, available_minutes: int) -> tuple[Schedule, list[str]]:
    """Applies the guardrail: returns (schedule, []) if it passes, or (empty_safe_schedule,
    issues) if it fails -- never surfaces an unsafe schedule to the user."""
    issues = check_schedule_invariants(schedule, available_minutes)
    if issues:
        logger.error("Guardrail rejected schedule: %s", "; ".join(issues))
        return Schedule(), issues
    logger.info(
        "Guardrail passed: %d min scheduled / %d min available, %d task(s) included",
        schedule.total_scheduled_minutes,
        available_minutes,
        len(schedule.included_items),
    )
    return schedule, []
