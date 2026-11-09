"""Local pairing control plane. No desktop tools are exposed in phase 5A."""

import hashlib
import secrets
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Connection, RowMapping, insert, select, update

from apps.api.contracts import (
    PairingChallenge,
    PairingClaim,
    RuntimeAudit,
    RuntimeCredential,
    RuntimeStatus,
    now,
)
from memory.store import Store, runtime_audit, runtime_devices, runtime_pairings

PAIRING_SECONDS = 120
CREDENTIAL_SECONDS = 30 * 24 * 60 * 60
LEASE_SECONDS = 15


def timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RuntimeService:
    def __init__(self, store: Store):
        self.store = store
        self.boot_id = str(uuid4())
        self.desktop_enabled: dict[str, bool] = {}

    def audit(self, db: Connection, event: str, identity: str | None = None) -> None:
        db.execute(
            insert(runtime_audit).values(
                event=event, runtime_id=identity, timestamp=now()
            )
        )

    def active(self, db: Connection) -> RowMapping | None:
        return (
            db.execute(
                select(runtime_devices).where(
                    runtime_devices.c.revoked.is_(False),
                    runtime_devices.c.expires > time.time(),
                )
            )
            .mappings()
            .first()
        )

    def status(self) -> RuntimeStatus:
        with self.store.transaction() as db:
            device = self.active(db)
            if device is None:
                return RuntimeStatus()
            connected = (
                not device["disconnected"]
                and device["boot_id"] == self.boot_id
                and device["last_seen"] is not None
                and 0 <= time.time() - device["last_seen"] <= LEASE_SECONDS
            )
            return RuntimeStatus(
                paired=True,
                connected=connected,
                runtimeId=device["id"],
                name=device["name"],
                lastSeen=timestamp(device["last_seen"])
                if device["last_seen"] is not None
                else None,
                credentialExpiresAt=timestamp(device["expires"]),
                capabilities=["heartbeat", "desktop"]
                if connected and self.desktop_enabled.get(device["id"], False)
                else ["heartbeat"],
                message="Runtime connected. Capabilities reflect helper opt-in."
                if connected
                else "Runtime paired, but no recent heartbeat.",
            )

    def issue(self) -> PairingChallenge:
        identity, code = str(uuid4()), secrets.token_urlsafe(24)
        expires = time.time() + PAIRING_SECONDS
        with self.store.transaction() as db:
            if self.active(db):
                raise ValueError("Revoke the existing runtime before pairing a new one")
            db.execute(update(runtime_pairings).values(consumed=True))
            db.execute(
                insert(runtime_pairings).values(
                    id=identity,
                    code_hash=secret_hash(code),
                    expires=expires,
                    attempts=0,
                    consumed=False,
                )
            )
            self.audit(db, "pairing.created")
        return PairingChallenge(
            pairingId=identity,
            pairingCode=identity + "." + code,
            expiresAt=timestamp(expires),
        )

    def claim(self, body: PairingClaim) -> RuntimeCredential:
        token, identity = secrets.token_urlsafe(32), str(uuid4())
        expires = time.time() + CREDENTIAL_SECONDS
        accepted = False
        with self.store.transaction() as db:
            pairing = (
                db.execute(
                    select(runtime_pairings).where(
                        runtime_pairings.c.id == str(body.pairingId)
                    )
                )
                .mappings()
                .first()
            )
            if (
                pairing
                and not pairing["consumed"]
                and pairing["expires"] > time.time()
                and pairing["attempts"] < 5
            ):
                accepted = (
                    secrets.compare_digest(pairing["code_hash"], secret_hash(body.code))
                    and self.active(db) is None
                )
                db.execute(
                    update(runtime_pairings)
                    .where(runtime_pairings.c.id == str(body.pairingId))
                    .values(
                        attempts=pairing["attempts"] + 1,
                        consumed=accepted or pairing["attempts"] >= 4,
                    )
                )
            if accepted:
                db.execute(
                    insert(runtime_devices).values(
                        id=identity,
                        name=body.name.strip(),
                        token_hash=secret_hash(token),
                        expires=expires,
                        revoked=False,
                        disconnected=True,
                    )
                )
                self.audit(db, "runtime.paired", identity)
            else:
                self.audit(db, "pairing.refused")
        if not accepted:
            raise PermissionError(
                "Pairing code is invalid, expired, consumed or locked"
            )
        return RuntimeCredential(
            runtimeId=identity, token=token, expiresAt=timestamp(expires)
        )

    def authenticate(
        self, db: Connection, identity: str, authorization: str | None
    ) -> RowMapping:
        token = (
            authorization[7:]
            if authorization and authorization.startswith("Bearer ")
            else ""
        )
        row = (
            db.execute(select(runtime_devices).where(runtime_devices.c.id == identity))
            .mappings()
            .first()
        )
        if (
            not row
            or row["revoked"]
            or row["expires"] <= time.time()
            or not secrets.compare_digest(row["token_hash"], secret_hash(token))
        ):
            raise PermissionError(
                "Runtime credential is invalid or revoked; pair again"
            )
        return row

    def heartbeat(self, identity: str, authorization: str | None) -> RuntimeStatus:
        with self.store.transaction() as db:
            row = self.authenticate(db, identity, authorization)
            if (
                row["disconnected"]
                or row["boot_id"] != self.boot_id
                or not row["last_seen"]
                or time.time() - row["last_seen"] > LEASE_SECONDS
            ):
                self.audit(db, "runtime.connected", identity)
            db.execute(
                update(runtime_devices)
                .where(runtime_devices.c.id == identity)
                .values(last_seen=time.time(), boot_id=self.boot_id, disconnected=False)
            )
        return self.status()

    def disconnect(self, identity: str, authorization: str | None) -> RuntimeStatus:
        with self.store.transaction() as db:
            self.authenticate(db, identity, authorization)
            db.execute(
                update(runtime_devices)
                .where(runtime_devices.c.id == identity)
                .values(disconnected=True)
            )
            self.audit(db, "runtime.disconnected", identity)
        return self.status()

    def revoke(self, identity: str) -> RuntimeStatus:
        with self.store.transaction() as db:
            device = self.active(db)
            if not device or device["id"] != identity:
                raise ValueError("This runtime is no longer paired")
            db.execute(
                update(runtime_devices)
                .where(runtime_devices.c.id == identity)
                .values(revoked=True, disconnected=True)
            )
            db.execute(update(runtime_pairings).values(consumed=True))
            self.audit(db, "runtime.revoked", identity)
        return self.status()

    def history(self) -> list[RuntimeAudit]:
        with self.store.transaction() as db:
            rows = db.execute(
                select(runtime_audit).order_by(runtime_audit.c.id.desc()).limit(30)
            ).mappings()
            return [
                RuntimeAudit(
                    id=row["id"],
                    event=row["event"],
                    runtimeId=row["runtime_id"],
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]
