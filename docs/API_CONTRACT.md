# API and event contract

Pydantic schemas in `apps/api/contracts.py` are authoritative. FastAPI publishes `/openapi.json` and `/docs`. Generated TypeScript is checked for drift in CI.

| Method   | `/api/v1` route                             | Purpose                                                                    |
| -------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| GET      | `/health`                                   | Active provider/model and API status; not an inference readiness guarantee |
| GET      | `/settings`                                 | Public per-role config, workspace, step budget, approval policy            |
| GET      | `/runtime/status`                           | Honest unimplemented local-runtime status                                  |
| GET/POST | `/conversations`                            | List/create persisted conversations                                        |
| GET      | `/conversations/{uuid}`                     | Messages and current task                                                  |
| POST     | `/conversations/{uuid}/messages`            | `{content, requestId: UUID}`; returns queued task (202)                    |
| GET      | `/tasks`                                    | All historical tasks                                                       |
| GET      | `/tasks/{uuid}`                             | Authoritative state                                                        |
| POST     | `/tasks/{uuid}/pause`, `/resume`, `/cancel` | Boundary-aware task controls                                               |
| GET      | `/approvals/pending`                        | Pending approval records                                                   |
| POST     | `/approvals/{uuid}/decision`                | `{taskId: UUID, decision, digest}`; validates task and payload binding     |
| GET      | `/tasks/{uuid}/events`                      | Named SSE events, Last-Event-ID or after cursor                            |
| GET      | `/tasks/{uuid}/events/history`              | Typed persisted event replay                                               |

Entity identifiers are UUIDs. Event IDs are ordered integer replay cursors. Every event includes timestamp, type, task/conversation IDs, a task snapshot, and an optional text delta. The stream uses event names such as `message.delta`, `approval.requested`, `approval.decided`, `tool.started`, `tool.completed`, `step.verified`, and terminal task events. The browser deduplicates event IDs and resumes automatically using EventSource Last-Event-ID. SSE disables compression to prevent proxy buffering.

The UI changes approval state after server events, never optimistically. A write decision starts execution asynchronously. A successful HTTP response alone is not proof of verified execution. Expiry/tampering/double-decisions return 409; expired approvals are persisted and emitted. Rejection ends the task and notifies the model without dispatching further proposals.

Conversation editing/deletion and persistent memory CRUD are deferred. The previous database-artifact endpoint was removed in favor of real file tools.
