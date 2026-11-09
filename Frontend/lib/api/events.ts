import type { TaskEvent } from "../types";

export const eventTypes: TaskEvent["type"][] = [
  "message.created",
  "message.delta",
  "task.created",
  "task.status_changed",
  "plan.created",
  "step.started",
  "approval.requested",
  "approval.decided",
  "tool.started",
  "tool.completed",
  "tool.failed",
  "step.verified",
  "task.completed",
  "task.failed",
  "task.cancelled",
];

export function acceptEvent(
  event: TaskEvent,
  taskId: string,
  lastId: number,
): boolean {
  return (
    Number.isSafeInteger(event.id) &&
    event.id > lastId &&
    event.taskId === taskId &&
    event.payload?.id === taskId &&
    eventTypes.includes(event.type)
  );
}
