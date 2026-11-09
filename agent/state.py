from apps.api.contracts import Task, TaskStatus

TERMINAL = {"completed", "failed", "cancelled", "needs_user_input"}
TRANSITIONS: dict[str, set[str]] = {
    "queued": {"planning", "paused", "cancelled", "failed"},
    "planning": {
        "running",
        "awaiting_approval",
        "completed",
        "needs_user_input",
        "paused",
        "cancelled",
        "failed",
    },
    "awaiting_approval": {"running", "paused", "cancelled", "failed"},
    "running": {"verifying", "paused", "cancelled", "failed"},
    "verifying": {"planning", "completed", "paused", "cancelled", "failed"},
    "paused": {
        "queued",
        "planning",
        "awaiting_approval",
        "running",
        "verifying",
        "cancelled",
        "failed",
    },
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "needs_user_input": set(),
}


def transition(task: Task, target: TaskStatus) -> None:
    if target not in TRANSITIONS[task.status]:
        raise ValueError(f"Illegal task transition: {task.status} -> {target}")
    task.status = target
