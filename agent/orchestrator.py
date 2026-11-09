import asyncio
import json
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import insert, select

from agent.context import build_context
from agent.state import TERMINAL, transition
from apps.api.config import Config
from apps.api.contracts import (
    Approval,
    Conversation,
    Decision,
    Message,
    Step,
    Task,
    ToolEvent,
    Trace,
)
from memory.records import MemoryService
from memory.store import Store, requests
from models.providers import Provider
from security.policy import GATED_TOOLS, action_digest
from tools.browser_sessions import BrowserAction
from tools.filesystem import Workspace
from tools.registry import ToolRegistry


class Orchestrator:
    def __init__(self, store: Store, provider: Provider, config: Config):
        self.store, self.provider, self.config = store, provider, config
        self.registry = ToolRegistry(
            Workspace(config.workspace),
            config.browser_origins,
            config.browser_interaction,
        )
        self.jobs: dict[str, asyncio.Task[None]] = {}

    def launch(self, identity: str) -> None:
        if identity in self.jobs and not self.jobs[identity].done():
            return
        job = asyncio.create_task(self.run(identity))
        self.jobs[identity] = job

        def remove(done: asyncio.Task[None]) -> None:
            if self.jobs.get(identity) is done:
                self.jobs.pop(identity, None)

        job.add_done_callback(remove)

    def submit(
        self, conversation_id: str, content: str, request_id: str
    ) -> Conversation:
        content = content.strip()
        if not content:
            raise ValueError("A message cannot be blank")
        with self.store.transaction() as db:
            conversation = self.store.conversation(db, conversation_id)
            previous = (
                db.execute(select(requests).where(requests.c.id == request_id))
                .mappings()
                .first()
            )
            if previous:
                if (
                    previous["conversation_id"] != conversation_id
                    or previous["content"] != content
                ):
                    raise ValueError("Request ID already belongs to another message")
                conversation.task = self.store.task(db, previous["task_id"])
                return conversation
            if conversation.task and conversation.task.status not in TERMINAL:
                raise ValueError(
                    "Finish or cancel the current task before starting another"
                )
            task = Task(
                conversationId=conversation_id,
                title=content[:100],
                provider=self.provider.name,
                model=self.provider.model,
                outline=[
                    "Understand the request",
                    "Choose the next safe step",
                    "Verify and report",
                ],
            )
            conversation.messages.append(
                Message(id=request_id, role="user", content=content)
            )
            if conversation.title == "New conversation":
                conversation.title = content[:45]
            conversation.task = task
            self.store.save_conversation(db, conversation)
            self.store.save_task(db, task, "task.created")
            db.execute(
                insert(requests).values(
                    id=request_id,
                    conversation_id=conversation_id,
                    content=content,
                    task_id=task.id,
                )
            )
        self.launch(task.id)
        return conversation

    def snapshot(self, identity: str) -> Task:
        with self.store.transaction() as db:
            return self.store.task(db, identity)

    def fail(self, identity: str, summary: str) -> None:
        with self.store.transaction() as db:
            task = self.store.task(db, identity)
            if task.status in TERMINAL or task.status == "paused":
                return
            transition(task, "failed")
            task.summary = summary
            self.store.save_task(db, task, "task.failed")

    async def run(self, identity: str) -> None:
        try:
            task = self.snapshot(identity)
            if task.status == "running" and not await self.execute(identity):
                return
            while True:
                with self.store.transaction() as db:
                    task = self.store.task(db, identity)
                    if task.status in TERMINAL or task.status in (
                        "paused",
                        "awaiting_approval",
                    ):
                        return
                    if task.status == "queued":
                        transition(task, "planning")
                    if task.iterations >= self.config.max_steps:
                        transition(task, "failed")
                        task.summary = "Task reached its step budget. Review the recorded results before continuing in a new request."
                        self.store.save_task(db, task, "task.failed")
                        return
                    task.iterations += 1
                    task.draft = ""
                    self.store.save_task(db, task, "plan.created")
                    conversation = self.store.conversation(db, task.conversationId)
                messages = build_context(
                    conversation,
                    task,
                    MemoryService(self.store).retrieve(
                        next(
                            (
                                m.content
                                for m in reversed(conversation.messages)
                                if m.role == "user"
                            ),
                            task.title,
                        ),
                        conversation.id,
                    ),
                )
                validated: Step | None = None
                response = None
                for attempt in range(self.config.retries + 1):
                    started = time.monotonic()

                    async def delta(text: str) -> None:
                        with self.store.transaction() as db:
                            live = self.store.task(db, identity)
                            if live.status != "planning":
                                return
                            live.draft = (live.draft or "") + text
                            self.store.save_task(db, live, "message.delta", text)

                    try:
                        response = await self.provider.generate(
                            messages, self.registry.schemas(), {}, delta
                        )
                    except asyncio.CancelledError:
                        with self.store.transaction() as db:
                            self.store.trace(
                                db,
                                Trace(
                                    taskId=identity,
                                    kind="model",
                                    request={
                                        "messages": messages,
                                        "tools": self.registry.schemas(),
                                    },
                                    outcome="interrupted",
                                    durationMs=(time.monotonic() - started) * 1000,
                                    validationErrors=[
                                        "Generation interrupted before a complete response was available"
                                    ],
                                ),
                            )
                        raise
                    errors: list[str] = []
                    if response.kind == "tool":
                        try:
                            if response.tool_call is None:
                                raise ValueError("Missing tool call")
                            validated = self.registry.validate(
                                response.tool_call, identity
                            )
                        except ValueError as error:
                            errors.append(str(error))
                    elif response.kind == "invalid":
                        errors.append(response.error or "Invalid model response")
                    with self.store.transaction() as db:
                        self.store.trace(
                            db,
                            Trace(
                                taskId=identity,
                                stepId=validated.id if validated else None,
                                kind="model",
                                request={
                                    "messages": messages,
                                    "tools": self.registry.schemas(),
                                    "options": {
                                        "thinking": self.config.thinking,
                                        "model": self.provider.model,
                                    },
                                },
                                rawResponse=response.raw,
                                parsed=validated.model_dump(mode="json")
                                if validated
                                else response.model_dump(exclude={"raw"}),
                                validationErrors=errors,
                                durationMs=(time.monotonic() - started) * 1000,
                                usage=response.usage,
                                outcome="invalid" if errors else response.kind,
                            ),
                        )
                    if self.snapshot(identity).status != "planning":
                        return
                    if not errors:
                        break
                    if attempt == self.config.retries:
                        with self.store.transaction() as db:
                            invalid_task = self.store.task(db, identity)
                            invalid_task.steps.append(
                                Step(
                                    title="Validate proposed action",
                                    tool="model.validation",
                                    status="failed",
                                    detail="Proposal rejected; no tool dispatched",
                                    result={"validationErrors": errors},
                                )
                            )
                            self.store.save_task(
                                db, invalid_task, "task.status_changed"
                            )
                        self.fail(
                            identity,
                            "Tool proposal failed validation after the permitted retry: "
                            + errors[0],
                        )
                        return
                    messages.append(
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "validation_error": errors,
                                    "instruction": "Return one corrected tool call or an honest final answer.",
                                }
                            ),
                        }
                    )
                assert response is not None
                if response.kind == "error":
                    self.fail(identity, response.error or "Provider failed")
                    return
                if response.kind in ("final", "clarification"):
                    with self.store.transaction() as db:
                        task = self.store.task(db, identity)
                        if task.status != "planning":
                            return
                        task.draft = response.text
                        task.summary = response.text
                        transition(
                            task,
                            "needs_user_input"
                            if response.kind == "clarification"
                            else "completed",
                        )
                        task.outline = [
                            s.title + ": " + s.status for s in task.steps
                        ] + [
                            "Awaiting your clarification"
                            if response.kind == "clarification"
                            else "Response complete"
                        ]
                        self.store.save_task(
                            db,
                            task,
                            "task.completed"
                            if response.kind == "final"
                            else "task.status_changed",
                        )
                    return
                assert validated is not None
                with self.store.transaction() as db:
                    task = self.store.task(db, identity)
                    if task.status != "planning":
                        return
                    task.steps.append(validated)
                    task.outline = [s.title + ": " + s.status for s in task.steps] + [
                        "Choose the next step after observation"
                    ]
                    if validated.tool in GATED_TOOLS:
                        target = str(validated.arguments.get("path", ""))
                        action = "Create or overwrite this file with the exact content shown below."
                        if validated.tool == "browser_action":
                            args = BrowserAction.model_validate(validated.arguments)
                            target, label = self.registry.sessions.validate_action(
                                task.id, args
                            )
                            action = f"{args.action.capitalize()} browser element {args.elementId} ({label}). Review the exact action, value, and snapshot below. Form submission is blocked."
                        task.approval = Approval(
                            taskId=task.id,
                            stepId=validated.id,
                            target=target,
                            action=action,
                            expiresAt=(
                                datetime.now(UTC)
                                + timedelta(seconds=self.config.approval_seconds)
                            ).isoformat(),
                            digest=action_digest(validated.tool, validated.arguments),
                        )
                        transition(task, "awaiting_approval")
                        self.store.save_task(db, task, "approval.requested")
                        return
                    transition(task, "running")
                    self.store.save_task(db, task, "step.started")
                if not await self.execute(identity):
                    return
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - contain unexpected runtime faults without disclosing secrets
            self.fail(
                identity,
                f"Task failed ({type(error).__name__}). Inspect the trace and any attempted write before retrying.",
            )

        finally:
            with self.store.transaction() as db:
                finished = self.store.task(db, identity).status in TERMINAL
            if finished:
                await self.registry.sessions.close_owned(identity)

    async def execute(self, identity: str) -> bool:
        started = time.monotonic()
        with self.store.transaction() as db:
            task = self.store.task(db, identity)
            if task.status != "running":
                return False
            step = task.steps[-1]
            step.status = "attempted"
            self.store.save_task(db, task, "tool.started")
        try:
            result = await self.registry.execute(task, step)
        except asyncio.CancelledError:
            with self.store.transaction() as db:
                self.store.trace(
                    db,
                    Trace(
                        taskId=identity,
                        stepId=step.id,
                        kind="tool",
                        request={"tool": step.tool, "arguments": step.arguments},
                        approvalState=task.approval.status if task.approval else None,
                        outcome="interrupted",
                        durationMs=(time.monotonic() - started) * 1000,
                        verification="Not verified; inspect target before retrying",
                    ),
                )
            raise
        except (ValueError, OSError, TimeoutError) as error:
            with self.store.transaction() as db:
                task = self.store.task(db, identity)
                step = task.steps[-1]
                step.status = "failed"
                step.result = {"error": str(error)}
                task.events.append(
                    ToolEvent(
                        tool=step.tool,
                        input=json.dumps(self.store.redactor.clean(step.arguments)),
                        output=str(self.store.redactor.clean(str(error))),
                        status="failed",
                    )
                )
                self.store.trace(
                    db,
                    Trace(
                        taskId=identity,
                        stepId=step.id,
                        kind="tool",
                        request={"tool": step.tool, "arguments": step.arguments},
                        approvalState=task.approval.status if task.approval else None,
                        outcome="failed",
                        validationErrors=[str(error)],
                        durationMs=(time.monotonic() - started) * 1000,
                    ),
                )
                if task.status == "running":
                    transition(task, "failed")
                task.summary = "Tool failed; no success is claimed. Inspect any attempted file write before retrying."
                self.store.save_task(db, task, "tool.failed")
                self.store.save_task(db, task, "task.failed")
            return False
        with self.store.transaction() as db:
            task = self.store.task(db, identity)
            if task.status != "running":
                return False
            step = task.steps[-1]
            step.status, step.result = "succeeded", result.model_dump()
            self.store.save_task(db, task, "tool.completed")
            transition(task, "verifying")
            self.store.save_task(db, task, "task.status_changed")
            step.verification = (
                "Verified by read-back hash"
                if step.tool == "write_file"
                else "Verified browser control outcome; no form submitted"
                if step.tool.startswith("browser_")
                else "Verified read-only page observation; page claims are untrusted"
                if step.tool == "inspect_page"
                else "Verified bounded filesystem observation"
            )
            step.status = "verified"
            task.events.append(
                ToolEvent(
                    tool=step.tool,
                    input=json.dumps(self.store.redactor.clean(step.arguments)),
                    output=json.dumps(self.store.redactor.clean(step.result)),
                    status="verified",
                )
            )
            self.store.trace(
                db,
                Trace(
                    taskId=identity,
                    stepId=step.id,
                    kind="tool",
                    request={"tool": step.tool, "arguments": step.arguments},
                    rawResponse=step.result,
                    parsed=step.result,
                    approvalState=task.approval.status if task.approval else None,
                    outcome="verified",
                    verification=step.verification,
                    durationMs=(time.monotonic() - started) * 1000,
                ),
            )
            self.store.save_task(db, task, "step.verified")
            transition(task, "planning")
            self.store.save_task(db, task, "task.status_changed")
        return True

    async def decide(self, approval_id: str, decision: Decision) -> Task:
        expired = False
        with self.store.transaction() as db:
            task = self.store.task(db, str(decision.taskId))
            approval = task.approval
            if (
                task.status != "awaiting_approval"
                or approval is None
                or approval.id != approval_id
                or approval.status != "pending"
            ):
                raise ValueError("This approval is not pending for this task")
            step = task.steps[-1]
            if approval.digest != decision.digest or approval.digest != action_digest(
                step.tool, step.arguments
            ):
                raise ValueError("Proposed arguments changed; this approval is invalid")
            expired = datetime.fromisoformat(approval.expiresAt) <= datetime.now(UTC)
            approval.status = (
                "expired"
                if expired
                else "approved"
                if decision.decision == "approve"
                else "rejected"
            )
            if expired:
                transition(task, "failed")
                task.summary = "Approval expired. No tool was dispatched. Send a new request to propose a new action."
            elif decision.decision == "reject":
                step.result = {
                    "error": "The user denied this action. Do not execute or retry it."
                }
                transition(task, "cancelled")
                task.summary = "Action declined. This action was not executed. Earlier verified steps remain recorded."
            else:
                transition(task, "running")
            self.store.trace(
                db,
                Trace(
                    taskId=task.id,
                    stepId=step.id,
                    kind="approval",
                    request=decision.model_dump(mode="json"),
                    approvalState=approval.status,
                    outcome=approval.status,
                ),
            )
            self.store.save_task(db, task, "approval.decided")
        if expired:
            await self.registry.sessions.close_owned(task.id)
            raise ValueError("Approval expired")
        if decision.decision == "approve":
            self.launch(task.id)
        else:
            await self.registry.sessions.close_owned(task.id)
            job = asyncio.create_task(self.notify_denial(task))
            self.jobs[task.id + "-denial"] = job
            job.add_done_callback(lambda _: self.jobs.pop(task.id + "-denial", None))
        return task

    async def notify_denial(self, task: Task) -> None:
        with self.store.transaction() as db:
            conversation = self.store.conversation(db, task.conversationId)
        messages = build_context(
            conversation,
            task,
            MemoryService(self.store).retrieve(
                next(
                    (
                        m.content
                        for m in reversed(conversation.messages)
                        if m.role == "user"
                    ),
                    task.title,
                ),
                conversation.id,
            ),
        )
        messages.append(
            {
                "role": "user",
                "content": "The user denied the action. End this task. No further tools may execute.",
            }
        )
        # Notify the model; tool proposals from this response are never dispatched.
        result = await self.provider.generate(messages, [], {"denied": True})
        with self.store.transaction() as db:
            self.store.trace(
                db,
                Trace(
                    taskId=task.id,
                    stepId=task.steps[-1].id,
                    kind="model",
                    request={"messages": messages, "tools": []},
                    rawResponse=result.raw,
                    parsed=result.model_dump(exclude={"raw"}),
                    usage=result.usage,
                    outcome="denial_notified",
                ),
            )

    async def control(self, identity: str, action: str) -> Task:
        with self.store.transaction() as db:
            task = self.store.task(db, identity)
            if action == "resume":
                if task.status != "paused" or task.resumeState is None:
                    raise ValueError("Only paused tasks can resume")
                if task.resumeState in ("running", "verifying"):
                    raise ValueError(
                        "Interrupted execution cannot be resumed; inspect the target and cancel this task"
                    )
                transition(task, task.resumeState)
                task.resumeState = None
            elif action == "pause":
                if task.status not in ("queued", "planning", "awaiting_approval"):
                    raise ValueError(
                        "Pause is available at planning or approval boundaries"
                    )
                task.resumeState = task.status
                transition(task, "paused")
            elif action == "cancel":
                transition(task, "cancelled")
                task.summary = "Task cancelled. Inspect any attempted write; completed steps are not undone."
                if task.approval and task.approval.status == "pending":
                    task.approval.status = "rejected"
            else:
                raise ValueError("Unknown task action")
            self.store.save_task(
                db,
                task,
                "task.cancelled" if action == "cancel" else "task.status_changed",
            )
        job = self.jobs.get(identity)
        if action != "resume" and job and not job.done():
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
        if action == "cancel":
            await self.registry.sessions.close_owned(identity)
        if action == "resume" and task.status != "awaiting_approval":
            self.launch(identity)
        return task

    async def close(self) -> None:
        jobs = list(self.jobs.values())
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await self.registry.sessions.stop()
