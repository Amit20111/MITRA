"""Outbound-only local API client. No proxies, redirects, or tool execution."""

from urllib.parse import urlsplit
from uuid import UUID

import httpx

from apps.api.contracts import (
    DesktopJob,
    DesktopResult,
    PairingClaim,
    RuntimeCredential,
    RuntimeHeartbeat,
    RuntimeStatus,
)


def api_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or "\\" in value
        or any(ord(c) <= 32 for c in value)
    ):
        raise ValueError(
            "Runtime API must be a loopback HTTP(S) origin without credentials or paths"
        )
    if parsed.port is not None and parsed.port < 1:
        raise ValueError("Invalid API port")
    return value.rstrip("/")


class RuntimeClient:
    def __init__(self, api: str, transport: httpx.BaseTransport | None = None):
        self.api = api_url(api)
        self.http = httpx.Client(
            base_url=self.api,
            timeout=5,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    def pair(self, pairing_code: str, name: str) -> RuntimeCredential:
        identity, separator, code = pairing_code.partition(".")
        if not separator:
            raise ValueError("Paste the complete pairing code from Settings")
        body = PairingClaim(pairingId=UUID(identity), code=code, name=name)
        response = self.http.post(
            "/api/v1/runtime/pairing/claim", json=body.model_dump(mode="json")
        )
        self.check(response)
        return RuntimeCredential.model_validate(response.json())

    @staticmethod
    def check(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise PermissionError(
                "Credential or pairing code refused; generate a new pairing in Settings"
            )
        if response.status_code != 200:
            raise ConnectionError(
                "Local API refused the runtime request; check pairing and service configuration"
            )

    def heartbeat(
        self, credential: RuntimeCredential, desktop: bool = False
    ) -> RuntimeStatus:
        response = self.http.post(
            f"/api/v1/runtime/{credential.runtimeId}/heartbeat",
            json=RuntimeHeartbeat(desktopEnabled=desktop).model_dump(),
            headers={"Authorization": "Bearer " + credential.token},
        )
        self.check(response)
        return RuntimeStatus.model_validate(response.json())

    def disconnect(self, credential: RuntimeCredential) -> None:
        response = self.http.post(
            f"/api/v1/runtime/{credential.runtimeId}/disconnect",
            headers={"Authorization": "Bearer " + credential.token},
        )
        self.check(response)

    def desktop_request(
        self,
        credential: RuntimeCredential,
        suffix: str,
        result: DesktopResult | None = None,
    ) -> DesktopJob | None:
        response = self.http.post(
            f"/api/v1/runtime/{credential.runtimeId}/{suffix}",
            headers={"Authorization": "Bearer " + credential.token},
            json=result.model_dump() if result else None,
        )
        self.check(response)
        data = response.json()
        return DesktopJob.model_validate(data) if data else None

    def close(self) -> None:
        self.http.close()
