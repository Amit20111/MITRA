import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from apps.api.main import create_app
from memory.store import runtime_devices, runtime_pairings
from tests.client import ApiClient
from tests.fakes import FakeProvider


@pytest.fixture
def runtime_client(tmp_path):
    app = create_app(tmp_path / "db.sqlite", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345)
    ) as client:
        yield client


def challenge(client):
    response = client.post("/api/v1/runtime/pairing")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    identity, code = result["pairingCode"].split(".", 1)
    return {"pairingId": identity, "code": code, "name": "Test Windows helper"}


def pair(client):
    response = client.post("/api/v1/runtime/pairing/claim", json=challenge(client))
    assert response.status_code == 200
    return response.json()


def heartbeat(client, credential, body=None):
    return client.post(
        f"/api/v1/runtime/{credential['runtimeId']}/heartbeat",
        json=body or {},
        headers={"Authorization": "Bearer " + credential["token"]},
    )


def test_pair_heartbeat_disconnect_revoke_and_no_secret_storage(
    runtime_client, tmp_path
):
    client = runtime_client
    assert not client.get("/api/v1/runtime/status").json()["paired"]
    claim = challenge(client)
    credential = client.post("/api/v1/runtime/pairing/claim", json=claim).json()
    assert client.post("/api/v1/runtime/pairing/claim", json=claim).status_code == 401
    state = client.get("/api/v1/runtime/status").json()
    assert state["paired"] and not state["connected"]
    assert state["capabilities"] == ["heartbeat"]
    connected = heartbeat(client, credential)
    assert connected.status_code == 200 and connected.json()["connected"]
    assert client.post("/api/v1/runtime/pairing").status_code == 409
    disconnected = client.post(
        f"/api/v1/runtime/{credential['runtimeId']}/disconnect",
        headers={"Authorization": "Bearer " + credential["token"]},
    )
    assert disconnected.json()["paired"] and not disconnected.json()["connected"]
    assert heartbeat(client, credential).json()["connected"]
    assert not client.post(
        "/api/v1/runtime/revoke", json={"runtimeId": credential["runtimeId"]}
    ).json()["paired"]
    assert heartbeat(client, credential).status_code == 401
    for secret in (claim["code"], credential["token"]):
        assert secret.encode() not in (tmp_path / "db.sqlite").read_bytes()
        assert secret not in client.get("/api/v1/runtime/audit").text
        assert secret not in client.get("/api/v1/runtime/status").text
    events = [item["event"] for item in client.get("/api/v1/runtime/audit").json()]
    assert "runtime.connected" in events and "runtime.revoked" in events


def test_pairing_expiry_replacement_and_attempt_limit(runtime_client):
    client = runtime_client
    old = challenge(client)
    current = challenge(client)
    assert client.post("/api/v1/runtime/pairing/claim", json=old).status_code == 401
    for _ in range(5):
        assert (
            client.post(
                "/api/v1/runtime/pairing/claim", json={**current, "code": "wrong" * 8}
            ).status_code
            == 401
        )
    assert client.post("/api/v1/runtime/pairing/claim", json=current).status_code == 401
    expired = challenge(client)
    with client.app.state.agent.store.transaction() as db:
        db.execute(
            update(runtime_pairings)
            .where(runtime_pairings.c.id == expired["pairingId"])
            .values(expires=time.time() - 1)
        )
    assert client.post("/api/v1/runtime/pairing/claim", json=expired).status_code == 401


def test_pair_code_consumed_atomically(runtime_client):
    claim = challenge(runtime_client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(
            pool.map(
                lambda _: (
                    runtime_client.post(
                        "/api/v1/runtime/pairing/claim", json=claim
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(codes) == [200, 401]


def test_native_auth_protocol_and_lease(runtime_client):
    client = runtime_client
    credential = pair(client)
    path = f"/api/v1/runtime/{credential['runtimeId']}/heartbeat"
    assert client.post(path, json={}).status_code == 401
    assert heartbeat(client, {**credential, "token": "invalid"}).status_code == 401
    assert (
        heartbeat(client, {**credential, "runtimeId": str(uuid4())}).status_code == 401
    )
    assert heartbeat(client, credential, {"capabilities": ["shell"]}).status_code == 422
    assert heartbeat(client, credential, {"protocolVersion": 2}).status_code == 422
    assert heartbeat(client, credential).json()["connected"]
    with client.app.state.agent.store.transaction() as db:
        db.execute(update(runtime_devices).values(last_seen=time.time() - 16))
    status = client.get("/api/v1/runtime/status").json()
    assert status["paired"] and not status["connected"]
    with client.app.state.agent.store.transaction() as db:
        db.execute(update(runtime_devices).values(expires=time.time() - 1))
    assert heartbeat(client, credential).status_code == 401


def test_runtime_rejects_web_credentials_remote_peers_and_hosts(
    runtime_client, tmp_path
):
    client = runtime_client
    claim = challenge(client)
    for origin in ["http://evil.example", "http://127.0.0.1:3000"]:
        response = client.post(
            "/api/v1/runtime/pairing/claim", json=claim, headers={"Origin": origin}
        )
        assert response.status_code == 403
    assert (
        client.post(
            "/api/v1/runtime/pairing", headers={"Origin": "http://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/runtime/status", headers={"Host": "evil.example"}
        ).status_code
        == 403
    )
    with ApiClient(
        create_app(tmp_path / "remote.db", FakeProvider([]), tmp_path / "other"),
        base_url="http://127.0.0.1:8000",
        client=("192.0.2.1", 1234),
        authenticate=False,
    ) as remote:
        assert remote.get("/api/v1/runtime/status").status_code == 403
        assert remote.post("/api/v1/auth/launch").status_code == 403
    invalid = client.post(
        "/api/v1/runtime/pairing/claim", json={**claim, "platform": claim["code"]}
    )
    assert invalid.status_code == 422 and claim["code"] not in invalid.text


def test_restart_retains_pairing_but_requires_fresh_heartbeat(tmp_path):
    database, workspace = tmp_path / "db.sqlite", tmp_path / "workspace"
    with ApiClient(
        create_app(database, FakeProvider([]), workspace),
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 1234),
    ) as client:
        conversation = client.post("/api/v1/conversations").json()
        credential = pair(client)
        assert heartbeat(client, credential).json()["connected"]
    with ApiClient(
        create_app(database, FakeProvider([]), workspace),
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 1234),
    ) as client:
        status = client.get("/api/v1/runtime/status").json()
        assert status["paired"] and not status["connected"]
        assert heartbeat(client, credential).json()["connected"]
        assert (
            client.get(f"/api/v1/conversations/{conversation['id']}").status_code == 200
        )
        with client.app.state.agent.store.transaction() as db:
            assert len(db.execute(select(runtime_devices)).all()) == 1
