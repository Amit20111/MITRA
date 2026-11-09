from __future__ import annotations

"""Ephemeral, exact-approved desktop jobs. Never replay after restart."""

import base64
import hashlib
import json
import struct
import threading
import time
from datetime import datetime

from apps.api.contracts import (
    DesktopDecision,
    DesktopJob,
    DesktopRequest,
    DesktopResult,
)
from apps.api.runtime_service import RuntimeService, timestamp


class DesktopService:
    def __init__(self, runtime: RuntimeService):
        self.runtime = runtime
        self.jobs: dict[str, DesktopJob] = {}
        self.lock = threading.RLock()
        self.paused = False

    def audit(self, event: str, runtime_id: str) -> None:
        with self.runtime.store.transaction() as db:
            self.runtime.audit(db, "desktop." + event, runtime_id)

    def expire(self) -> None:
        state = self.runtime.status()
        for job in self.jobs.values():
            expired = datetime.fromisoformat(job.expiresAt).timestamp() < time.time()
            if (
                expired
                or not state.connected
                or "desktop" not in state.capabilities
                or state.runtimeId != job.runtimeId
            ):
                job.image = None
                job.targets = []
                if job.state in ("pending", "approved", "dispatched"):
                    job.state, job.message = (
                        "cancelled",
                        "Expired or runtime disconnected; no replay.",
                    )

    def list_jobs(self) -> list[DesktopJob]:
        with self.lock:
            self.expire()
            return [
                j.model_copy(
                    update={"image": None, "hasImage": bool(j.image)}, deep=True
                )
                for j in self.jobs.values()
            ]

    def create(self, body: DesktopRequest) -> DesktopJob:
        with self.lock:
            self.expire()
            status = self.runtime.status()
            if (
                self.paused
                or not status.connected
                or "desktop" not in status.capabilities
            ):
                raise ValueError(
                    "Start the paired helper with --desktop; desktop dispatch must be enabled"
                )
            if any(
                j.state in ("pending", "approved", "dispatched")
                for j in self.jobs.values()
            ):
                raise ValueError("Finish or stop the current desktop request first")
            title = "Visible window titles and process IDs"
            if body.action != "list_windows":
                targets = [
                    t
                    for j in self.jobs.values()
                    if j.state == "completed" and j.action == "list_windows"
                    for t in j.targets
                ]
                target = next((t for t in targets if t.id == body.targetId), None)
                if not target:
                    raise ValueError("Target expired; inspect windows again")
                title = target.title
            elif body.targetId is not None:
                raise ValueError("Window listing cannot specify a target")
            digest = hashlib.sha256(
                json.dumps(body.model_dump(), sort_keys=True).encode()
            ).hexdigest()
            job = DesktopJob(
                runtimeId=status.runtimeId or "",
                **body.model_dump(),
                targetTitle=title,
                digest=digest,
                expiresAt=timestamp(time.time() + 120),
            )
            if len(self.jobs) >= 20:
                self.jobs.pop(next(iter(self.jobs)))
            self.jobs[job.id] = job
            self.audit("proposed", job.runtimeId)
            return job.model_copy(deep=True)

    def decide(self, identity: str, body: DesktopDecision) -> DesktopJob:
        with self.lock:
            self.expire()
            job = self.get(identity)
            if job.state != "pending" or body.digest != job.digest:
                raise ValueError("Approval is stale or does not match")
            job.state = "approved" if body.approve else "cancelled"
            job.message = "Waiting for helper" if body.approve else "Rejected"
            self.audit(job.state, job.runtimeId)
            return job.model_copy(deep=True)

    def get(self, identity: str) -> DesktopJob:
        if identity not in self.jobs:
            raise LookupError("Desktop request not found")
        return self.jobs[identity]

    def auth(self, runtime_id: str, authorization: str | None) -> None:
        with self.runtime.store.transaction() as db:
            self.runtime.authenticate(db, runtime_id, authorization)

    def poll(self, runtime_id: str, authorization: str | None) -> DesktopJob | None:
        with self.lock:
            self.auth(runtime_id, authorization)
            self.expire()
            if self.paused:
                return None
            for job in self.jobs.values():
                if job.runtimeId == runtime_id and job.state == "approved":
                    job.state, job.message = (
                        "dispatched",
                        "Helper is validating the target",
                    )
                    self.audit("dispatched", runtime_id)
                    return job.model_copy(deep=True)
            return None

    def authorize(
        self, runtime_id: str, identity: str, authorization: str | None
    ) -> DesktopJob:
        with self.lock:
            self.auth(runtime_id, authorization)
            self.expire()
            job = self.get(identity)
            if self.paused or job.runtimeId != runtime_id or job.state != "dispatched":
                raise ValueError("Desktop request no longer authorized")
            return job.model_copy(deep=True)

    def finish(
        self,
        runtime_id: str,
        identity: str,
        authorization: str | None,
        result: DesktopResult,
    ) -> DesktopJob:
        with self.lock:
            job = self.authorize(runtime_id, identity, authorization)
            if result.image:
                if job.action != "screenshot" or not result.success:
                    raise ValueError("Unexpected image")
                try:
                    image = base64.b64decode(result.image, validate=True)
                except ValueError as error:
                    raise ValueError("Invalid screenshot") from error
                if (
                    len(image) < 54
                    or len(image) > 9000000
                    or not image.startswith(b"BM")
                ):
                    raise ValueError("Invalid screenshot")
                length, offset = (
                    struct.unpack_from("<I", image, 2)[0],
                    struct.unpack_from("<I", image, 10)[0],
                )
                header, width, height, planes, bits, compression = struct.unpack_from(
                    "<IiiHHI", image, 14
                )
                if not (
                    length == len(image)
                    and offset == 54
                    and header == 40
                    and 1 <= width <= 1920
                    and 1 <= height <= 1080
                    and planes == 1
                    and bits == 32
                    and compression == 0
                    and len(image) == 54 + width * height * 4
                ):
                    raise ValueError("Invalid screenshot dimensions or encoding")
            if result.targets and job.action != "list_windows":
                raise ValueError("Unexpected targets")
            if result.image:
                for previous in self.jobs.values():
                    previous.image = None
            stored = self.get(identity)
            stored.state = "completed" if result.success else "failed"
            stored.message, stored.targets, stored.image = (
                result.message,
                result.targets,
                result.image,
            )
            self.audit(stored.state, runtime_id)
            return stored.model_copy(
                update={"image": None, "hasImage": bool(stored.image)}, deep=True
            )

    def stop(self, pause: bool = True) -> list[DesktopJob]:
        with self.lock:
            self.paused = pause
            for job in self.jobs.values():
                job.image = None
                job.targets = []
                if job.state in ("pending", "approved", "dispatched"):
                    job.state, job.message = (
                        "cancelled",
                        "Stopped; inspect again to start new work",
                    )
            return self.list_jobs()
