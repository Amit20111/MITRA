"""Task-owned, bounded browser sessions; interaction always requires stored consent."""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field

from apps.api.contracts import Contract, Step, Task
from security.policy import authorize
from tools.browser import BrowserInspector, stop_browser_process


class SessionInput(Contract):
    sessionId: str = Field(pattern=r"^[0-9a-f-]{36}$")


class BrowserAction(SessionInput):
    snapshotId: str = Field(pattern=r"^[0-9a-f]{64}$")
    elementId: str = Field(pattern=r"^e[0-9]{1,2}$")
    action: Literal["click", "fill"]
    value: str = Field(default="", max_length=2000)


class Control(Contract):
    ref: str
    kind: Literal["link", "text"]
    label: str
    href: str
    value: str


class SessionOutput(Contract):
    sessionId: str
    snapshotId: str = ""
    fingerprint: str = ""
    url: str = ""
    title: str = ""
    text: str = ""
    controls: list[Control] = Field(default_factory=list)
    verified: bool = True
    closed: bool = False


@dataclass
class Session:
    owner: str
    identity: str
    process: asyncio.subprocess.Process
    expires: float
    latest: SessionOutput | None = None


class BrowserSessions:
    def __init__(self, origins: tuple[str, ...]):
        self.inspector = BrowserInspector(origins)
        self.session: Session | None = None
        self.lock = asyncio.Lock()

    def owned(self, owner: str, identity: str) -> Session:
        session = self.session
        if (
            session is None
            or session.owner != owner
            or session.identity != identity
            or session.expires <= time.monotonic()
            or session.process.returncode is not None
        ):
            raise ValueError(
                "Browser session is absent, expired or belongs to another task"
            )
        return session

    def validate_action(self, owner: str, args: BrowserAction) -> tuple[str, str]:
        session = self.owned(owner, args.sessionId)
        observation = session.latest
        if observation is None or observation.snapshotId != args.snapshotId:
            raise ValueError(
                "Browser snapshot changed; inspect again before proposing an action"
            )
        control = next(
            (item for item in observation.controls if item.ref == args.elementId), None
        )
        if (
            control is None
            or (args.action == "click" and (control.kind != "link" or args.value))
            or (args.action == "fill" and control.kind != "text")
        ):
            raise ValueError("Unsupported browser control or action")
        detail = control.label + (
            f" -> {control.href}" if control.kind == "link" else ""
        )
        return observation.url, detail

    async def exchange(
        self, session: Session, message: dict[str, object]
    ) -> SessionOutput:
        process = session.process
        assert process.stdin is not None and process.stdout is not None
        try:
            process.stdin.write(
                (json.dumps(message, ensure_ascii=False) + "\n").encode()
            )
            await process.stdin.drain()
            line = await asyncio.wait_for(process.stdout.readline(), 40)
            data = json.loads(line or b"{}")
            if "result" not in data:
                raise ValueError(
                    "Browser action refused or failed; session invalidated"
                )
            result = SessionOutput.model_validate(data["result"])
            session.latest = result
            return result
        except (Exception, asyncio.CancelledError):
            await self.stop()
            raise

    async def open(self, owner: str, url: str) -> SessionOutput:
        url = self.inspector.validate(url)
        async with self.lock:
            if self.session:
                if (
                    self.session.expires <= time.monotonic()
                    or self.session.process.returncode is not None
                ):
                    await self.stop()
                else:
                    raise ValueError(
                        "One browser session is already active; close it before opening another"
                    )
            process = await asyncio.create_subprocess_exec(
                "node",
                str(Path(__file__).with_name("browser_session_driver.mjs")),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=1024 * 1024,
            )
            session = Session(owner, str(uuid4()), process, time.monotonic() + 600)
            self.session = session
            return await self.exchange(
                session,
                {
                    "command": "open",
                    "owner": owner,
                    "sessionId": session.identity,
                    "origins": self.inspector.origins,
                    "url": url,
                },
            )

    async def observe(self, owner: str, identity: str) -> SessionOutput:
        async with self.lock:
            session = self.owned(owner, identity)
            return await self.exchange(
                session, {"command": "snapshot", "owner": owner, "sessionId": identity}
            )

    async def act(self, task: Task, step: Step) -> SessionOutput:
        async with self.lock:
            args = BrowserAction.model_validate(step.arguments)
            self.validate_action(task.id, args)
            authorize(task.id, step, task.approval)
            session = self.owned(task.id, args.sessionId)
            return await self.exchange(
                session,
                {
                    "command": "action",
                    "owner": task.id,
                    "sessionId": args.sessionId,
                    "args": args.model_dump(),
                    "stepId": step.id,
                    "approval": task.approval.model_dump() if task.approval else None,
                },
            )

    async def close_owned(self, owner: str, identity: str | None = None) -> None:
        async with self.lock:
            if identity:
                self.owned(owner, identity)
            if self.session and self.session.owner == owner:
                await self.stop()

    async def stop(self) -> None:
        session, self.session = self.session, None
        if session is None:
            return
        cleanup = asyncio.create_task(self.close_process(session.process))
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            # API shutdown may cancel a task already closing its session. Finish
            # draining its owned pipes before allowing the task to disappear.
            await cleanup
            raise

    @staticmethod
    async def close_process(process: asyncio.subprocess.Process) -> None:
        try:
            if process.returncode is None and process.stdin:
                process.stdin.write(b'{"command":"close"}\n')
                await process.stdin.drain()
            if process.stdin:
                process.stdin.close()
            await asyncio.wait_for(process.communicate(), 3)
        except (OSError, TimeoutError):
            await stop_browser_process(process)
            await process.communicate()
