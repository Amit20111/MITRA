import type { Task } from "../lib/types";
export function taskFixture(): Task {
  return {
    id: "task-id",
    conversationId: "conversation-id",
    title: "Write a note",
    status: "awaiting_approval",
    provider: "test-only",
    model: "scripted",
    messageId: "message-id",
    draft: null,
    summary: null,
    outline: ["Write note"],
    iterations: 1,
    resumeState: null,
    steps: [
      {
        id: "step-id",
        title: "Write file",
        tool: "write_file",
        status: "pending",
        detail: "HIGH risk",
        arguments: { path: "note.txt", content: "Hello" },
        result: null,
        verification: null,
      },
    ],
    events: [],
    approval: {
      id: "approval-id",
      taskId: "task-id",
      stepId: "step-id",
      status: "pending",
      target: "note.txt",
      action: "Write note.txt",
      risk: "high",
      expiresAt: "2099-01-01T00:00:00Z",
      digest: "0".repeat(64),
    },
  };
}
