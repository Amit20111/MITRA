# Supervised agent slice

The original backend slice follows `docs/SLICE1_SPEC.md`. Subsequent user-requested frontend redesigns and phases 4A/4B browser capabilities are tracked in `PROJECT_PROGRESS.md`. The original blueprint is retained at the repository root as product reference.

## Execution

1. Persist a queued task and its user message.
2. Build bounded context from the current request, recent conversation, tool schemas, and clearly delimited untrusted observations. The authoritative, packaged system prompt is `agent/system_prompt.md`.
3. Request one model decision: a final answer, clarification, or one native tool call.
4. Validate registry membership, Pydantic arguments, canonical paths, and policy. Feed validation errors back once, then fail honestly.
5. Stop on a high-risk write and persist an approval bound to `sha256(tool_name + canonical_json(arguments))` with a ten-minute default expiry.
6. Dispatch only after checking stored approval, task/step identity, digest, and expiry again. Fixed subprocess entry points provide hard execution timeouts without a generic command tool.
7. Record attempted/succeeded/failed/verified separately. Verify writes by reading back and comparing SHA-256 hashes. Revise the outline and choose the next step.
8. Stop on completion, clarification, failure, cancellation, or the eight-iteration budget.

All legal task transitions live in `agent/state.py`; every legal/illegal state pair is tested. Cancellation stops owned model/tool work, but cannot undo a filesystem mutation that already happened. Pause is supported at planning and approval boundaries. Restart recovery fails interrupted work without automatic replay; pending approvals survive.

## Storage and contracts

SQLAlchemy manages SQLite transactions; Alembic owns schema revisions. Conversation and task snapshots persist messages, steps, tool events, and approvals. Separate tables retain ordered SSE events, idempotency requests, and redacted traces. Filesystem writes cannot be transactionally rolled back with the database: restart/failure messages explicitly require inspection of any attempted write.

Pydantic in `apps/api/contracts.py` is authoritative. `packages/contracts/api.d.ts` is generated with openapi-typescript. Frontend types are aliases only. Settings exposes role configuration and workspace/policy values without API keys. The model cannot modify any of these settings.

## Trust and limits

- File tools list_directory/read_file/write_file are registered. Opt-in inspect_page adds bounded read-only browser inspection when exact trusted origins are configured; see `BROWSER_PHASE.md`. Paths cannot traverse outside the allowlisted root. Symlinks/junctions/reparse points are rejected. UTF-8 file reads/writes are limited to 32 KB and directory output to 500 entries.
- Tool output is quoted and marked untrusted; it cannot change backend approval rules. This does not prove a particular model resists prompt injection; live evals are required.
- Full redacted tool output remains in traces even when context is truncated for CPU inference. Prior history and model input are bounded; there is no semantic embedding model or summarizer running. Explicit confirmed memories use bounded lexical retrieval.
- Agent and opt-in speech requests share one inference semaphore. Summarizer/embedder are configuration-only. No silent hosted fallback exists. Hosted endpoints must be HTTPS; local endpoints are loopback.
- Trace redaction covers configured secrets, common credential fields, bearer strings, and key/password/token patterns. No universal redactor can recognize every possible secret; traces may contain personal file content.
- The sandbox assumes a user-controlled local workspace. It is not an OS security boundary against a hostile process concurrently replacing paths; stronger handle-level filesystem isolation remains future hardening.
- Only loopback use with one worker is supported. Web-account authentication, multi-user isolation, browser forms/authentication, arbitrary desktop input, scheduling, and integrations are not implemented.

## Frontend

The workspace uses generated contracts and real API data. The user subsequently approved a mechanical visual redesign, animated MITRA core, and viewport-fit prompt layout. Browser configuration appears in Settings and Working Context; it reports configured/disabled rather than claiming a live connection. Memory is user-managed, and voice exposes explicit recording, review and playback controls with opt-in speech adapters. A separate build directory isolates browser E2E checks from the user's dev server.

References: [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), [openapi-typescript](https://openapi-ts.dev/cli), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

## Controlled browser sessions (4B)

`MITRA_BROWSER_INTERACTION=true` adds four tools only when trusted origins are configured. A single task-owned worker keeps one browser/context alive for up to ten minutes. It exposes numbered safe links and ordinary text fields, not selectors, arbitrary JavaScript or forms. Every action requires the current snapshot, exact arguments, and stored high-risk approval, checked both by Python dispatch and the Node worker. The worker checks page fingerprint and verifies the resulting field value or navigation URL. Success means local control/navigation verification, never form submission.

Sessions close on completion, failure, cancellation, denial, API shutdown or expiry. A service restart expires pending browser approvals and fails their tasks instead of replaying actions. A paused or awaiting-approval task may retain its session until the ten-minute deadline; expired sessions cannot be resumed for interaction. Page scripts, subresources, downloads, passwords, forms and authentication remain blocked. The default remains read-only inspection with interaction disabled.

## Windows runtime foundation (5A)

`apps/runtime` is a separate Windows process with no listener. Pairing alone enables heartbeat; --desktop adds exact-approved inspection, capture and window focus. The local API owns one-use pairing, hashed credentials, revocation and a fifteen-second heartbeat lease. The helper stores its token and API origin under CurrentUser DPAPI. API restarts retain pairing but invalidate connection leases. Settings polls visible-page status and supports pairing/revocation. This is credential authentication within the existing trusted single-user loopback deployment, not an OS sandbox or multi-user security boundary. See [protocol, setup and limitations](WINDOWS_RUNTIME.md).


## Milestones 5B/5C, 6 and 7

`DesktopService` holds a bounded in-memory queue of exact-approved operations with runtime ownership, two-minute expiry and at-most-once dispatch. The helper polls outward, reauthorizes immediately before dispatch, then validates its own target snapshot/digest/deadline and verifies focus or returns a bounded client-area image. Stop, expiry, opt-out and disconnect cancel work; a restart loses the queue and cannot replay actions. Captures use a fixed time-limited child, stay out of logs/SQLite/model context, and are deleted by expiry cleanup. See [runtime limits](WINDOWS_RUNTIME.md), including non-atomic stop/revocation and supported operations.

`MemoryService` owns persistent user-authored records, revision checks, scope isolation and bounded lexical retrieval. The agent retrieves confirmed matching facts afresh at each model decision and quotes them as untrusted data with provenance. No automatic extraction or embedding service runs. Deletion excludes future retrieval, not previously copied message/trace content.

`VoiceService` uses explicitly configured speech endpoints and a semaphore shared with `CompatibleProvider`. Responses, input lengths and timeouts are bounded; cancellation discards browser results and cancels active server work. A transcript is only a reviewable text result, never a task submission. Reviewed text enters the existing prompt/send/approval path. Audio is transient and never persisted by MITRA. See [memory and voice](MEMORY_AND_VOICE.md).
