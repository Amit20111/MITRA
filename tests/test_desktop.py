import base64
import hashlib
import json
import struct
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from apps.api.contracts import DesktopJob
from apps.api.main import create_app
from apps.runtime.desktop import NativeDesktop
from tests.client import ApiClient
from tests.fakes import FakeProvider
from tests.test_runtime_pairing import heartbeat, pair


@pytest.fixture
def desktop_client(tmp_path):
    app = create_app(tmp_path / "desktop.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 2222)
    ) as client:
        credential = pair(client)
        heartbeat(client, credential, {"desktopEnabled": True})
        yield client, credential


def native(client, credential, suffix, data=None):
    return client.post(
        f"/api/v1/runtime/{credential['runtimeId']}/{suffix}",
        headers={"Authorization": "Bearer " + credential["token"]},
        json=data,
    )


def propose(client, action="list_windows", target=None):
    response = client.post(
        "/api/v1/runtime/desktop/jobs", json={"action": action, "targetId": target}
    )
    assert response.status_code == 200, response.text
    return response.json()


def approve(client, job):
    return client.post(
        f"/api/v1/runtime/desktop/{job['id']}/decision",
        json={"digest": job["digest"], "approve": True},
    )


def listed(client, credential):
    job = propose(client)
    approve(client, job)
    native(client, credential, "poll")
    target = {"id": str(uuid4()), "title": "Fixture", "processId": 123}
    response = native(
        client,
        credential,
        job["id"] + "/result",
        {"success": True, "message": "Inspected", "targets": [target]},
    )
    assert response.status_code == 200
    return target


def test_dispatch_requires_exact_approval_and_is_once(desktop_client):
    client, credential = desktop_client
    job = propose(client)
    assert native(client, credential, "poll").json() is None
    assert native(client, credential, job["id"] + "/authorize").status_code == 409
    assert (
        client.post(
            f"/api/v1/runtime/desktop/{job['id']}/decision",
            json={"digest": "bad", "approve": True},
        ).status_code
        == 409
    )
    assert approve(client, job).status_code == 200
    assert approve(client, job).status_code == 409
    dispatched = native(client, credential, "poll").json()
    assert dispatched["state"] == "dispatched"
    assert native(client, credential, "poll").json() is None
    assert native(client, credential, job["id"] + "/authorize").status_code == 200
    assert (
        native(
            client,
            credential,
            job["id"] + "/result",
            {"success": True, "message": "Done"},
        ).status_code
        == 200
    )
    assert native(client, credential, job["id"] + "/authorize").status_code == 409


@pytest.mark.parametrize("boundary", ["stop", "disconnect", "revoke", "expire"])
def test_dispatch_stops_at_boundaries(desktop_client, boundary):
    client, credential = desktop_client
    job = propose(client)
    approve(client, job)
    native(client, credential, "poll")
    if boundary == "stop":
        client.post("/api/v1/runtime/desktop/stop")
    elif boundary == "disconnect":
        native(client, credential, "disconnect")
    elif boundary == "revoke":
        client.post(
            "/api/v1/runtime/revoke", json={"runtimeId": credential["runtimeId"]}
        )
    else:
        client.app.state.desktop_service.jobs[job["id"]].expiresAt = (
            datetime.now(UTC) - timedelta(seconds=1)
        ).isoformat()
    assert native(client, credential, job["id"] + "/authorize").status_code in (
        401,
        409,
    )
    assert client.get("/api/v1/runtime/desktop/jobs").json()[0]["state"] == "cancelled"
    if boundary == "stop":
        client.post("/api/v1/runtime/desktop/enable")
        assert native(client, credential, "poll").json() is None


def test_targets_images_and_protocol_are_bounded(desktop_client):
    client, credential = desktop_client
    assert (
        client.post(
            "/api/v1/runtime/desktop/jobs", json={"action": "click"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/runtime/desktop/jobs",
            json={"action": "focus", "targetId": "made-up"},
        ).status_code
        == 409
    )
    target = listed(client, credential)
    job = propose(client, "screenshot", target["id"])
    approve(client, job)
    native(client, credential, "poll")
    bitmap = (
        struct.pack("<2sIHHI", b"BM", 58, 0, 0, 54)
        + struct.pack("<IiiHHIIiiII", 40, 1, 1, 1, 32, 0, 4, 0, 0, 0, 0)
        + bytes(4)
    )
    encoded = base64.b64encode(bitmap).decode()
    bad_image = native(
        client,
        credential,
        job["id"] + "/result",
        {
            "success": True,
            "message": "bad image",
            "image": base64.b64encode(b"BMinvalid").decode(),
        },
    )
    assert bad_image.status_code == 409
    done = native(
        client,
        credential,
        job["id"] + "/result",
        {"success": True, "message": "Captured", "image": encoded},
    )
    assert done.status_code == 200 and done.json()["hasImage"]
    jobs = client.get("/api/v1/runtime/desktop/jobs").json()
    assert all(j["image"] is None for j in jobs)
    url = f"/api/v1/runtime/desktop/{job['id']}/image"
    image = client.get(url)
    assert image.content == bitmap and image.headers["cache-control"] == "no-store"
    client.post("/api/v1/runtime/desktop/stop")
    assert client.get(url).status_code == 404
    assert (
        client.post(
            f"/api/v1/runtime/{credential['runtimeId']}/poll",
            headers={"Origin": "http://127.0.0.1:3000"},
        ).status_code
        == 403
    )


def test_opt_in_and_wrong_runtime(desktop_client):
    client, credential = desktop_client
    heartbeat(client, credential)
    assert (
        client.post(
            "/api/v1/runtime/desktop/jobs", json={"action": "list_windows"}
        ).status_code
        == 409
    )
    assert (
        native(client, {**credential, "runtimeId": str(uuid4())}, "poll").status_code
        == 401
    )


def native_job(action="list_windows", target=None, title="Visible windows"):
    args = {"action": action, "targetId": target}
    return DesktopJob(
        runtimeId=str(uuid4()),
        **args,
        targetTitle=title,
        digest=hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest(),
        expiresAt=(datetime.now(UTC) + timedelta(seconds=120)).isoformat(),
        state="dispatched",
    )


def test_helper_rechecks_digest_expiry_replay_and_target(monkeypatch):
    desktop = NativeDesktop()
    monkeypatch.setattr(desktop, "inspect", list)
    job = native_job()
    assert desktop.execute(job).success
    with pytest.raises(ValueError):
        desktop.execute(job)
    job = native_job()
    job.digest = "modified"
    with pytest.raises(ValueError):
        desktop.execute(job)
    job = native_job()
    job.expiresAt = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError):
        desktop.execute(job)
    with pytest.raises(ValueError):
        desktop.execute(native_job("focus", "unknown"))
    signature = (123, "Fixture", "Class", 100, 100)
    desktop.targets["target"] = (1, signature, time.monotonic() + 10)
    monkeypatch.setattr(
        "apps.runtime.desktop.identity", lambda _: (999, "Fixture", "Class", 100, 100)
    )
    with pytest.raises(ValueError):
        desktop.execute(native_job("focus", "target", "Fixture"))


def test_restart_does_not_replay_desktop(desktop_client):
    client, _ = desktop_client
    job = propose(client)
    approve(client, job)
    from apps.api.desktop_service import DesktopService

    restarted = DesktopService(client.app.state.runtime_service)
    assert restarted.list_jobs() == []
