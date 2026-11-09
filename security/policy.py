import hashlib
import json
from datetime import UTC, datetime

from apps.api.contracts import Approval, Step


def action_digest(tool_name: str, arguments: dict[str, object]) -> str:
    canonical = json.dumps(
        arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256((tool_name + canonical).encode("utf-8")).hexdigest()


GATED_TOOLS = frozenset({"write_file", "browser_action"})


def authorize(task_id: str, step: Step, approval: Approval | None) -> None:
    if step.tool not in GATED_TOOLS:
        return
    if approval is None or approval.taskId != task_id or approval.stepId != step.id:
        raise ValueError("No approval for this exact task and step")
    if approval.status != "approved":
        raise ValueError("Explicit stored approval is required")
    if datetime.fromisoformat(approval.expiresAt) <= datetime.now(UTC):
        raise ValueError("Approval expired")
    if approval.digest != action_digest(step.tool, step.arguments):
        raise ValueError("Action arguments changed after approval")
