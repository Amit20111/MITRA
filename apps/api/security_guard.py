"""Request boundary for the local API: loopback, origin, rate limit and authentication.

Every request is checked in this order:

1. The peer and the Host header must be loopback (DNS-rebinding protection).
2. A browser Origin, when present, must be the configured web origin.
3. Global per-category rate limits.
4. Authentication:
   * native runtime routes use their own pairing/runtime credentials;
   * control-plane routes need the raw local key and refuse browser/proxy traffic;
   * every other API route needs the derived web key (or local key) *and* a
     valid browser session cookie.
"""

import ipaddress
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from apps.api.auth_service import SESSION_COOKIE, AuthService

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOCAL_KEY_HEADER = "x-mitra-local-key"
WEB_KEY_HEADER = "x-mitra-web-key"
_UUID = r"[0-9a-fA-F-]{36}"
NATIVE_ROUTES = re.compile(
    rf"^/api/v1/runtime/(pairing/claim|{_UUID}/(heartbeat|disconnect|poll)"
    rf"|{_UUID}/{_UUID}/(authorize|result))$"
)
CONTROL_ROUTES = {"/api/v1/auth/launch", "/api/v1/auth/redeem", "/openapi.json"}
PROTECTED_PREFIXES = ("/api/", "/openapi.json", "/docs", "/redoc")
MESSAGE_ROUTE = re.compile(rf"^/api/v1/conversations/{_UUID}/messages$")

# (requests, window seconds) per category, shared by all loopback callers.
RATE_LIMITS: dict[str, tuple[int, float]] = {
    "auth": (20, 60.0),
    "claim": (20, 60.0),
    "native": (1200, 60.0),
    "message": (30, 60.0),
    "voice": (30, 60.0),
    "write": (300, 60.0),
}


def _deny(status: int, detail: str, **headers: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status, headers=headers)


def loopback_host(header: str) -> bool:
    try:
        authority = urlsplit("http://" + header)
        if (
            authority.username
            or authority.password
            or authority.path
            or authority.query
            or authority.fragment
        ):
            return False
        _ = authority.port
    except ValueError:
        return False
    return authority.hostname in LOOPBACK_HOSTS


def loopback_peer(request: Request) -> bool:
    try:
        return bool(
            request.client and ipaddress.ip_address(request.client.host).is_loopback
        )
    except ValueError:
        return False


class RateLimiter:
    def __init__(self, limits: dict[str, tuple[int, float]] | None = None):
        self.limits = dict(limits or RATE_LIMITS)
        self.hits: dict[str, deque[float]] = {name: deque() for name in self.limits}

    def category(self, method: str, path: str) -> str | None:
        if path in ("/api/v1/auth/launch", "/api/v1/auth/redeem"):
            return "auth"
        if path == "/api/v1/runtime/pairing/claim":
            return "claim"
        if NATIVE_ROUTES.match(path):
            return "native"
        if method in ("GET", "HEAD", "OPTIONS"):
            return None
        if MESSAGE_ROUTE.match(path):
            return "message"
        if path.startswith("/api/v1/voice/"):
            return "voice"
        return "write"

    def retry_after(self, method: str, path: str) -> int | None:
        name = self.category(method, path)
        if name is None:
            return None
        limit, window = self.limits[name]
        hits = self.hits[name]
        current = time.monotonic()
        while hits and current - hits[0] >= window:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, int(window - (current - hits[0])) + 1)
        hits.append(current)
        return None


def build_guard(
    auth: Callable[[], AuthService],
    allowed_origins: set[str],
    limiter: RateLimiter,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if not loopback_peer(request) or not loopback_host(
            request.headers.get("host", "")
        ):
            return _deny(403, "MITRA only accepts loopback requests")
        origin = request.headers.get("origin")
        native = bool(NATIVE_ROUTES.match(path))
        if origin and (native or path in CONTROL_ROUTES):
            return _deny(403, "This endpoint is not available to browsers")
        if origin and origin not in allowed_origins:
            return _deny(403, "Origin not allowed")
        retry = limiter.retry_after(request.method, path)
        if retry is not None:
            return _deny(429, "Too many requests; slow down", **{"Retry-After": str(retry)})
        if path.startswith(PROTECTED_PREFIXES) and not native:
            service = auth()
            local_key = request.headers.get(LOCAL_KEY_HEADER)
            web_key = request.headers.get(WEB_KEY_HEADER)
            if path in CONTROL_ROUTES:
                if web_key is not None or not service.local_key_valid(local_key):
                    return _deny(401, "Local API key required")
            else:
                if not (
                    service.web_key_valid(web_key) or service.local_key_valid(local_key)
                ):
                    return _deny(401, "Requests must come through the MITRA interface")
                token = request.cookies.get(SESSION_COOKIE)
                if service.session_expiry(token) is None:
                    return _deny(401, "MITRA is locked. Open a new launch link.")
        response = await call_next(request)
        if path.startswith(PROTECTED_PREFIXES):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response

    return guard
