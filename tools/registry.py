import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any

from apps.api.contracts import Contract, Step, Task, ToolCall
from security.policy import authorize
from tools.browser import BrowserInput, BrowserInspector, BrowserOutput
from tools.browser_sessions import (
    BrowserAction,
    BrowserSessions,
    SessionInput,
    SessionOutput,
)
from tools.filesystem import FileOutput, PathInput, Workspace, WriteInput


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: type[Contract]
    risk: str
    scopes: tuple[str, ...]
    version: str = "1"
    timeout: float = 5.0
    reversible: bool = False
    idempotent: bool = True
    output_schema: type[FileOutput] | type[BrowserOutput] | type[SessionOutput] = (
        FileOutput
    )


class ToolRegistry:
    def __init__(
        self,
        workspace: Workspace,
        browser_origins: tuple[str, ...] = (),
        browser_interaction: bool = False,
    ):
        self.workspace = workspace
        self.browser = BrowserInspector(browser_origins)
        self.sessions = BrowserSessions(browser_origins)
        self.specs = {
            "list_directory": ToolSpec(
                "list_directory",
                "List a directory inside the allowed workspace",
                PathInput,
                "low",
                ("workspace:read",),
            ),
            "read_file": ToolSpec(
                "read_file",
                "Read a UTF-8 file inside the workspace, up to 32 KB",
                PathInput,
                "low",
                ("workspace:read",),
            ),
            "write_file": ToolSpec(
                "write_file",
                "Create or overwrite a UTF-8 file inside the workspace; explicit human approval is always required",
                WriteInput,
                "high",
                ("workspace:write",),
            ),
        }
        if browser_origins:
            self.specs["inspect_page"] = ToolSpec(
                "inspect_page",
                "Read title, text and links from an allowlisted URL in a fresh browser. No JavaScript, login, clicks, typing or downloads.",
                BrowserInput,
                "low",
                ("browser:read",),
                timeout=40,
                output_schema=BrowserOutput,
            )

            if browser_interaction:
                for name, description, schema, risk in (
                    (
                        "browser_open",
                        "Open a task-owned static browser session; returns snapshotId and numbered controls. One session, ten-minute lifetime.",
                        BrowserInput,
                        "low",
                    ),
                    (
                        "browser_snapshot",
                        "Inspect an owned session and get fresh snapshotId and controls.",
                        SessionInput,
                        "low",
                    ),
                    (
                        "browser_action",
                        "Click a numbered allowlisted link or fill a text field from the latest snapshot. Always needs exact human approval. No forms, passwords, scripts or uploads.",
                        BrowserAction,
                        "high",
                    ),
                    (
                        "browser_close",
                        "Close this task's browser session.",
                        SessionInput,
                        "low",
                    ),
                ):
                    self.specs[name] = ToolSpec(
                        name,
                        description,
                        schema,
                        risk,
                        ("browser:interact",),
                        timeout=40,
                        idempotent=False,
                        output_schema=SessionOutput,
                    )

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": s.input_schema.model_json_schema(),
                },
            }
            for s in self.specs.values()
        ]

    def validate(self, call: ToolCall, task_id: str | None = None) -> Step:
        spec = self.specs.get(call.name)
        if spec is None:
            raise ValueError("Unknown tool; use only the tools in the supplied schemas")
        args = spec.input_schema.model_validate(call.arguments)
        values = args.model_dump()
        if isinstance(args, BrowserAction):
            if task_id is None:
                raise ValueError("Browser interaction requires task ownership")
            canonical, _ = self.sessions.validate_action(task_id, args)
        elif isinstance(args, SessionInput):
            if task_id is None:
                raise ValueError("Browser session requires task ownership")
            self.sessions.owned(task_id, args.sessionId)
            canonical = args.sessionId
        elif isinstance(args, BrowserInput):
            canonical = self.browser.validate(args.url)
            values["url"] = canonical
        elif isinstance(args, PathInput):
            canonical = str(self.workspace.resolve(args.path))
            values["path"] = canonical
        else:
            raise TypeError("Unsupported tool schema")
        return Step(
            title=call.name.replace("_", " ").capitalize(),
            tool=call.name,
            arguments=values,
            detail=f"{spec.risk.upper()} risk ? {canonical}",
        )

    async def execute(
        self, task: Task, step: Step
    ) -> FileOutput | BrowserOutput | SessionOutput:
        spec = self.specs.get(step.tool)
        if not spec:
            raise ValueError("Tool is not registered")
        # Revalidate canonical path and stored approval immediately before dispatch.
        self.validate(ToolCall(name=step.tool, arguments=step.arguments), task.id)
        authorize(task.id, step, task.approval)
        if step.tool == "inspect_page":
            return await self.browser.inspect(str(step.arguments["url"]))
        if step.tool == "browser_open":
            return await self.sessions.open(task.id, str(step.arguments["url"]))
        if step.tool == "browser_snapshot":
            return await self.sessions.observe(
                task.id, str(step.arguments["sessionId"])
            )
        if step.tool == "browser_action":
            return await self.sessions.act(task, step)
        if step.tool == "browser_close":
            identity = str(step.arguments["sessionId"])
            await self.sessions.close_owned(task.id, identity)
            return SessionOutput(sessionId=identity, closed=True)
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "tools.worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        payload = json.dumps(
            {
                "workspace": str(self.workspace.root),
                "task": task.model_dump(mode="json"),
            }
        ).encode()
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(payload), timeout=spec.timeout
            )
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
            await process.wait()
            raise
        data = json.loads(stdout or b"{}")
        if process.returncode:
            raise ValueError(data.get("error", "Tool process failed"))
        return spec.output_schema.model_validate(data)
