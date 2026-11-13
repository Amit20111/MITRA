import type {
  MemoryInput,
  MemoryRecord,
  MemoryUpdate,
  DesktopJob,
  DesktopRequest,
} from "../types";
import type {
  Conversation,
  Decision,
  Health,
  RuntimeStatus,
  PairingChallenge,
  SendMessage,
  Settings,
  Task,
  TaskEvent,
} from "../types";
import { acceptEvent, eventTypes } from "./events";

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
    cache: "no-store",
  });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new Error(
      typeof result?.detail === "string"
        ? result.detail
        : `API request failed (${response.status}). Check the backend connection.`,
    );
  }
  return response.json() as Promise<T>;
}

export const agentClient = {
  memories: () => request<MemoryRecord[]>("/memories"),
  saveMemory: (body: MemoryInput) => request<MemoryRecord>("/memories", body),
  updateMemory: (id: string, body: MemoryUpdate) =>
    request<MemoryRecord>(`/memories/${id}/update`, body),
  deleteMemory: (id: string) =>
    request<MemoryRecord[]>(`/memories/${id}/delete`, {}),
  desktopJobs: () => request<DesktopJob[]>("/runtime/desktop/jobs"),
  proposeDesktop: (body: DesktopRequest) =>
    request<DesktopJob>("/runtime/desktop/jobs", body),
  decideDesktop: (job: DesktopJob, approve: boolean) =>
    request<DesktopJob>(`/runtime/desktop/${job.id}/decision`, {
      digest: job.digest,
      approve,
    }),
  stopDesktop: () => request<DesktopJob[]>("/runtime/desktop/stop", {}),
  enableDesktop: () => request<DesktopJob[]>("/runtime/desktop/enable", {}),
  listConversations: () => request<Conversation[]>("/conversations"),
  createConversation: () => request<Conversation>("/conversations", {}),
  getConversation: (id: string) =>
    request<Conversation>(`/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}/rename`, { title }),
  deleteConversation: (id: string) =>
    request<Conversation[]>(`/conversations/${id}/delete`, {}),
  dataStatus: () => request<import("../types").DataStatus>("/data/status"),
  createBackup: () => request<import("../types").BackupInfo>("/data/backup", {}),
  pruneData: (days: number) =>
    request<import("../types").PruneResult>("/data/prune", { days }),
  diagnosticsUrl: () => "/api/v1/data/diagnostics",
  listTasks: () => request<Task[]>("/tasks"),
  health: () => request<Health>("/health"),
  settings: () => request<Settings>("/settings"),
  runtime: () => request<RuntimeStatus>("/runtime/status"),
  beginRuntimePairing: () => request<PairingChallenge>("/runtime/pairing", {}),
  revokeRuntime: (runtimeId: string) =>
    request<RuntimeStatus>("/runtime/revoke", { runtimeId }),
  sendMessage: (conversation: Conversation, content: string) => {
    const body: SendMessage = {
      content,
      requestId: conversation.messages.at(-1)?.id || crypto.randomUUID(),
    };
    return request<Conversation>(
      `/conversations/${conversation.id}/messages`,
      body,
    );
  },
  decide: (task: Task, decision: Decision["decision"]) => {
    if (!task.approval) throw new Error("No pending approval");
    const body: Decision = {
      taskId: task.id,
      decision,
      digest: task.approval.digest,
    };
    return request<Task>(`/approvals/${task.approval.id}/decision`, body);
  },
  control: (task: Task, action: "pause" | "resume" | "cancel") =>
    request<Task>(`/tasks/${task.id}/${action}`, {}),
};

export function subscribeTask(
  id: string,
  onTask: (task: Task, event: TaskEvent) => void,
  onConnection: (connected: boolean) => void,
) {
  let lastId = 0;
  // EventSource retains Last-Event-ID across reconnects on this connection.
  const stream = new EventSource(`/api/v1/tasks/${id}/events`);
  stream.onopen = () => onConnection(true);
  stream.onerror = () => onConnection(false);
  const receive = (event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as TaskEvent;
      if (!acceptEvent(data, id, lastId)) return;
      lastId = data.id;
      onTask(data.payload, data);
      if (
        ["completed", "failed", "cancelled", "needs_user_input"].includes(
          data.payload.status,
        )
      )
        stream.close();
    } catch {
      onConnection(false);
    }
  };
  for (const type of eventTypes)
    stream.addEventListener(type, receive as EventListener);
  return () => stream.close();
}
