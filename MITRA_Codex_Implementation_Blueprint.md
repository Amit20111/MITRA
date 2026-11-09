# MITRA — Product Requirements, System Architecture, and Codex Implementation Blueprint

**Document purpose:** This is the source-of-truth implementation brief for Codex. Build MITRA as a full-fledged personal AI agent, not a basic chatbot. Implement the user interface first with Next.js, but design the UI against stable backend contracts so the real agent runtime can be connected incrementally.

**Project name:** MITRA  
**Assistant identity:** MITRA is the separate agent being built. The existing ChatGPT assistant may be addressed as Jarvis; do not confuse the two.  
**Owner's confirmed product decisions:**
- **Interaction mode:** Both text and voice.
- **Autonomy:** Supervised autonomy. MITRA may plan and execute multi-step tasks, but consequential actions must be gated by explicit user approval and all execution must be observable.
- **Interface:** Both web and desktop.
- **Build order:** Start with the user interface using Next.js.

---

## 1. Product vision

Build a capable personal AI agent that can understand a user's goal, create a plan, use tools, interact with the computer and browser, work with files, assist with coding and research, remember useful context, and complete multi-step workflows.

MITRA must be more than a prompt-and-response chat window. It should have:
1. A conversational interface for text and voice.
2. A persistent task and execution model.
3. A planner/orchestrator that decomposes goals into steps.
4. A tool system with typed inputs and outputs.
5. Browser, desktop-computer, and file capabilities.
6. Memory with explicit controls and provenance.
7. Permission and approval gates.
8. Execution observation, verification, retries, and recovery.
9. Logs and a clear record of what the agent did.
10. A web interface and a desktop interface backed by the same core services.

### Product principles
- **Agent, not chatbot:** prioritize task completion and tool use over merely generating text.
- **Supervised by default:** no silent consequential actions.
- **Visible execution:** users can inspect plans, running steps, tool activity, approvals, and results.
- **Modular:** model providers, tools, interfaces, and storage must be replaceable.
- **Local-first computer control:** computer automation should run on the user's machine through a local runtime/agent bridge. Cloud services may provide reasoning or hosted services, but should not be assumed to have direct access to the local desktop.
- **Provider-independent:** avoid hard-coding the entire system to one LLM vendor.
- **Recoverable:** failed steps should be reported accurately; retry only when safe.
- **Secure:** secrets, files, and computer-control permissions must be handled deliberately.

---

## 2. Confirmed scope and capability targets

### 2.1 Interaction
- Text chat.
- Voice input (speech-to-text).
- Voice output (text-to-speech).
- Ability to switch between text and voice during a task.
- Display transcripts and task progress in the conversation.
- Voice is an additional interface to the same agent runtime, not a separate agent with separate memory.

### 2.2 Agent capabilities
Design the architecture to support these capability groups:
- General reasoning, planning, and task decomposition.
- Multi-step task execution.
- Browser navigation and interaction.
- Desktop UI interaction and computer control.
- File discovery, reading, writing, and organization, subject to permissions.
- Coding assistance and controlled IDE/repository workflows.
- Research and synthesis.
- Scheduling and reminders, through configured integrations.
- Long-term and task-level memory.
- Monitoring, error detection, retry, and recovery.
- Execution history, audit logs, and result verification.

These are architectural targets. Implement each capability through a tool adapter and permission policy; do not fake capability in the UI before the relevant backend tool exists.

### 2.3 Interfaces
- **Web:** Next.js application, the first interface to build.
- **Desktop:** a later desktop shell (Tauri is the proposed lightweight option) that reuses the web UI and connects to the same backend services.
- **Local runtime:** a Windows-capable local agent/bridge for desktop automation, local files, and local applications.

---

## 3. High-level architecture

Use a layered architecture:

```text
                 ┌───────────────────────────────┐
                 │          Interfaces           │
                 │ Next.js Web │ Desktop Shell   │
                 │ Text Chat   │ Voice UI        │
                 └──────────────┬────────────────┘
                                │ HTTPS / WebSocket
                 ┌──────────────▼────────────────┐
                 │          API Gateway          │
                 │ Auth · Sessions · Tasks       │
                 │ Streaming · Approval Events   │
                 └──────────────┬────────────────┘
                                │
                 ┌──────────────▼────────────────┐
                 │       MITRA Core Runtime      │
                 │ Orchestrator / State Machine  │
                 │ Planner · Policy · Verifier   │
                 └───────┬───────────────┬───────┘
                         │               │
             ┌───────────▼──────┐  ┌─────▼────────────┐
             │ Intelligence     │  │ Memory Services  │
             │ LLM Router       │  │ User / Task      │
             │ Planning         │  │ Episodic / Vector│
             │ Context Builder  │  │ Retrieval        │
             └───────────┬──────┘  └──────────────────┘
                         │
                 ┌───────▼──────────────────────────┐
                 │           Tool Manager           │
                 │ Registry · Schemas · Permissions │
                 │ Approval · Dispatch · Results    │
                 └───────┬──────────────────────────┘
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
┌──────▼──────┐  ┌───────▼───────┐  ┌───────▼─────────┐
│ Browser     │  │ Local Computer│  │ Files / Coding  │
│ Playwright  │  │ Local Bridge  │  │ Repository Tools│
└─────────────┘  └───────────────┘  └─────────────────┘

                 ┌───────────────────────────────┐
                 │ Execution · Observation       │
                 │ Verification · Recovery       │
                 │ Audit Logs · Metrics          │
                 └───────────────────────────────┘
```

### 3.1 Core architectural rule
The Next.js frontend must never call model providers or local computer-control libraries directly. It communicates with the backend API. The backend orchestrates work and dispatches typed tool calls. The local runtime exposes a narrowly scoped authenticated interface for local-only capabilities.

### 3.2 Recommended technology choices
Treat these as initial defaults, not irreversible decisions:
- **Frontend:** Next.js (App Router), React, TypeScript.
- **UI styling:** Tailwind CSS and a consistent component system.
- **Backend API:** Python + FastAPI.
- **Realtime updates:** WebSocket or Server-Sent Events (SSE); use SSE for straightforward one-way task streaming and WebSocket where bidirectional voice/session transport is needed.
- **Agent orchestration:** a clear custom state machine first; LangGraph may be introduced when graph-based branching, persistence, and resumability justify it. Keep orchestration behind an internal interface.
- **LLM routing:** provider adapter layer supporting hosted providers (for example OpenAI, Groq, xAI) and local inference through Ollama. Do not require every provider to be configured.
- **Speech:** pluggable STT and TTS adapters. Whisper-compatible STT is a possible initial implementation; choose a TTS provider through configuration.
- **Browser automation:** Playwright.
- **Windows desktop automation:** Windows UI Automation where practical, with PyAutoGUI as a limited fallback. Keep all computer-control code inside the local runtime.
- **Database:** PostgreSQL for durable application data. SQLite may be used for a simple local-development setup.
- **Vector retrieval:** pgvector when semantic memory retrieval is implemented.
- **Background jobs:** Redis-backed worker queue only when long-running/background workloads require it; do not add infrastructure before needed.
- **Desktop shell:** Tauri as the proposed desktop wrapper, reusing the web frontend.
- **Deployment/dev environment:** Docker for backend services where useful; Git and GitHub for version control and CI.

---

## 4. Main subsystems and responsibilities

### 4.1 Next.js interface
Owns:
- Conversation list and conversation view.
- Text composer and voice controls.
- Task plan and step timeline.
- Tool activity feed.
- Approval and permission prompts.
- Task status, cancellation, and retry controls.
- Memory and settings screens.
- Responsive web layout.
- Desktop-compatible layout and reusable components.

Must not own:
- LLM orchestration.
- Secrets for model providers.
- Direct operating-system automation.
- Authorization decisions.
- Persistent agent state beyond normal UI state/cache.

### 4.2 API gateway (FastAPI)
Owns:
- API contracts and validation.
- Session and conversation endpoints.
- Task creation and status endpoints.
- Streaming task events to the frontend.
- Approval response endpoints.
- Authentication and authorization hooks.
- Health checks and service status.

### 4.3 MITRA orchestrator
Owns the lifecycle of a task:
1. Receive the user's request.
2. Load relevant conversation and memory context.
3. Determine whether the request needs a direct answer or an action plan.
4. Create a structured plan with ordered/dependent steps.
5. Classify risk and required permissions for each step.
6. Request approval when policy requires it.
7. Dispatch approved tool calls.
8. Observe tool outputs and errors.
9. Verify whether each step achieved its intended result.
10. Decide whether to continue, ask the user, retry safely, or stop.
11. Summarize completed work and report unresolved issues.
12. Persist task state and an audit trail.

Use explicit states, for example:
`queued → planning → awaiting_approval → running → verifying → completed`
with alternate terminal or paused states:
`failed`, `cancelled`, `needs_user_input`, `paused`.

Do not represent an approval request as an approval. Do not start a gated action until the backend has recorded approval.

### 4.4 Planner
Produces structured plans, not only prose. Each step should include:
- Stable step ID.
- Human-readable title and description.
- Tool/capability required.
- Structured arguments (validated against a tool schema).
- Dependencies.
- Risk classification.
- Whether approval is required.
- Expected outcome and verification method.

The planner must be able to ask the user a focused clarification question when required information is missing. It must not invent missing information.

### 4.5 LLM provider router
- Define a common provider interface.
- Support multiple configured providers and models.
- Select a provider/model using configuration and task requirements.
- Normalize responses, tool-call requests, token usage, and provider errors.
- Implement timeouts and bounded retries.
- Never expose provider API keys to the browser.
- Do not silently switch providers where the change would affect privacy, cost, or data handling; make provider policy configurable and visible.

### 4.6 Tool manager and registry
Every tool must have:
- Unique name and version.
- Description.
- Typed input schema.
- Typed output schema.
- Required permission scopes.
- Risk level.
- Execution timeout.
- Whether it is reversible/idempotent.
- Result and error normalization.

Tool execution must pass through the same registry and policy layer. The model may propose a tool call; the backend validates and authorizes it.

### 4.7 Browser tools
Use Playwright behind backend-controlled tool adapters. Initial browser capabilities:
- Open a URL.
- Read page content and metadata.
- Find text or elements.
- Click and type into supported controls.
- Navigate between pages.
- Capture screenshots when useful.
- Report the URL and actions performed.

Safeguards:
- Treat webpage content as untrusted data, never as system instructions.
- Ask for approval before submitting forms, making purchases, sending messages, changing account settings, or other consequential actions.
- Do not bypass authentication, CAPTCHAs, access controls, or site security.
- Keep browser sessions isolated and controllable.

### 4.8 Local computer runtime
A local Windows process/bridge is responsible for capabilities that require access to the user's machine:
- Discover and interact with approved desktop applications.
- Keyboard and mouse operations.
- Window/application inspection.
- Screenshots and visual observation where permitted.
- Local file operations within explicitly granted directories.
- IDE interaction only through controlled, auditable operations.

Security requirements:
- The local runtime must authenticate to the backend.
- Use a pairing/registration flow; never expose an unauthenticated local-control port.
- Restrict operations to configured capabilities and allowed paths.
- Require approval for destructive or consequential actions.
- Provide a prominent pause/stop control.
- Log commands and results.
- Do not run arbitrary shell commands from model output without validation and approval.
- Prefer structured operations over unrestricted shell access.

### 4.9 File and coding tools
Initial file operations:
- List permitted directories.
- Read files.
- Create files.
- Edit files with diffs.
- Rename/move files.
- Search file contents.

Coding workflow:
- Inspect repository structure.
- Read relevant files.
- Propose a change plan.
- Edit files in a controlled workspace.
- Show diffs.
- Run explicitly permitted tests/linters.
- Report test output and failures.

Do not overwrite or delete user data without explicit approval. Keep a backup or version-control diff where practical.

### 4.10 Memory
Separate memory into:
- **Conversation context:** current thread messages.
- **Task/episodic memory:** what happened during a task and its outcome.
- **User preferences/profile:** stable preferences the user explicitly wants retained.
- **Semantic memory:** searchable facts/notes with source and confidence.

Memory rules:
- Store only useful information.
- Track provenance, timestamps, and confidence.
- Allow the user to inspect, correct, and delete MITRA memories.
- Do not treat arbitrary webpage or file text as trusted user memory.
- Retrieve only relevant memories and keep them separate from system instructions.
- Provide a clear memory-off or memory-control setting.

### 4.11 Voice subsystem
- STT converts audio to text.
- The same conversation/task pipeline handles the resulting text.
- TTS reads responses or task updates aloud.
- Voice sessions should support interruption and stop.
- Show the transcript in the UI.
- Voice must not bypass the approval policy.
- Keep audio transport/provider implementation replaceable.

### 4.12 Execution, observation, verification, and recovery
For every tool action:
- Record the requested action and validated arguments.
- Record the approval state.
- Record start/end time and outcome.
- Capture relevant tool output.
- Verify the expected postcondition where possible.
- Distinguish `attempted`, `succeeded`, `failed`, and `verified`.
- Retry only when safe and within a bounded retry policy.
- If a step fails, reassess dependencies and either recover, ask the user, or stop.
- Never claim an action succeeded solely because a tool call was issued.

### 4.13 Security and permissions
Implement a centralized policy engine. Example action classes:
- **Low risk:** read-only inspection of already permitted data.
- **Medium risk:** creating or editing a new file in a designated workspace.
- **High risk:** deleting/overwriting files, sending communications, purchases, account changes, installing software, running commands, or actions with external consequences.

Approval requirements should be configurable, but high-risk actions require explicit user approval by default. Approval must be bound to the exact action/arguments and expire when those arguments change.

---

## 5. UI-first implementation plan

The first deliverable is a polished, functional Next.js interface using mock API data. Build it so real API endpoints can replace mocks without redesigning the app.

### Phase UI-1: Project foundation
1. Create a Next.js App Router project with TypeScript.
2. Configure Tailwind CSS and linting/formatting.
3. Establish a clean component and route structure.
4. Define design tokens for color, spacing, typography, borders, and states.
5. Create typed frontend domain models for conversations, messages, tasks, steps, tool events, approvals, and agent status.
6. Add an API client abstraction with a mock implementation.
7. Add loading, empty, error, and offline states.

Suggested structure:

```text
apps/
  web/
    app/
      (app)/
        chat/
        tasks/
        memory/
        settings/
      layout.tsx
      page.tsx
    components/
      app-shell/
      chat/
      voice/
      tasks/
      approvals/
      activity/
      settings/
      ui/
    lib/
      api/
      hooks/
      types/
      mock/
    styles/
packages/
  shared/
    types/
    schemas/
```

Adjust this structure as needed; do not create empty abstractions without a current use.

### Phase UI-2: Main application shell
Build:
- Left sidebar with MITRA identity, new conversation, conversation history, and navigation.
- Main content area.
- Header with current conversation/task status.
- Settings and profile entry points.
- Responsive behavior for narrower screens.

### Phase UI-3: Chat interface
Build:
- Message history with user and MITRA messages.
- Streaming response presentation.
- Text input and send action.
- New conversation.
- Conversation switching.
- Message timestamps and error states.
- Copy response and retry response controls where appropriate.

### Phase UI-4: Agent task visibility
Build:
- Task plan panel.
- Ordered step timeline.
- Step status indicators.
- Current action and tool name.
- Expandable tool input/output details, with secrets redacted.
- Overall task status.
- Pause/cancel controls (mocked initially).
- Completion summary and unresolved items.

### Phase UI-5: Supervised approval experience
Build an approval card/modal that shows:
- What MITRA wants to do.
- Why it wants to do it.
- Exact target/resource.
- Relevant arguments or a safe summary.
- Risk level.
- Approve and reject actions.
- Clear pending/approved/rejected/expired states.

The UI must never visually imply approval before the backend confirms it.

### Phase UI-6: Voice interface
Build the UI and frontend abstraction for:
- Microphone permission state.
- Start/stop recording.
- Listening/processing/speaking states.
- Live or final transcript.
- Playback controls.
- Interruption/stop speaking.
Initially use mocked voice events if no voice backend exists. Do not fake real microphone transcription.

### Phase UI-7: Additional screens
Build:
- Tasks/history page.
- Memory viewer and controls.
- Settings page for model/provider, voice, permissions, local runtime, and appearance.
- Local runtime connection status.

### UI acceptance criteria
- `npm run dev` starts the application successfully.
- Main chat layout is responsive.
- A user can create/switch conversations using mock data.
- A user can send a message and see a mock response.
- A mock task can display plan, progress, tool events, and completion.
- A mock high-risk action displays an approval prompt.
- Approve/reject updates the mock task state correctly.
- Voice controls show honest mock states and do not claim to record/transcribe unless implemented.
- Loading, error, empty, and disconnected states are designed.
- UI domain types are independent of mock implementation.
- No backend secrets are included in frontend code.

---

## 6. Backend implementation roadmap

Do not attempt to implement every advanced capability in one pass. After the UI contract is stable, implement in vertical slices.

### Milestone 1 — Backend foundation and contracts
- Create FastAPI service.
- Define Pydantic schemas matching frontend domain models.
- Add health endpoint.
- Add conversation/session CRUD.
- Add task creation and status endpoints.
- Add SSE/WebSocket event contract.
- Add database migrations and persistence.
- Add automated tests for schemas and endpoints.

### Milestone 2 — Core orchestration
- Implement task state machine.
- Implement planner interface and first planner.
- Implement LLM provider adapter and one working provider.
- Add tool registry and a safe mock tool.
- Persist plans, steps, events, and task outcomes.
- Stream task events to Next.js.

### Milestone 3 — Permission and approval engine
- Implement risk classification.
- Implement approval request/response endpoints.
- Bind approvals to exact tool arguments.
- Prevent dispatch until approval is confirmed.
- Add audit events and tests for denied/expired approvals.

### Milestone 4 — Browser automation
- Add Playwright tool adapters.
- Implement read-only navigation and page inspection first.
- Add controlled interaction.
- Gate consequential actions with approval.
- Add browser session isolation and tests.

### Milestone 5 — Local Windows runtime
- Create a separate local agent process.
- Add secure pairing/authentication.
- Add health/connection status.
- Add limited window inspection and screenshot capability.
- Add structured UI automation actions.
- Add allowlisted file operations.
- Add pause/stop mechanism and audit logging.

### Milestone 6 — Memory
- Implement conversation and task history retrieval.
- Add user-controlled memory records.
- Add PostgreSQL persistence and pgvector only when semantic retrieval is needed.
- Add provenance, confidence, correction, and deletion flows.
- Test relevance and isolation between users/sessions.

### Milestone 7 — Voice
- Add STT and TTS adapters.
- Connect voice transcripts to the same conversation/task pipeline.
- Add streaming and interruption.
- Add UI status events.
- Enforce the same permission and approval system for voice-initiated actions.

### Milestone 8 — Desktop and production hardening
- Wrap the web UI with Tauri.
- Connect desktop shell to the same backend and local runtime.
- Add authentication, secure secret handling, rate limits, structured logs, monitoring, backups, and CI.
- Add packaging and update strategy.
- Conduct security and failure-recovery tests.

---

## 7. API contract proposal

Use versioned routes under `/api/v1`.

### Conversations
- `GET /conversations`
- `POST /conversations`
- `GET /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`

### Messages and tasks
- `POST /conversations/{conversation_id}/messages`
  - Accepts user text and optional attachments/references.
  - Returns message/task identifiers and initial status.
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/events` (SSE)
- `POST /tasks/{task_id}/cancel`
- `POST /tasks/{task_id}/pause`
- `POST /tasks/{task_id}/resume`

### Approvals
- `GET /approvals/pending`
- `POST /approvals/{approval_id}/decision`
  - Decision is `approve` or `reject`.
  - Backend verifies that the approval is still pending and its action payload has not changed.

### Memory
- `GET /memory`
- `POST /memory`
- `PATCH /memory/{memory_id}`
- `DELETE /memory/{memory_id}`

### Runtime and health
- `GET /health`
- `GET /runtime/status`
- `POST /runtime/pair` (secure pairing flow; final design must not expose an unauthenticated control endpoint)

Use generated OpenAPI documentation and keep frontend TypeScript types synchronized with backend schemas. These endpoints are a starting contract; refine them consistently rather than implementing incompatible duplicate models.

---

## 8. Core data models

Define at least these entities:

### Conversation
- `id`
- `title`
- `created_at`
- `updated_at`
- `status`

### Message
- `id`
- `conversation_id`
- `role` (`user`, `assistant`, `system` only where appropriate)
- `content`
- `created_at`
- `attachments`
- `metadata`

### Task
- `id`
- `conversation_id`
- `goal`
- `status`
- `created_at`
- `updated_at`
- `plan`
- `result_summary`
- `error`

### TaskStep
- `id`
- `task_id`
- `order`
- `title`
- `description`
- `tool_name`
- `arguments`
- `status`
- `risk_level`
- `approval_id`
- `result`
- `verification`

### ToolEvent
- `id`
- `task_id`
- `step_id`
- `tool_name`
- `event_type`
- `safe_input_summary`
- `output_summary`
- `status`
- `started_at`
- `finished_at`

### Approval
- `id`
- `task_id`
- `step_id`
- `action_digest`
- `action_summary`
- `risk_level`
- `status`
- `requested_at`
- `decided_at`
- `expires_at`

### MemoryRecord
- `id`
- `kind`
- `content`
- `source`
- `confidence`
- `created_at`
- `updated_at`
- `user_visible`
- `embedding` (optional, only when vector search is enabled)

Use UUIDs or another consistent opaque identifier. Validate all data at API boundaries. Redact credentials and sensitive values from logs and UI.

---

## 9. Event model for live updates

The frontend should receive typed events such as:
- `message.created`
- `message.delta`
- `task.created`
- `task.status_changed`
- `plan.created`
- `step.started`
- `step.progress`
- `approval.requested`
- `approval.decided`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `step.verified`
- `task.completed`
- `task.failed`
- `task.cancelled`

Every event should include:
- Event ID.
- Task/conversation ID as applicable.
- Timestamp.
- Event type.
- Typed payload.

The client should handle reconnects and avoid duplicating events. Do not rely on UI polling as the only long-term progress mechanism.

---

## 10. Repository organization proposal

A monorepo is a reasonable starting point:

```text
mitra/
  apps/
    web/                 # Next.js UI
    api/                 # FastAPI application
    local-runtime/       # Local Windows agent/bridge
    desktop/             # Tauri shell, introduced later
  packages/
    contracts/           # Shared API/event schemas or generated types
    sdk/                 # Typed client SDK if needed
  services/
    worker/              # Background execution workers, when needed
  infra/
    docker/
    migrations/
  docs/
    PRODUCT_SPEC.md
    ARCHITECTURE.md
    API_CONTRACT.md
    SECURITY.md
  tests/
  .env.example
  README.md
```

Do not create all folders and placeholder files mechanically. Start with the web application and the minimum shared contracts. Add API and runtime services as the corresponding milestones begin.

---

## 11. Engineering standards for Codex

1. Inspect the repository before changing anything.
2. If the repository is empty, scaffold the project cleanly.
3. Before implementation, provide a short plan and list assumptions.
4. Implement one milestone or vertical slice at a time.
5. Do not silently change confirmed product decisions.
6. Do not build a basic chatbot and call it the completed agent.
7. Do not implement unrestricted autonomous shell access.
8. Do not place API keys or secrets in frontend code or source control.
9. Use environment variables and provide `.env.example` with placeholders only.
10. Use strict TypeScript and typed Python models.
11. Add tests for important state transitions, permissions, and tool behavior.
12. Handle loading, error, timeout, cancellation, and disconnected states.
13. Use structured logs with sensitive values redacted.
14. Keep modules small and responsibilities clear.
15. Document setup and commands in the README.
16. Do not claim a tool action succeeded unless its result confirms success.
17. Never bypass approval requirements to make a demo appear functional.
18. Prefer a working, testable vertical slice over a large collection of stubs.

---

## 12. First Codex task: build the Next.js UI

**Start here. Do not begin by implementing the entire backend.**

Codex should:
1. Inspect the current repository and report its state.
2. Create or configure the Next.js App Router + TypeScript application.
3. Build the main MITRA application shell.
4. Build the chat interface with mock conversation data.
5. Define typed models for conversations, messages, tasks, steps, tool events, and approvals.
6. Add a mock API/service layer that can later be replaced by FastAPI.
7. Build the task plan and live execution timeline.
8. Build the supervised approval card and its mock approve/reject behavior.
9. Build voice controls and honest placeholder states for STT/TTS.
10. Add responsive layouts, empty/loading/error states, and basic tests.
11. Run lint, type-check, and build commands; fix failures.
12. Update the README with exact setup and run instructions.
13. Summarize files created, design decisions, commands run, test results, and remaining limitations.

**Important:** The UI must represent the real intended product: a supervised, multimodal, multi-interface AI agent with plans, tools, approvals, and execution visibility. It must not look or behave like an ordinary chatbot with a microphone icon added.

---

## 13. Definition of done

The project is not complete merely because a chat page renders. A meaningful first release must demonstrate:
- Text and voice interaction paths.
- Web and desktop interface strategy.
- Structured planning and task state.
- Tool registry and controlled execution.
- Supervised approvals.
- Browser and local computer capability through separate adapters.
- File and coding workflows.
- Memory with user controls.
- Observation, verification, audit history, and safe recovery.
- Provider-independent model integration.
- Clear setup, tests, documentation, and security boundaries.

The first milestone is narrower: deliver the Next.js UI and mock workflows described in Section 12, with clean contracts ready for the backend.

---

## 14. Open implementation choices

These details were not confirmed as fixed product decisions and should remain configurable or be proposed by Codex before implementation:
- Exact LLM provider/model and routing policy.
- Exact STT and TTS providers.
- Whether the first database environment is PostgreSQL or SQLite.
- Authentication method and whether the first release is single-user only.
- Final desktop packaging and local-runtime pairing mechanism.
- Exact visual design system and branding.
- Which external services (calendar, email, task manager, etc.) should be integrated first.

Do not block the UI-first milestone on these choices. Use mock data and stable interfaces until the relevant decision is required.
