"""Phase 8A security boundary tests: local key, launch codes, sessions, Host/Origin, rate limits."""

import time
from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.api.auth_service import SESSION_COOKIE
from apps.api.local_key import KEY_NAME, load_or_create, web_key
from apps.api.main import create_app
from apps.api.security_guard import LOCAL_KEY_HEADER, WEB_KEY_HEADER
from memory.store import auth_sessions
from tests.client import ApiClient, login
from tests.fakes import FakeProvider


def test_local_key_created_once_validated_and_redacted(tmp_path, monkeypatch):
    secret_dir = tmp_path / "secrets"
    monkeypatch.setenv("MITRA_SECRET_DIR", str(secret_dir))
    first = load_or_create(secret_dir)
    second = load_or_create(secret_dir)
    assert first == second
    assert len(first) >= 43
    assert (secret_dir / KEY_NAME).exists()

    bad_dir = tmp_path / "bad-secrets"
    bad_dir.mkdir()
    (bad_dir / KEY_NAME).write_text("short", encoding="ascii")
    with pytest.raises(RuntimeError):
        load_or_create(bad_dir)


def test_unauthenticated_and_wrong_key_requests_are_refused(tmp_path):
    app = create_app(tmp_path / "sec.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app, authenticate=False) as client:
        key = app.state.local_key
        derived = web_key(key)
        for path in [
            "/api/v1/health",
            "/api/v1/settings",
            "/api/v1/conversations",
            "/api/v1/tasks",
            "/api/v1/memories",
            "/api/v1/runtime/status",
            "/openapi.json",
        ]:
            assert client.get(path).status_code == 401
        assert client.get("/docs").status_code == 401
        assert client.get("/redoc").status_code == 401

        assert (
            client.get(
                "/api/v1/health", headers={WEB_KEY_HEADER: derived}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/launch", headers={WEB_KEY_HEADER: derived}
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/openapi.json", headers={WEB_KEY_HEADER: derived}
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/openapi.json", headers={LOCAL_KEY_HEADER: key}
            ).status_code
            == 200
        )


def test_launch_link_single_use_expiry_and_pending_cap(tmp_path):
    app = create_app(tmp_path / "launch.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app, authenticate=False) as client:
        key = app.state.local_key
        headers = {LOCAL_KEY_HEADER: key}

        codes = [
            client.post("/api/v1/auth/launch", headers=headers).json()["code"]
            for _ in range(6)
        ]
        assert (
            client.post(
                "/api/v1/auth/redeem", json={"code": codes[0]}, headers=headers
            ).status_code
            == 401
        )
        redeemed = client.post(
            "/api/v1/auth/redeem", json={"code": codes[-1]}, headers=headers
        )
        assert redeemed.status_code == 200
        token = redeemed.json()["token"]

        assert (
            client.post(
                "/api/v1/auth/redeem", json={"code": codes[-1]}, headers=headers
            ).status_code
            == 401
        )

        with app.state.agent.store.transaction() as db:
            rows = db.execute(select(auth_sessions)).mappings().all()
            assert len(rows) == 1
            assert rows[0]["token_hash"] != token

        expired_code = client.post("/api/v1/auth/launch", headers=headers).json()[
            "code"
        ]
        for digest in list(app.state.auth_service.launches):
            app.state.auth_service.launches[digest] = time.time() - 1
        assert (
            client.post(
                "/api/v1/auth/redeem", json={"code": expired_code}, headers=headers
            ).status_code
            == 401
        )


def test_session_lifecycle_logout_and_revoke_all(tmp_path):
    app = create_app(tmp_path / "sess.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app, authenticate=False) as client_a, ApiClient(
        app, authenticate=False
    ) as client_b:
        login(client_a, app)
        login(client_b, app)

        status = client_a.get("/api/v1/auth/session")
        assert status.status_code == 200
        assert status.json()["activeSessions"] == 2
        assert status.headers["x-frame-options"] == "DENY"
        assert status.headers["x-content-type-options"] == "nosniff"
        assert status.headers["referrer-policy"] == "no-referrer"
        assert status.headers["cross-origin-resource-policy"] == "same-origin"

        assert client_a.post("/api/v1/auth/logout").status_code == 204
        assert client_a.get("/api/v1/health").status_code == 401
        assert client_b.get("/api/v1/health").status_code == 200

        login(client_a, app)
        assert client_b.post("/api/v1/auth/revoke-all").status_code == 204
        assert client_a.get("/api/v1/health").status_code == 401
        assert client_b.get("/api/v1/health").status_code == 401


def test_dns_rebinding_host_and_origin_guards_on_all_routes(tmp_path):
    app = create_app(tmp_path / "host.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app) as client:
        for bad_host in [
            "evil.example",
            "127.0.0.1.evil.example",
            "localhost:8000@evil.example",
            "192.168.1.10:8000",
        ]:
            for path in ["/api/v1/health", "/api/v1/conversations", "/openapi.json"]:
                assert (
                    client.get(path, headers={"Host": bad_host}).status_code == 403
                )
        assert (
            client.post(
                "/api/v1/auth/launch",
                headers={
                    LOCAL_KEY_HEADER: app.state.local_key,
                    "Origin": "http://127.0.0.1:3000",
                },
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/openapi.json",
                headers={
                    LOCAL_KEY_HEADER: app.state.local_key,
                    "Origin": "http://127.0.0.1:3000",
                },
            ).status_code
            == 403
        )


def test_rate_limiter_blocks_bursts_with_retry_after(tmp_path):
    app = create_app(tmp_path / "rate.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app, authenticate=False) as client:
        key = app.state.local_key
        statuses = [
            client.post(
                "/api/v1/auth/redeem",
                json={"code": "a" * 32},
                headers={LOCAL_KEY_HEADER: key},
            ).status_code
            for _ in range(21)
        ]
        assert statuses[:20] == [401] * 20
        assert statuses[20] == 429
        limited = client.post(
            "/api/v1/auth/launch", headers={LOCAL_KEY_HEADER: key}
        )
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) >= 1

        # GET requests remain unaffected by auth burst limiting.
        assert (
            client.get(
                "/openapi.json", headers={LOCAL_KEY_HEADER: key}
            ).status_code
            == 200
        )


def test_session_cookie_bound_to_store_across_expiry(tmp_path):
    app = create_app(tmp_path / "exp.db", FakeProvider([]), tmp_path / "workspace")
    with ApiClient(app) as client:
        assert client.get("/api/v1/settings").status_code == 200
        with app.state.agent.store.transaction() as db:
            db.execute(auth_sessions.update().values(expires=time.time() - 5))
        assert client.get("/api/v1/settings").status_code == 401
        client.cookies.set(SESSION_COOKIE, "x" * 200)
        assert client.get("/api/v1/settings").status_code == 401
        assert str(uuid4())
