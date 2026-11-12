"""Authenticated test clients that behave like the trusted Next.js proxy."""

from typing import Any, Self

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.auth_service import SESSION_COOKIE
from apps.api.local_key import web_key
from apps.api.security_guard import LOCAL_KEY_HEADER, WEB_KEY_HEADER


def login(client: httpx.Client, app: FastAPI) -> str:
    """Create a browser session using the launch flow and attach proxy credentials."""
    key = app.state.local_key
    client.headers.pop(WEB_KEY_HEADER, None)
    launch = client.post("/api/v1/auth/launch", headers={LOCAL_KEY_HEADER: key})
    assert launch.status_code == 200, launch.text
    grant = client.post(
        "/api/v1/auth/redeem",
        json={"code": launch.json()["code"]},
        headers={LOCAL_KEY_HEADER: key},
    )
    assert grant.status_code == 200, grant.text
    token: str = grant.json()["token"]
    client.cookies.set(SESSION_COOKIE, token)
    client.headers[WEB_KEY_HEADER] = web_key(key)
    return token


class ApiClient(TestClient):
    def __init__(self, app: FastAPI, authenticate: bool = True, **kwargs: Any):
        kwargs.setdefault("base_url", "http://127.0.0.1:8000")
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(app, **kwargs)
        self.authenticate = authenticate
        self.fastapi = app

    def __enter__(self) -> Self:
        super().__enter__()
        if self.authenticate:
            login(self, self.fastapi)
        return self
