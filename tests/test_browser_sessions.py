import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.contracts import Approval, Task, ToolCall
from apps.api.main import create_app
from security.policy import action_digest
from tests.fakes import FakeProvider, final, tool
from tests.test_workflow import decide, submit, wait_for
from tools.browser_sessions import BrowserAction
from tools.filesystem import Workspace
from tools.registry import ToolRegistry


@pytest.fixture
def interaction_site():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            requests.append(self.path)
            body = (
                b"<html><title>Next page</title><body>Navigation verified</body></html>"
                if self.path == "/next"
                else b"""<html><title>Interaction fixture</title><body>
            <label>Note<input name="note"></label><input type="password" aria-label="Password">
            <input type="file"><input name="secret" aria-label="Secret">
            <a href="/next">Next page</a><a href="http://127.0.0.1:1/denied">Outside</a>
            <form method="post" action="/submit"><button>Submit</button></form>
            <script>fetch('/side-effect')</script></body></html>"""
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            requests.append("POST:" + self.path)
            self.send_response(500)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()
    server.server_close()
    thread.join()


def new_task():
    return Task(
        conversationId=str(uuid4()), title="Browse", provider="test", model="test"
    )


def approve(task, step):
    task.steps.append(step)
    task.approval = Approval(
        taskId=task.id,
        stepId=step.id,
        target="fixture",
        action="test",
        status="approved",
        digest=action_digest(step.tool, step.arguments),
        expiresAt=(datetime.now(UTC) + timedelta(minutes=2)).isoformat(),
    )


def proposal(registry, task, observed, action, value=""):
    control = next(
        item
        for item in observed.controls
        if item.kind == ("text" if action == "fill" else "link")
    )
    return registry.validate(
        ToolCall(
            name="browser_action",
            arguments={
                "sessionId": observed.sessionId,
                "snapshotId": observed.snapshotId,
                "elementId": control.ref,
                "action": action,
                "value": value,
            },
        ),
        task.id,
    )


def test_real_session_approval_fill_click_and_isolation(interaction_site, tmp_path):
    origin, requests = interaction_site

    async def run():
        registry = ToolRegistry(Workspace(tmp_path), (origin,), True)
        task = new_task()
        try:
            observation = await registry.sessions.open(task.id, origin)
            assert [item.label for item in observation.controls] == [
                "Note",
                "Next page",
            ]
            with pytest.raises(ValueError):
                registry.sessions.owned(new_task().id, observation.sessionId)
            with pytest.raises(ValueError):
                await registry.sessions.open(new_task().id, origin)
            step = proposal(registry, task, observation, "fill", "Approved note")
            with pytest.raises(ValueError, match="approval"):
                await registry.execute(task, step)
            approve(task, step)
            step.arguments["value"] = "Tampered"
            with pytest.raises(ValueError, match="changed"):
                await registry.execute(task, step)
            step.arguments["value"] = "Approved note"
            filled = await registry.execute(task, step)
            assert filled.controls[0].value == "Approved note"
            with pytest.raises(ValueError, match="snapshot"):
                await registry.execute(task, step)
            navigation = proposal(registry, task, filled, "click")
            approve(task, navigation)
            navigated = await registry.execute(task, navigation)
            assert navigated.url == origin + "/next"
            assert "Navigation verified" in navigated.text
            await registry.sessions.close_owned(task.id, observation.sessionId)
            assert registry.sessions.session is None
        finally:
            await registry.sessions.stop()

    asyncio.run(run())
    assert requests == ["/", "/next"]


@pytest.mark.parametrize(
    "case", ["expired", "rejected", "wrong_task", "stale", "expired_session"]
)
def test_browser_action_refuses_invalid_authority(interaction_site, tmp_path, case):
    origin, requests = interaction_site

    async def run():
        registry = ToolRegistry(Workspace(tmp_path), (origin,), True)
        task = new_task()
        try:
            observation = await registry.sessions.open(task.id, origin)
            step = proposal(registry, task, observation, "click")
            approve(task, step)
            if case == "expired":
                task.approval.expiresAt = (
                    datetime.now(UTC) - timedelta(seconds=1)
                ).isoformat()
            elif case == "rejected":
                task.approval.status = "rejected"
            elif case == "wrong_task":
                task.approval.taskId = str(uuid4())
            elif case == "stale":
                await registry.sessions.observe(task.id, observation.sessionId)
            else:
                registry.sessions.session.expires = time.monotonic() - 1
            with pytest.raises(ValueError):
                await registry.execute(task, step)
        finally:
            await registry.sessions.stop()

    asyncio.run(run())
    assert requests == ["/"]


class SessionProvider(FakeProvider):
    def __init__(self, origin):
        super().__init__([])
        self.origin = origin
        self.registry = None
        self.stage = 0

    async def generate(self, messages, tools, options, on_delta=None):
        if not options.get("denied"):
            if self.stage == 0:
                response = tool("browser_open", url=self.origin)
            elif self.stage == 1:
                state = self.registry.sessions.session.latest
                control = next(item for item in state.controls if item.kind == "text")
                response = tool(
                    "browser_action",
                    sessionId=state.sessionId,
                    snapshotId=state.snapshotId,
                    elementId=control.ref,
                    action="fill",
                    value="Approved browser text",
                )
            else:
                response = final(
                    "The field was filled and verified. No form was submitted."
                )
            self.responses.append(response)
            self.stage += 1
        return await super().generate(messages, tools, options, on_delta)


@pytest.mark.parametrize("decision", ["approve", "reject", "cancel"])
def test_session_agent_approval_and_cleanup(
    interaction_site, tmp_path, monkeypatch, decision
):
    origin, _ = interaction_site
    monkeypatch.setenv("MITRA_BROWSER_ORIGINS", origin)
    monkeypatch.setenv("MITRA_BROWSER_INTERACTION", "true")
    provider = SessionProvider(origin)
    with TestClient(
        create_app(tmp_path / "db.sqlite", provider, tmp_path / "workspace")
    ) as client:
        provider.registry = client.app.state.agent.registry
        task = wait_for(client, submit(client, "Fill the fixture note field")["id"])
        session = provider.registry.sessions.session
        assert session.latest.controls[0].value == ""
        assert task["steps"][-1]["tool"] == "browser_action"
        assert "Form submission is blocked" in task["approval"]["action"]
        if decision == "cancel":
            assert client.post(f"/api/v1/tasks/{task['id']}/cancel").status_code == 200
        else:
            assert decide(client, task, decision).status_code == 200
            finished = wait_for(
                client,
                task["id"],
                "completed" if decision == "approve" else "cancelled",
            )
            if decision == "approve":
                assert (
                    finished["steps"][-1]["result"]["controls"][0]["value"]
                    == "Approved browser text"
                )
        for _ in range(100):
            if provider.registry.sessions.session is None:
                break
            time.sleep(0.02)
        assert provider.registry.sessions.session is None


def test_interaction_not_exposed_without_opt_in(tmp_path):
    registry = ToolRegistry(Workspace(tmp_path), ("https://example.com",))
    assert "inspect_page" in registry.specs
    assert "browser_action" not in registry.specs
    with pytest.raises(ValueError):
        BrowserAction(
            sessionId=str(uuid4()), snapshotId="a" * 64, elementId="e0", action="submit"
        )


@pytest.mark.parametrize("mode", ["bad_digest", "stale_snapshot"])
def test_browser_worker_independently_rechecks_approval(
    interaction_site, tmp_path, mode
):
    origin, requests = interaction_site

    async def run():
        registry = ToolRegistry(Workspace(tmp_path), (origin,), True)
        task = new_task()
        try:
            observed = await registry.sessions.open(task.id, origin)
            step = proposal(registry, task, observed, "click")
            approve(task, step)
            if mode == "bad_digest":
                task.approval.digest = "0" * 64
            else:
                await registry.sessions.observe(task.id, observed.sessionId)
            # Bypass Python authorization deliberately to test the worker boundary.
            with pytest.raises(ValueError):
                await registry.sessions.exchange(
                    registry.sessions.session,
                    {
                        "command": "action",
                        "owner": task.id,
                        "sessionId": observed.sessionId,
                        "args": step.arguments,
                        "stepId": step.id,
                        "approval": task.approval.model_dump(),
                    },
                )
            assert registry.sessions.session is None
        finally:
            await registry.sessions.stop()

    asyncio.run(run())
    assert requests == ["/"]


def test_restart_invalidates_browser_approval(interaction_site, tmp_path, monkeypatch):
    origin, _ = interaction_site
    monkeypatch.setenv("MITRA_BROWSER_ORIGINS", origin)
    monkeypatch.setenv("MITRA_BROWSER_INTERACTION", "true")
    provider = SessionProvider(origin)
    database, workspace = tmp_path / "db.sqlite", tmp_path / "workspace"
    with TestClient(create_app(database, provider, workspace)) as client:
        provider.registry = client.app.state.agent.registry
        task = wait_for(client, submit(client, "Fill fixture note")["id"])
    with TestClient(create_app(database, FakeProvider([]), workspace)) as client:
        recovered = client.get(f"/api/v1/tasks/{task['id']}").json()
        assert recovered["status"] == "failed"
        assert recovered["approval"]["status"] == "expired"
        assert decide(client, task).status_code == 409
