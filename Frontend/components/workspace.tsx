"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Activity,
  Zap,
  ArrowUp,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Circle,
  CircleHelp,
  Copy,
  Eye,
  FileText,
  Globe2,
  LayoutGrid,
  Loader2,
  Menu,
  MessageSquare,
  Mic,
  Monitor,
  Pause,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Square,
  X,
} from "lucide-react";
import { MemoryPanel } from "@/components/memory-panel";
import { FullscreenToggle } from "@/components/fullscreen-toggle";
import { DesktopPanel } from "@/components/desktop-panel";
import { VoicePanel } from "@/components/voice-panel";
import { RuntimeSettings } from "@/components/runtime-settings";
import { SessionControls } from "@/components/session-controls";
import { MitraMark } from "@/components/mitra-mark";
import { SystemCore } from "@/components/system-core";
import { agentClient, subscribeTask } from "@/lib/api/client";
import type { Conversation, RuntimeStatus, Settings, Task } from "@/lib/types";

type View = "workspace" | "tasks" | "memory" | "settings";
const suggestions = [
  {
    icon: Globe2,
    title: "Navigate workspace",
    text: "Search, manage your workspace",
    prompt: "List the files in my workspace",
  },
  {
    icon: LayoutGrid,
    title: "Make a plan",
    text: "Turn big ideas into a clear roadmap",
    prompt: "Help me plan a focused week",
  },
  {
    icon: Zap,
    title: "Build something",
    text: "Think through a project together",
    prompt: "Help me plan my next coding project",
  },
];

export function Workspace({
  initialView = "workspace",
}: {
  initialView?: View;
}) {
  const [view, setView] = useState<View>(initialView),
    [conversations, setConversations] = useState<Conversation[]>([]),
    [activeId, setActiveId] = useState("workspace");
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [input, setInput] = useState(""),
    [sidebar, setSidebar] = useState(false),
    [query, setQuery] = useState("");
  const [notice, setNotice] = useState(""),
    [tab, setTab] = useState<"plan" | "activity">("plan"),
    [voice, setVoice] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const pendingSend = useRef<{
    id: string;
    content: string;
    conversationId: string;
  } | null>(null);
  const [provider, setProvider] = useState("offline");
  const [model, setModel] = useState("");
  const [latency, setLatency] = useState<number | null>(null);
  const [configuration, setConfiguration] = useState<Settings | null>(null);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [decisionPending, setDecisionPending] = useState(false);
  const [streamConnected, setStreamConnected] = useState(true);
  const [taskHistory, setTaskHistory] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [taskPaneOpen, setTaskPaneOpen] = useState(false);
  const current = conversations.find((c) => c.id === activeId);
  const task = selectedTask || current?.task;
  const taskId = task?.id;
  useEffect(() => {
    let active = true;
    Promise.all([
      agentClient.listConversations(),
      (async () => {
        const started = performance.now();
        const health = await agentClient.health();
        if (active) setLatency(Math.round(performance.now() - started));
        return health;
      })(),
      agentClient.listTasks(),
      agentClient.settings(),
      agentClient.runtime(),
    ])
      .then(([items, health, tasks, settings, runtimeStatus]) => {
        if (!active) return;
        setConversations(items);
        setActiveId(items[0]?.id || "");
        setProvider(health.provider);
        setModel(health.model);
        setConfiguration(settings);
        setRuntime(runtimeStatus);
        setTaskHistory(tasks);
      })
      .catch(() => {
        if (active)
          setError(
            "Backend offline. Start the FastAPI service on port 8000, then reload.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    async function refreshRuntime() {
      if (document.hidden || inFlight) return;
      inFlight = true;
      try {
        const next = await agentClient.runtime();
        if (!cancelled) setRuntime(next);
      } catch {
        if (!cancelled)
          setRuntime((previous) =>
            previous
              ? {
                  ...previous,
                  connected: false,
                  message:
                    "Runtime status unavailable. Check the API connection.",
                }
              : null,
          );
      } finally {
        inFlight = false;
      }
    }
    const interval = window.setInterval(() => void refreshRuntime(), 5000);
    const visible = () => void refreshRuntime();
    document.addEventListener("visibilitychange", visible);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);
  useEffect(() => {
    if (!taskId) return;
    return subscribeTask(
      taskId,
      (next, event) => {
        if (event.type === "approval.decided") setDecisionPending(false);
        setSelectedTask((previous) =>
          previous?.id === next.id ? next : previous,
        );
        setTaskHistory((previous) => [
          next,
          ...previous.filter((t) => t.id !== next.id),
        ]);
        setConversations((previous) =>
          previous.map((c) => {
            if (c.id !== next.conversationId || c.task?.id !== next.id)
              return c;
            const existing = c.messages.find((m) => m.id === next.messageId);
            const messages =
              next.draft !== null
                ? existing
                  ? c.messages.map((m) =>
                      m.id === next.messageId
                        ? { ...m, content: next.draft! }
                        : m,
                    )
                  : [
                      ...c.messages,
                      {
                        id: next.messageId,
                        role: "assistant" as const,
                        content: next.draft,
                        createdAt: new Date().toISOString(),
                      },
                    ]
                : c.messages;
            return { ...c, task: next, messages };
          }),
        );
      },
      setStreamConnected,
    );
  }, [taskId]);
  useEffect(() => {
    if (notice) {
      const timeout = setTimeout(() => setNotice(""), 3500);
      return () => clearTimeout(timeout);
    }
  }, [notice]);
  useEffect(() => {
    if (current?.messages.length || busy)
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [current?.messages.length, busy]);
  function navigate(next: View) {
    setView(next);
    setSidebar(false);
    if (next === "tasks")
      agentClient
        .listTasks()
        .then(setTaskHistory)
        .catch(() => setError("Could not refresh task history."));
    window.history.replaceState(
      null,
      "",
      next === "workspace" ? "/" : "/" + next,
    );
  }
  function updateConversation(next: Conversation) {
    setConversations((cs) => cs.map((c) => (c.id === next.id ? next : c)));
  }
  async function newConversation() {
    if (busy) return;
    setBusy(true);
    try {
      const conversation = await agentClient.createConversation();
      setConversations((cs) => [conversation, ...cs]);
      setActiveId(conversation.id);
      setSelectedTask(null);
      setDecisionPending(false);
      navigate("workspace");
      setInput("");
      setError("");
    } catch {
      setError(
        "Could not create a conversation. Check the backend connection.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function send(text = input) {
    if (!text.trim() || busy) return;
    const content = text.trim();
    setBusy(true);
    setError("");
    let conversation = current;
    try {
      if (!conversation) {
        conversation = await agentClient.createConversation();
        setConversations((cs) => [conversation!, ...cs]);
        setActiveId(conversation.id);
      }
    } catch {
      setError("Backend offline. Start the API, then try again.");
      setBusy(false);
      return;
    }
    const previous = pendingSend.current;
    const requestId =
      previous?.content === content &&
      previous.conversationId === conversation.id
        ? previous.id
        : crypto.randomUUID();
    pendingSend.current = {
      id: requestId,
      content,
      conversationId: conversation.id,
    };
    const updated: Conversation = {
      ...conversation,
      title: conversation.messages.length
        ? conversation.title
        : content.slice(0, 32),
      messages: [
        ...conversation.messages,
        {
          id: requestId,
          role: "user",
          content,
          createdAt: new Date().toISOString(),
        },
      ],
    };
    updateConversation(updated);
    setInput("");
    setBusy(true);
    setError("");
    try {
      updateConversation(await agentClient.sendMessage(updated, content));
      setSelectedTask(null);
      setDecisionPending(false);
      pendingSend.current = null;
    } catch (e) {
      updateConversation(conversation);
      setError(
        e instanceof Error
          ? e.message
          : "Message could not be sent. Please try again.",
      );
      setInput(content);
    } finally {
      setBusy(false);
    }
  }
  async function changeTask(
    action: "approve" | "reject" | "pause" | "resume" | "cancel",
  ) {
    if (!task || !current || busy) return;
    setBusy(true);
    setError("");
    try {
      if (action === "approve" || action === "reject") {
        setDecisionPending(true);
        await agentClient.decide(task, action);
        // Approval state changes only on the server's approval.decided event.
      } else {
        await agentClient.control(task, action);
      }
    } catch (e) {
      setDecisionPending(false);
      setError(
        e instanceof Error
          ? e.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  const activeCount = conversations.filter(
    (c) =>
      c.task &&
      !["completed", "cancelled", "failed", "needs_user_input"].includes(
        c.task.status,
      ),
  ).length;
  return (
    <div className="app-shell">
      {sidebar && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setSidebar(false)}
        />
      )}
      <aside className={`sidebar ${sidebar ? "open" : ""}`}>
        <button
          className="brand"
          onClick={() => navigate("workspace")}
          aria-label="MITRA home"
        >
          <span className="brand-symbol">
            <MitraMark size={44} />
          </span>
          <span className="brand-wordmark">MITRA</span>
          <span className="version">BETA</span>
        </button>
        <button className="new-chat" onClick={newConversation} disabled={busy}>
          <Plus size={17} /> New conversation <span>+</span>
        </button>
        <nav aria-label="Main navigation">
          {(
            [
              { id: "workspace", label: "Workspace", icon: LayoutGrid },
              { id: "tasks", label: "AI Tasks", icon: Check },
              { id: "memory", label: "Memory", icon: BookOpen },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              className={`nav-item ${view === item.id ? "selected" : ""}`}
              onClick={() => navigate(item.id)}
            >
              <item.icon size={17} />
              {item.label}
              {item.id === "tasks" && (
                <span className="count">{activeCount}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="history-heading">
          <span>CONVERSATIONS</span>
          <Search size={14} />
        </div>
        <label className="search-field">
          <Search size={13} />
          <input
            aria-label="Search conversations"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find a conversation"
          />
        </label>
        <div className="conversation-list">
          <span className="day-label">Your workspace</span>
          {conversations
            .filter((c) => c.title.toLowerCase().includes(query.toLowerCase()))
            .map((c) => (
              <button
                key={c.id}
                className={`conversation-item ${c.id === activeId && view === "workspace" ? "active" : ""}`}
                onClick={() => {
                  setActiveId(c.id);
                  setSelectedTask(null);
                  setDecisionPending(false);
                  navigate("workspace");
                }}
              >
                <MessageSquare size={14} />
                <span>{c.title}</span>
                {c.id === activeId && <span className="tiny-dot" />}
              </button>
            ))}
          {query &&
            !conversations.some((c) =>
              c.title.toLowerCase().includes(query.toLowerCase()),
            ) && <p className="muted small">No conversations found.</p>}
        </div>
        <div className="sidebar-bottom">
          <div className="runtime-card">
            <div className="runtime-icon">
              <Monitor size={17} />
            </div>
            <div>
              <strong>Local runtime</strong>
              <span>
                <i />{" "}
                {runtime?.connected
                  ? "Connected"
                  : runtime?.paired
                    ? "Paired / offline"
                    : "Not paired"}
              </span>
            </div>
            <button
              aria-label="Local runtime settings"
              onClick={() => navigate("settings")}
            >
              <ChevronRight size={15} />
            </button>
          </div>
          <button
            className={`nav-item ${view === "settings" ? "selected" : ""}`}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={17} /> Settings
          </button>
          <div className="profile">
            <span className="avatar">Y</span>
            <div>
              <strong>Your workspace</strong>
              <small>Personal account</small>
            </div>
            <span className="profile-dot" />
          </div>
        </div>
      </aside>
      <main className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setSidebar(true)}
            >
              <Menu size={20} />
            </button>
            <span>Mitra</span>
            <ChevronRight size={13} />
            <strong>
              {view === "workspace"
                ? "Overview"
                : view[0].toUpperCase() + view.slice(1)}
            </strong>
          </div>
          <div className="header-right">
            <span className="demo-badge">
              <span />{" "}
              {provider === "offline"
                ? "Backend offline"
                : `${provider} · ${model || "model not configured"}`}
            </span>
            <span className="header-divider" />
            <button
              className="icon-button mobile-task-toggle"
              aria-label="Toggle task overview"
              aria-expanded={taskPaneOpen}
              onClick={() => setTaskPaneOpen(!taskPaneOpen)}
            >
              <LayoutGrid size={17} />
            </button>
            <FullscreenToggle onError={setNotice} />
            <button
              className="icon-button"
              aria-label="About this workspace"
              onClick={() =>
                setNotice(
                  "Supervised file tools and opt-in browser inspection and approved link/field interactions. Form submission remains blocked. Desktop observation/focus and voice require explicit opt-in; saved memory is user-managed.",
                )
              }
            >
              <CircleHelp size={17} />
            </button>
            <span className="mini-avatar">Y</span>
          </div>
        </header>
        {view === "workspace" ? (
          <div
            className={`workspace-grid ${taskPaneOpen ? "show-task-panel" : ""}`}
          >
            <section className="conversation-panel">
              <div className="conversation-scroll">
                <div className="workspace-intro">
                  <div className="eyebrow">
                    <span /> MITRA / COMMAND INTERFACE
                  </div>
                  <h1>
                    Your workspace. <span>Amplified.</span>
                  </h1>
                  <p>Plan with clarity. Execute with control.</p>
                </div>
                <SystemCore
                  connected={provider !== "offline"}
                  loading={loading}
                  model={model}
                  status={task?.status}
                  activeCount={activeCount}
                  completedCount={
                    taskHistory.filter((item) => item.status === "completed")
                      .length
                  }
                  approvalCount={
                    taskHistory.filter(
                      (item) => item.status === "awaiting_approval",
                    ).length
                  }
                />
                <div className="suggestions">
                  {suggestions.map((s) => (
                    <button key={s.title} onClick={() => setInput(s.prompt)}>
                      <s.icon size={19} />
                      <strong>
                        {s.title}
                        <ArrowUp size={13} />
                      </strong>
                      <span>{s.text}</span>
                    </button>
                  ))}
                </div>
                <div className="section-divider">
                  <span>{current?.title || "Your conversation"}</span>
                  <span>
                    SESSION <span className="mono">01</span>
                  </span>
                </div>
                {!streamConnected && (
                  <div className="error" role="status">
                    Task stream disconnected. Reconnecting automatically;
                    approvals wait for server confirmation.
                  </div>
                )}
                <div className="messages" aria-live="polite">
                  {loading ? (
                    <div className="empty-state">
                      <Loader2 className="spin" /> Preparing your workspace…
                    </div>
                  ) : !current?.messages.length ? (
                    <div className="empty-state">
                      <Sparkles size={25} />
                      <h3>Awaiting your instruction.</h3>
                      <p>Tell Mitra what you’d like to work on.</p>
                    </div>
                  ) : (
                    current.messages.map((message) => (
                      <article
                        className={`message ${message.role}`}
                        key={message.id}
                      >
                        <div
                          className={`message-avatar ${message.role === "assistant" ? "agent" : ""}`}
                        >
                          {message.role === "assistant" ? (
                            <MitraMark size={19} />
                          ) : (
                            "Y"
                          )}
                        </div>
                        <div className="message-content">
                          <div className="message-meta">
                            <strong>
                              {message.role === "assistant" ? "MITRA" : "You"}
                            </strong>
                            {message.role === "assistant" && (
                              <span className="agent-label">AGENT</span>
                            )}
                            <time>
                              {new Date(message.createdAt).toLocaleTimeString(
                                "en-US",
                                {
                                  hour: "numeric",
                                  minute: "2-digit",
                                  timeZone: "Asia/Dhaka",
                                },
                              )}
                            </time>
                          </div>
                          <p>{message.content}</p>
                          {message.role === "assistant" && (
                            <button
                              className="copy-button"
                              aria-label="Copy response"
                              onClick={async () => {
                                try {
                                  await navigator.clipboard.writeText(
                                    message.content,
                                  );
                                  setNotice("Response copied.");
                                } catch {
                                  setNotice("Clipboard access is unavailable.");
                                }
                              }}
                            >
                              <Copy size={12} /> Copy
                            </button>
                          )}
                        </div>
                      </article>
                    ))
                  )}
                  {task?.draft && (
                    <div className="result-preview">
                      <div className="document-icon">
                        <FileText size={23} />
                      </div>
                      <div>
                        <strong>{task.title}</strong>
                        <p>
                          {task.status === "completed"
                            ? "Response complete"
                            : "Live response"}{" "}
                          <span>·</span> {task.provider}
                        </p>
                      </div>
                      <button
                        className="icon-button"
                        aria-label="Read artifact"
                        onClick={() =>
                          setPreview(task.draft || task.summary || "")
                        }
                      >
                        <Eye size={17} />
                      </button>
                    </div>
                  )}
                  {task?.approval && (
                    <ApprovalCard
                      task={task}
                      busy={busy || decisionPending}
                      onDecision={changeTask}
                    />
                  )}
                  {busy && (
                    <div className="thinking">
                      <span />
                      <span />
                      <span /> Updating workspace
                    </div>
                  )}
                  {error && (
                    <div className="error" role="alert">
                      {error}
                      <button
                        onClick={() => setError("")}
                        aria-label="Dismiss error"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}
                  <div ref={endRef} />
                </div>
              </div>
              <form
                className="composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  void send();
                }}
              >
                <textarea
                  aria-label="Message MITRA"
                  placeholder="What would you like to work on?"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !e.nativeEvent.isComposing
                    ) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                />
                <div className="composer-toolbar">
                  <div>
                    <span className="supervised">
                      <ShieldCheck size={14} /> Supervised{" "}
                      <ChevronDown size={12} />
                    </span>
                    <span className="composer-separator" />
                    <span className="model-label">{model || provider}</span>
                  </div>
                  <div>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Voice input information"
                      onClick={() => setVoice(true)}
                    >
                      <Mic size={17} />
                    </button>
                    <button
                      className="send-button"
                      type="submit"
                      aria-label="Send message"
                      disabled={busy || !input.trim() || loading}
                    >
                      <ArrowUp size={19} />
                    </button>
                  </div>
                </div>
              </form>
              <div className="composer-note">
                <span className="mitra-footer-brand">
                  &copy; {new Date().getFullYear()} <strong>Mitra.</strong>
                </span>
                <span className="mitra-footer-copy">
                  Your AI companion for a smarter tomorrow.
                </span>
                <span className="mitra-footer-version">v0.2.0</span>
              </div>
            </section>
            <aside className="task-panel">
              <div className="task-panel-heading">
                <span>
                  <span className="live-dot" /> Task overview
                </span>
                <span className="outline-badge">
                  {streamConnected ? "LOCAL" : "RECONNECTING"}
                </span>
              </div>
              {task ? (
                <>
                  <div className="task-title">
                    <span
                      className={`status-pill ${task.status === "completed" ? "complete" : ""}`}
                    >
                      {statusLabel(task.status)}
                    </span>
                    <h2>{task.title}</h2>
                    <p>{task.outline.join(" → ")}</p>
                  </div>
                  <div className="task-tabs">
                    <button
                      className={tab === "plan" ? "active" : ""}
                      onClick={() => setTab("plan")}
                    >
                      Plan <span>{task.steps.length}</span>
                    </button>
                    <button
                      className={tab === "activity" ? "active" : ""}
                      onClick={() => setTab("activity")}
                    >
                      Activity <span>{task.events.length}</span>
                    </button>
                  </div>
                  {tab === "plan" ? (
                    <div className="steps">
                      {task.steps.map((step, index) => (
                        <div
                          className={`step ${step.status === "verified" ? "completed" : step.status}`}
                          key={step.id}
                        >
                          <div className="step-marker">
                            {step.status === "verified" ? (
                              <Check size={13} />
                            ) : (
                              index + 1
                            )}
                          </div>
                          <details open={step.status === "pending"}>
                            <summary>
                              {step.title}
                              <ChevronDown size={12} />
                            </summary>
                            <p>{step.detail}</p>
                            <code>
                              {step.tool} · {step.status}
                            </code>
                          </details>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="activity-list">
                      {task.events.map((event) => (
                        <details key={event.id}>
                          <summary>
                            <Globe2 size={15} />
                            {event.tool}
                            <ChevronDown size={12} />
                          </summary>
                          <p>
                            <strong>Input</strong>
                            <br />
                            {event.input}
                          </p>
                          <p>
                            <strong>Output</strong>
                            <br />
                            {event.output}
                          </p>
                        </details>
                      ))}
                    </div>
                  )}
                  <div className="progress-area">
                    <div>
                      <span>Overall progress</span>
                      <strong>
                        {
                          task.steps.filter((s) => s.status === "verified")
                            .length
                        }{" "}
                        of {task.steps.length}
                      </strong>
                    </div>
                    <div className="progress-track">
                      <span
                        style={{
                          width: `${(task.steps.filter((s) => s.status === "verified").length / Math.max(1, task.steps.length)) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                  {task.summary && (
                    <p className="task-summary">{task.summary}</p>
                  )}
                  {task.status === "failed" && (
                    <button
                      className="secondary-button"
                      disabled={busy}
                      onClick={() => {
                        const message = current?.messages
                          .filter((m) => m.role === "user")
                          .at(-1);
                        if (message) void send(message.content);
                      }}
                    >
                      Retry request
                    </button>
                  )}
                  {![
                    "completed",
                    "cancelled",
                    "failed",
                    "needs_user_input",
                  ].includes(task.status) && (
                    <div className="task-actions">
                      <button
                        disabled={busy}
                        onClick={() =>
                          changeTask(
                            task.status === "paused" ? "resume" : "pause",
                          )
                        }
                      >
                        {task.status === "paused" ? (
                          <Play size={13} />
                        ) : (
                          <Pause size={13} />
                        )}{" "}
                        {task.status === "paused" ? "Resume" : "Pause"} task
                      </button>
                      <button
                        aria-label="Cancel task"
                        disabled={busy}
                        onClick={() => changeTask("cancel")}
                      >
                        <Square size={12} />
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <Circle size={25} />
                  <h3>A fresh start</h3>
                  <p>Your next task’s plan will appear here.</p>
                </div>
              )}
              <div className="context-card">
                <span className="eyebrow">USAGE CONTEXT</span>
                <div>
                  <Globe2 size={15} />
                  <span>Browser</span>
                  <span className="context-status">
                    {configuration?.browserEnabled
                      ? configuration.browserInteraction
                        ? "Interactions configured"
                        : "Read-only configured"
                      : "Disabled"}
                  </span>
                </div>
                <div>
                  <Monitor size={15} />
                  <span>Computer</span>
                  <span className="context-status">
                    {runtime?.connected
                      ? runtime.capabilities.includes("desktop")
                        ? "Scoped desktop"
                        : "Heartbeat only"
                      : "Offline"}
                  </span>
                </div>
                <div>
                  <BookOpen size={15} />
                  <span>Memory</span>
                  <span className="context-status">User managed</span>
                </div>
              </div>
              <div className="quiet-note">
                <Activity size={26} />
                <p>
                  Performance Monitor
                  <br />
                  <span>
                    {provider === "offline"
                      ? "API offline"
                      : latency === null
                        ? "Latency unavailable"
                        : `API response: ${latency} ms`}
                  </span>
                </p>
              </div>
            </aside>
          </div>
        ) : (
          <section className="secondary-page">
            <div className="eyebrow">YOUR PERSONAL WORKSPACE</div>
            <h1>
              {view === "tasks"
                ? "A little progress, every day."
                : view === "memory"
                  ? "The details that matter."
                  : "Make yourself at home."}
            </h1>
            <p className="page-description">
              {view === "tasks"
                ? "See where things stand, and pick up where you left off."
                : view === "memory"
                  ? "Manage the facts you explicitly choose to keep."
                  : "Provider configuration comes from the backend. Pair and manage your Windows helper here."}
            </p>
            {view === "tasks" && (
              <div className="task-table">
                <div className="table-heading">
                  <span>TASK</span>
                  <span>STATUS</span>
                </div>
                {taskHistory.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveId(item.conversationId || "");
                      setSelectedTask(item);
                      navigate("workspace");
                    }}
                  >
                    <span>
                      <FileText size={19} />
                      <span>
                        <strong>{item.title}</strong>
                        <small>{item.provider} · Saved task history</small>
                      </span>
                    </span>
                    <span className="status-pill">
                      {statusLabel(item.status)}
                    </span>
                    <ArrowRight size={17} />
                  </button>
                ))}
                {!taskHistory.length && (
                  <p>No tasks yet. Start a conversation to create a task.</p>
                )}
              </div>
            )}
            {view === "memory" && (
              <MemoryPanel
                conversationId={activeId === "workspace" ? null : activeId}
              />
            )}
            {view === "settings" && (
              <div className="settings-list">
                <h3>Agent & interaction</h3>
                <div className="setting-row">
                  <div>
                    <strong>Model provider</strong>
                    <p>
                      Configured by LLM_AGENT_* or LLM_* environment variables.
                    </p>
                  </div>
                  <span className="outline-badge">
                    {provider} ? {model || "not configured"}
                  </span>
                </div>
                <div className="setting-row">
                  <div>
                    <strong>Supervised autonomy</strong>
                    <p>Review consequential actions before they run.</p>
                  </div>
                  <span className="green-label">
                    <ShieldCheck size={14} /> Always on
                  </span>
                </div>
                <div className="setting-row">
                  <div>
                    <strong>Voice input & playback</strong>
                    <p>
                      Opt-in recording, transcript review and speech playback.
                      Open controls to check provider availability.
                    </p>
                  </div>
                  <button
                    className="secondary-button"
                    onClick={() => setVoice(true)}
                  >
                    View status
                  </button>
                </div>
                <h3>Model roles</h3>
                {configuration &&
                  Object.entries(configuration.roles).map(([role, config]) => (
                    <div className="setting-row" key={role}>
                      <div>
                        <strong>{role}</strong>
                        <p>
                          {config.baseUrl} |{" "}
                          {config.implemented
                            ? "Active role"
                            : "Not implemented; configuration only"}
                        </p>
                      </div>
                      <span className="outline-badge">
                        {config.model || "Not configured"}
                      </span>
                    </div>
                  ))}
                <h3>Workspace & device</h3>
                <div className="setting-row">
                  <div>
                    <strong>Allowed workspace</strong>
                    <p>{configuration?.workspace || "Backend unavailable"}</p>
                  </div>
                </div>
                <div className="setting-row">
                  <div>
                    <strong>Approval policy</strong>
                    <p>
                      Every file write requires approval. Expires after{" "}
                      {configuration
                        ? configuration.approvalSeconds / 60
                        : "not available"}{" "}
                      minutes.
                    </p>
                  </div>
                  <span className="outline-badge">
                    Max {configuration?.maxSteps ?? "not available"} steps
                  </span>
                </div>
                <div className="setting-row">
                  <div>
                    <strong>Browser tools</strong>
                    <p>
                      {configuration?.browserEnabled
                        ? `Configured origins: ${configuration.browserOrigins.join(", ")}. Inspection is isolated; no login, scripts or downloads. ${configuration.browserInteraction ? "Task sessions allow approved link clicks and text entry. Forms are blocked." : "Interaction is disabled."}`
                        : "Disabled. Set MITRA_BROWSER_ORIGINS to exact trusted site origins to enable page inspection. No browser starts at API startup."}
                    </p>
                  </div>
                  <span className="outline-badge">
                    {configuration?.browserEnabled ? "Configured" : "Disabled"}
                  </span>
                </div>
                <RuntimeSettings status={runtime} onStatus={setRuntime} />
                <DesktopPanel status={runtime} />
                <SessionControls />
                <div className="setting-row">
                  <div>
                    <strong>Appearance</strong>
                    <p>
                      Mechanical panels, cyan accents, and continuous motion.
                    </p>
                  </div>
                  <span className="appearance-swatch" />
                </div>
                <div className="settings-footnote">
                  <ShieldCheck size={18} />
                  <p>
                    Conversations, tasks and redacted traces are stored locally.
                    File tools are restricted to the configured workspace; every
                    write needs approval. Voice and desktop require explicit
                    opt-in. Desktop actions are limited to window focus.
                    Provider and role configuration is read from environment
                    variables.
                  </p>
                </div>
              </div>
            )}
          </section>
        )}
      </main>
      {preview !== null && (
        <div className="modal-backdrop">
          <section
            className="voice-modal artifact-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Artifact content"
          >
            <button
              autoFocus
              className="modal-close"
              aria-label="Close artifact"
              onClick={() => setPreview(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setPreview(null);
                if (e.key === "Tab") e.preventDefault();
              }}
            >
              <X size={19} />
            </button>
            <h2>Artifact content</h2>
            <pre>{preview}</pre>
          </section>
        </div>
      )}
      {notice && (
        <div role="status" className="toast">
          <Check size={17} />
          {notice}
          <button
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}
      {voice && (
        <VoicePanel onClose={() => setVoice(false)} onTranscript={setInput} />
      )}
    </div>
  );
}
function statusLabel(status: Task["status"]) {
  return {
    queued: "Queued",
    planning: "Choosing the next step",
    verifying: "Verifying result",
    needs_user_input: "Needs your input",
    awaiting_approval: "Awaiting your approval",
    running: "In progress",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
    failed: "Failed",
  }[status];
}
export function ApprovalCard({
  task,
  busy,
  onDecision,
}: {
  task: Task;
  busy: boolean;
  onDecision: (decision: "approve" | "reject") => void;
}) {
  const approval = task.approval!;
  const proposedStep = task.steps.find((step) => step.id === approval.stepId);
  const browserAction = proposedStep?.tool === "browser_action";
  const pending =
    approval.status === "pending" && task.status === "awaiting_approval";
  return (
    <div
      className={`approval-card ${approval.status !== "pending" ? "resolved" : ""}`}
    >
      <div className="approval-heading">
        <span>
          <ShieldCheck size={17} />
          {pending
            ? "A quick check before I continue"
            : approval.status === "approved"
              ? "Approved by you"
              : approval.status === "expired"
                ? "Approval expired"
                : approval.status === "rejected"
                  ? "Request declined"
                  : task.status === "paused"
                    ? "Approval on hold"
                    : "Task cancelled"}
        </span>
        <span className="risk-badge">{approval.risk} risk</span>
      </div>
      <p>
        {pending
          ? approval.action
          : task.summary || "Resume this task to review the pending action."}
      </p>
      <div className="file-target">
        {browserAction ? <Globe2 size={14} /> : <FileText size={14} />}
        {approval.target}
      </div>
      <details>
        <summary>
          {browserAction
            ? "Review exact browser action"
            : "Review exact write content"}
        </summary>
        <pre
          style={{
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
            maxHeight: 200,
            overflowY: "auto",
          }}
        >
          {browserAction
            ? JSON.stringify(proposedStep?.arguments, null, 2)
            : String(proposedStep?.arguments.content ?? "")}
        </pre>
      </details>
      <div className="approval-footer">
        <span>
          Workspace file write · expires{" "}
          {new Date(approval.expiresAt).toLocaleTimeString()}
        </span>
        {pending && (
          <div>
            <button disabled={busy} onClick={() => onDecision("reject")}>
              Decline
            </button>
            <button
              disabled={busy}
              className="approve-button"
              onClick={() => onDecision("approve")}
            >
              <Check size={14} /> Approve
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
