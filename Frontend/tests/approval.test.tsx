import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { ApprovalCard } from "../components/workspace";
import { taskFixture } from "./fixtures";

for (const [state, label] of [
  ["pending", "A quick check"],
  ["approved", "Approved by you"],
  ["rejected", "Request declined"],
  ["expired", "Approval expired"],
] as const) {
  test(`approval card renders ${state} from server data`, () => {
    const task = taskFixture();
    task.approval!.status = state;
    if (state !== "pending")
      task.status = state === "approved" ? "running" : "failed";
    const html = renderToStaticMarkup(
      <ApprovalCard task={task} busy={false} onDecision={() => {}} />,
    );
    assert.ok(html.includes(label));
    assert.equal(html.includes('class="approve-button"'), state === "pending");
    assert.ok(html.includes("Hello"));
  });
}
test("pending decision disables controls without showing approval", () => {
  const html = renderToStaticMarkup(
    <ApprovalCard task={taskFixture()} busy onDecision={() => {}} />,
  );
  assert.ok(html.includes('disabled=""'));
  assert.ok(!html.includes("Approved by you"));
});

test("browser approval shows exact snapshot, action and value", () => {
  const task = taskFixture();
  task.steps[0].tool = "browser_action";
  task.steps[0].arguments = {
    sessionId: "session-example",
    snapshotId: "snapshot-example",
    elementId: "e0",
    action: "fill",
    value: "Review this exact text",
  };
  task.approval!.stepId = task.steps[0].id;
  task.approval!.target = "https://example.com/note";
  const html = renderToStaticMarkup(
    <ApprovalCard task={task} busy={false} onDecision={() => {}} />,
  );
  for (const text of [
    "Review exact browser action",
    "Review this exact text",
    "snapshot-example",
    "session-example",
    "https://example.com/note",
  ])
    assert.ok(html.includes(text));
  assert.ok(!html.includes("Review exact write content"));
  assert.ok(!html.includes("Approved by you"));
});
