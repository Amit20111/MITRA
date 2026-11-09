import assert from "node:assert/strict";
import test from "node:test";
import { acceptEvent } from "../lib/api/events";
import type { TaskEvent } from "../lib/types";
import { taskFixture } from "./fixtures";
const event: TaskEvent = {
  id: 4,
  type: "approval.decided",
  taskId: "task-id",
  conversationId: "conversation-id",
  timestamp: "2026-11-09T00:00:00Z",
  payload: taskFixture(),
  delta: null,
};
test("SSE accepts a new event and rejects replayed or out-of-order IDs", () => {
  assert.equal(acceptEvent(event, "task-id", 3), true);
  assert.equal(acceptEvent(event, "task-id", 4), false);
  assert.equal(acceptEvent(event, "task-id", 5), false);
});
test("SSE rejects another task and mismatched payloads", () => {
  assert.equal(acceptEvent(event, "other", 0), false);
  assert.equal(
    acceptEvent(
      { ...event, payload: { ...event.payload, id: "other" } },
      "task-id",
      0,
    ),
    false,
  );
});
