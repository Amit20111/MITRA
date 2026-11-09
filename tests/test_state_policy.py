import asyncio
import os
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agent.state import TRANSITIONS, transition
from apps.api.contracts import Approval, Task, ToolCall
from security.policy import action_digest
from security.redaction import Redactor
from tools.filesystem import Workspace, WriteInput
from tools.registry import ToolRegistry


@pytest.mark.parametrize("source", list(TRANSITIONS))
@pytest.mark.parametrize("target", list(TRANSITIONS))
def test_every_state_transition(source, target):
    task = Task(
        conversationId=str(uuid4()),
        title="test",
        status=source,
        provider="test",
        model="test",
    )
    if target in TRANSITIONS[source]:
        transition(task, target)
        assert task.status == target
    else:
        with pytest.raises(ValueError, match="Illegal"):
            transition(task, target)


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "sub/../../secret",
        "sub/../note",
        "..\\secret",
        "/etc/passwd",
        "C:/Windows/system.ini",
        "file:stream",
    ],
)
def test_traversal(tmp_path, path):
    workspace = Workspace(tmp_path / "workspace")
    with pytest.raises(ValueError):
        workspace.resolve(path)


def test_symlink_escape(tmp_path):
    root = tmp_path / "workspace"
    workspace = Workspace(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(root / "link"), str(outside)],
            check=True,
            capture_output=True,
        )
    with pytest.raises(ValueError):
        workspace.resolve("link/secret.txt")


def test_dispatcher_checks_approval_expiry_and_arguments(tmp_path):
    registry = ToolRegistry(Workspace(tmp_path))
    step = registry.validate(
        ToolCall(name="write_file", arguments={"path": "note.txt", "content": "hello"})
    )
    task = Task(
        conversationId=str(uuid4()),
        title="test",
        provider="test",
        model="test",
        status="running",
        steps=[step],
    )
    with pytest.raises(ValueError, match="approval"):
        asyncio.run(registry.execute(task, step))
    task.approval = Approval(
        taskId=task.id,
        stepId=step.id,
        target="note.txt",
        action="write",
        status="approved",
        expiresAt=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        digest=action_digest(step.tool, step.arguments),
    )
    with pytest.raises(ValueError, match="expired"):
        asyncio.run(registry.execute(task, step))
    task.approval.expiresAt = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    step.arguments["content"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        asyncio.run(registry.execute(task, step))
    assert not (tmp_path / "note.txt").exists()


def test_write_overwrites_and_verifies_hash(tmp_path):
    workspace = Workspace(tmp_path)
    (tmp_path / "note.txt").write_text("old")
    result = workspace.write_file(WriteInput(path="note.txt", content="new"))
    assert result.verified
    assert (tmp_path / "note.txt").read_text() == "new"


def test_redaction_nested_and_known_secrets():
    redactor = Redactor(["my-live-credential"])
    data = redactor.clean(
        {
            "Authorization": "Bearer abc",
            "nested": [
                {
                    "content": "password=hunter2 token=abcd my-live-credential sk-abcdefghijkl"
                }
            ],
            "messages": [{"content": "Bearer abc.def"}],
        }
    )
    text = str(data)
    for secret in ("hunter2", "abcd", "my-live-credential", "abcdefghijkl", "abc.def"):
        assert secret not in text
    assert "[REDACTED]" in text


def test_token_fields_and_traces_are_redacted():
    result = Redactor().clean(
        {"token": "private", "api_key": "private", "usage": {"total_tokens": 12}}
    )
    assert result["token"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["usage"]["total_tokens"] == 12
