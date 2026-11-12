"""Local web-interface authentication: one-time launch codes and hashed sessions."""

import hashlib
import secrets
import threading
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, insert, select

from apps.api.contracts import LaunchCode, SessionGrant, SessionStatus
from memory.store import Store, auth_sessions

LAUNCH_SECONDS = 120
MAX_PENDING_LAUNCHES = 5
SESSION_COOKIE = "mitra_session"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


class AuthService:
    def __init__(self, store: Store, key: str, web_key: str, session_seconds: int):
        self.store = store
        self.key = key
        self.web_key = web_key
        self.session_seconds = session_seconds
        self.launches: dict[str, float] = {}
        self.lock = threading.Lock()

    @staticmethod
    def _matches(expected: str, presented: str | None) -> bool:
        return presented is not None and secrets.compare_digest(
            expected.encode(), presented.encode()
        )

    def local_key_valid(self, presented: str | None) -> bool:
        return self._matches(self.key, presented)

    def web_key_valid(self, presented: str | None) -> bool:
        return self._matches(self.web_key, presented)

    def issue_launch(self) -> LaunchCode:
        code = secrets.token_urlsafe(32)
        expires = time.time() + LAUNCH_SECONDS
        with self.lock:
            self._prune()
            while len(self.launches) >= MAX_PENDING_LAUNCHES:
                oldest = min(self.launches, key=self.launches.__getitem__)
                del self.launches[oldest]
            self.launches[_hash(code)] = expires
        return LaunchCode(code=code, expiresAt=_timestamp(expires))

    def _prune(self) -> None:
        current = time.time()
        for digest in [k for k, v in self.launches.items() if v <= current]:
            del self.launches[digest]

    def redeem(self, code: str) -> SessionGrant:
        with self.lock:
            self._prune()
            expires = self.launches.pop(_hash(code), None)
        if expires is None:
            raise PermissionError("Launch link is invalid, expired or already used")
        token = secrets.token_urlsafe(32)
        created = time.time()
        session_expires = created + self.session_seconds
        with self.store.transaction() as db:
            db.execute(delete(auth_sessions).where(auth_sessions.c.expires <= created))
            db.execute(
                insert(auth_sessions).values(
                    id=str(uuid4()),
                    token_hash=_hash(token),
                    created=created,
                    expires=session_expires,
                )
            )
        return SessionGrant(token=token, expiresAt=_timestamp(session_expires))

    def session_expiry(self, token: str | None) -> float | None:
        if not token or len(token) > 128:
            return None
        with self.store.engine.connect() as db:
            expires = db.execute(
                select(auth_sessions.c.expires).where(
                    auth_sessions.c.token_hash == _hash(token)
                )
            ).scalar_one_or_none()
        return expires if expires is not None and expires > time.time() else None

    def status(self, token: str | None) -> SessionStatus:
        expires = self.session_expiry(token)
        if expires is None:
            raise PermissionError("MITRA is locked. Open a new launch link.")
        with self.store.engine.connect() as db:
            active = db.execute(
                select(func.count())
                .select_from(auth_sessions)
                .where(auth_sessions.c.expires > time.time())
            ).scalar_one()
        return SessionStatus(expiresAt=_timestamp(expires), activeSessions=active)

    def revoke(self, token: str | None) -> None:
        if token:
            with self.store.transaction() as db:
                db.execute(
                    delete(auth_sessions).where(
                        auth_sessions.c.token_hash == _hash(token)
                    )
                )

    def revoke_all(self) -> None:
        with self.lock:
            self.launches.clear()
        with self.store.transaction() as db:
            db.execute(delete(auth_sessions))
