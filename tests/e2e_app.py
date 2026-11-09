"""Test-only ASGI entry point. Never selected by production configuration."""

import os
import tempfile
from pathlib import Path

from fastapi.responses import HTMLResponse

from apps.api.main import create_app
from tests.fakes import FakeProvider, final, tool

sandbox = tempfile.TemporaryDirectory(prefix="mitra-e2e-")
root = Path(sandbox.name)
os.environ["MITRA_BROWSER_ORIGINS"] = "http://127.0.0.1:8007"
os.environ["MITRA_BROWSER_INTERACTION"] = "true"


class BrowserDemoProvider(FakeProvider):
    async def generate(self, messages, tools, options, on_delta=None):
        if any(
            "Fill browser note" in str(message.get("content", ""))
            for message in messages
        ) and not options.get("denied"):
            session = app.state.agent.registry.sessions.session
            if session is None:
                response = tool(
                    "browser_open", url="http://127.0.0.1:8007/browser-fixture"
                )
            elif session.latest.controls[0].value == "":
                response = tool(
                    "browser_action",
                    sessionId=session.identity,
                    snapshotId=session.latest.snapshotId,
                    elementId=session.latest.controls[0].ref,
                    action="fill",
                    value="Verified browser value",
                )
            else:
                response = final(
                    "The browser field was verified. No form was submitted."
                )
            return await FakeProvider([response]).generate(
                messages, tools, options, on_delta
            )
        return await super().generate(messages, tools, options, on_delta)


app = create_app(
    root / "db.sqlite",
    BrowserDemoProvider(
        [
            tool(
                "write_file",
                path="approved.txt",
                content="Verified by the browser test",
            ),
            final("The file was written and verified."),
        ]
    ),
    root / "workspace",
)


@app.get("/browser-fixture", response_class=HTMLResponse)
def browser_fixture():
    return '<html><title>Browser fixture</title><body><label>Note<input name="note"></label></body></html>'
