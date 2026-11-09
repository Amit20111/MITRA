from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Connection,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)
from sqlalchemy.dialects.sqlite import insert

from apps.api.contracts import (
    Conversation,
    EventType,
    Message,
    Task,
    TaskEvent,
    Trace,
    now,
)
from security.redaction import Redactor

metadata = MetaData()
conversations = Table(
    "conversations",
    metadata,
    Column("id", String, primary_key=True),
    Column("payload", JSON, nullable=False),
)
tasks = Table(
    "tasks",
    metadata,
    Column("id", String, primary_key=True),
    Column("conversation_id", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task_id", String, nullable=False, index=True),
    Column("payload", JSON, nullable=False),
)
requests = Table(
    "requests",
    metadata,
    Column("id", String, primary_key=True),
    Column("conversation_id", String, nullable=False),
    Column("content", String, nullable=False),
    Column("task_id", String, nullable=False),
)
traces = Table(
    "traces",
    metadata,
    Column("id", String, primary_key=True),
    Column("task_id", String, nullable=False, index=True),
    Column("step_id", String),
    Column("payload", JSON, nullable=False),
)
runtime_pairings = Table(
    "runtime_pairings",
    metadata,
    Column("id", String, primary_key=True),
    Column("code_hash", String, nullable=False),
    Column("expires", Float, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("consumed", Boolean, nullable=False),
)
runtime_devices = Table(
    "runtime_devices",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String, nullable=False),
    Column("expires", Float, nullable=False),
    Column("revoked", Boolean, nullable=False),
    Column("last_seen", Float, nullable=True),
    Column("boot_id", String, nullable=True),
    Column("disconnected", Boolean, nullable=False),
)
runtime_audit = Table(
    "runtime_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event", String, nullable=False),
    Column("runtime_id", String, nullable=True),
    Column("timestamp", String, nullable=False),
)


memory_records = Table(
    "memory_records",
    metadata,
    Column("id", String, primary_key=True),
    Column("payload", JSON, nullable=False),
)


class Store:
    def __init__(self, path: Path, redactor: Redactor | None = None):
        self.redactor = redactor or Redactor()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            "sqlite:///" + path.resolve().as_posix(),
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        config = AlembicConfig()
        config.set_main_option(
            "script_location",
            str(Path(__file__).resolve().parents[1] / "apps/api/migrations"),
        )
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with self.engine.connect() as db:
            db.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def conversation(self, db: Connection, identity: str) -> Conversation:
        data = db.execute(
            select(conversations.c.payload).where(conversations.c.id == identity)
        ).scalar_one_or_none()
        if data is None:
            raise LookupError("Conversation not found")
        return Conversation.model_validate(data)

    def task(self, db: Connection, identity: str) -> Task:
        data = db.execute(
            select(tasks.c.payload).where(tasks.c.id == identity)
        ).scalar_one_or_none()
        if data is None:
            raise LookupError("Task not found")
        return Task.model_validate(data)

    def save_conversation(self, db: Connection, conversation: Conversation) -> None:
        statement = insert(conversations).values(
            id=conversation.id, payload=conversation.model_dump(mode="json")
        )
        db.execute(
            statement.on_conflict_do_update(
                index_elements=[conversations.c.id],
                set_={"payload": statement.excluded.payload},
            )
        )

    def save_task(
        self,
        db: Connection,
        task: Task,
        event_type: EventType,
        delta: str | None = None,
    ) -> None:
        statement = insert(tasks).values(
            id=task.id,
            conversation_id=task.conversationId,
            payload=task.model_dump(mode="json"),
        )
        db.execute(
            statement.on_conflict_do_update(
                index_elements=[tasks.c.id],
                set_={"payload": statement.excluded.payload},
            )
        )
        conversation = self.conversation(db, task.conversationId)
        if conversation.task is None or conversation.task.id == task.id:
            conversation.task = task
            if task.draft is not None:
                message = next(
                    (m for m in conversation.messages if m.id == task.messageId), None
                )
                if message:
                    message.content = task.draft
                else:
                    conversation.messages.append(
                        Message(id=task.messageId, role="assistant", content=task.draft)
                    )
            self.save_conversation(db, conversation)
        payload = {
            "type": event_type,
            "taskId": task.id,
            "conversationId": task.conversationId,
            "timestamp": now(),
            "payload": task.model_dump(mode="json"),
            "delta": delta,
        }
        safe_payload = self.redactor.clean(payload)
        # Consent must show the exact proposed write. Tool observations and traces
        # stay redacted; execution arguments are already private task state.
        if task.approval:
            for index, step in enumerate(task.steps):
                if step.id == task.approval.stepId and step.tool in (
                    "write_file",
                    "browser_action",
                ):
                    safe_payload["payload"]["steps"][index]["arguments"] = (
                        step.arguments
                    )
        db.execute(insert(events).values(task_id=task.id, payload=safe_payload))

    def event_rows(self, identity: str, after: int) -> list[TaskEvent]:
        with self.engine.connect() as db:
            rows = db.execute(
                select(events)
                .where(events.c.task_id == identity, events.c.id > after)
                .order_by(events.c.id)
            ).mappings()
            return [
                TaskEvent.model_validate({**row["payload"], "id": row["id"]})
                for row in rows
            ]

    def trace(self, db: Connection, trace: Trace) -> None:
        db.execute(
            insert(traces).values(
                id=trace.id,
                task_id=trace.taskId,
                step_id=trace.stepId,
                payload=self.redactor.clean(trace.model_dump(mode="json")),
            )
        )

    def trace_rows(self) -> list[dict[str, Any]]:
        with self.engine.connect() as db:
            return [
                self.redactor.clean(item)
                for item in db.execute(select(traces.c.payload)).scalars()
            ]

    def recover(self) -> None:
        with self.transaction() as db:
            for data in db.execute(select(tasks.c.payload)).scalars().all():
                task = Task.model_validate(data)
                browser_lost = any(
                    step.tool.startswith("browser_") for step in task.steps
                ) and task.status not in (
                    "completed",
                    "failed",
                    "cancelled",
                    "needs_user_input",
                )
                if browser_lost and task.approval and task.approval.status == "pending":
                    task.approval.status = "expired"
                if (
                    browser_lost
                    or task.status in ("queued", "planning", "running", "verifying")
                    or (
                        task.status == "paused"
                        and task.resumeState != "awaiting_approval"
                    )
                ):
                    task.status = "failed"
                    task.summary = (
                        "Browser session was lost after a service restart; its approval is invalid. Start a new task. Actions are never replayed."
                        if browser_lost
                        else "Execution was interrupted by a service restart. Inspect any attempted file write before starting a new task; actions are never replayed automatically."
                    )
                    self.save_task(db, task, "task.failed")

    def close(self) -> None:
        self.engine.dispose()
