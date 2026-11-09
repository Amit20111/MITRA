import asyncio
import base64
import ipaddress
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select

from agent.orchestrator import Orchestrator
from agent.state import TERMINAL
from apps.api.config import ROOT, Config
from apps.api.contracts import (
    Approval,
    Conversation,
    Decision,
    DesktopDecision,
    DesktopJob,
    DesktopRequest,
    DesktopResult,
    Health,
    MemoryInput,
    MemoryRecord,
    MemoryUpdate,
    PairingChallenge,
    PairingClaim,
    RuntimeAudit,
    RuntimeCredential,
    RuntimeHeartbeat,
    RuntimeRevoke,
    RuntimeStatus,
    SendMessage,
    Settings,
    SpeechAudio,
    SpeechInput,
    Task,
    TaskEvent,
    Transcript,
    TranscriptionInput,
    VoiceStatus,
)
from apps.api.desktop_service import DesktopService
from apps.api.runtime_service import RuntimeService
from memory.records import MemoryService
from memory.store import Store, conversations, tasks
from models.providers import CompatibleProvider, Provider
from models.voice import VoiceService
from observability.logging import log_request
from security.redaction import Redactor

load_dotenv(ROOT / ".env")


def create_app(
    database: Path | None = None,
    provider: Provider | None = None,
    workspace: Path | None = None,
) -> FastAPI:
    config = Config(workspace, database)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        redactor = Redactor([key.get_secret_value() for key in config.keys.values()])
        store = Store(config.database, redactor)
        store.recover()
        app.state.runtime_service = RuntimeService(store)
        app.state.desktop_service = DesktopService(app.state.runtime_service)
        app.state.memory_service = MemoryService(store)
        app.state.agent = Orchestrator(
            store, provider or CompatibleProvider(config), config
        )
        selected_provider = service().provider
        slot = (
            selected_provider.slot
            if isinstance(selected_provider, CompatibleProvider)
            else asyncio.Semaphore(1)
        )
        app.state.voice_service = VoiceService(config, slot)

        async def cleanup_desktop() -> None:
            while True:
                await asyncio.sleep(5)
                desktop_service().list_jobs()

        cleanup = asyncio.create_task(cleanup_desktop())
        try:
            yield
        finally:
            cleanup.cancel()
            try:
                await cleanup
            except asyncio.CancelledError:
                pass
        await service().close()
        store.close()

    app = FastAPI(title="MITRA API", version="0.3.0", lifespan=lifespan)
    app.middleware("http")(log_request)

    def service() -> Orchestrator:
        return cast(Orchestrator, app.state.agent)

    def runtime_service() -> RuntimeService:
        return cast(RuntimeService, app.state.runtime_service)

    def desktop_service() -> DesktopService:
        return cast(DesktopService, app.state.desktop_service)

    def memories() -> MemoryService:
        return cast(MemoryService, app.state.memory_service)

    @app.middleware("http")
    async def origin_guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        if request.url.path.startswith("/api/v1/runtime/"):
            try:
                authority = urlsplit("http://" + request.headers.get("host", ""))
                host = (
                    authority.hostname
                    if not (
                        authority.username
                        or authority.password
                        or authority.path
                        or authority.query
                        or authority.fragment
                    )
                    else None
                )
                _ = authority.port
            except ValueError:
                host = None
            try:
                local_peer = bool(
                    request.client
                    and ipaddress.ip_address(request.client.host).is_loopback
                )
            except ValueError:
                local_peer = False
            if not local_peer or host not in ("127.0.0.1", "localhost", "::1"):
                return JSONResponse(
                    {"detail": "Runtime API requires a loopback host"}, status_code=403
                )
            native = request.url.path.endswith(
                (
                    "/claim",
                    "/heartbeat",
                    "/disconnect",
                    "/poll",
                    "/authorize",
                    "/result",
                )
            )
            if native and origin:
                return JSONResponse(
                    {"detail": "Runtime credentials are for the native helper only"},
                    status_code=403,
                )
        if origin and origin not in {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            config.web_origin,
        }:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/runtime/"):
            response.headers["Cache-Control"] = "no-store"
        if request.url.path.startswith(("/api/v1/voice/", "/api/v1/memories")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(PermissionError)
    async def denied(request: Request, error: PermissionError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=401)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, error: RequestValidationError) -> Response:
        if request.url.path.startswith(("/api/v1/runtime/", "/api/v1/voice/")):
            return JSONResponse({"detail": "Invalid request"}, status_code=422)
        from fastapi.exception_handlers import request_validation_exception_handler

        return await request_validation_exception_handler(request, error)

    @app.exception_handler(LookupError)
    async def missing(request: Request, error: LookupError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=404)

    @app.exception_handler(ValueError)
    async def conflict(request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.get("/api/v1/health", response_model=Health)
    def health() -> Health:
        return Health(provider=service().provider.name, model=service().provider.model)

    @app.get("/api/v1/settings", response_model=Settings)
    def settings() -> Settings:
        result = config.public()
        state = runtime_service().status()
        result.localRuntime = (
            "connected"
            if state.connected
            else "paired / offline"
            if state.paired
            else "not paired"
        )
        return result

    @app.get("/api/v1/runtime/status", response_model=RuntimeStatus)
    def runtime() -> RuntimeStatus:
        return runtime_service().status()

    @app.post("/api/v1/runtime/pairing", response_model=PairingChallenge)
    def begin_pairing() -> PairingChallenge:
        return runtime_service().issue()

    @app.post("/api/v1/runtime/pairing/claim", response_model=RuntimeCredential)
    def claim_pairing(body: PairingClaim) -> RuntimeCredential:
        return runtime_service().claim(body)

    @app.post("/api/v1/runtime/{identity}/heartbeat", response_model=RuntimeStatus)
    def runtime_heartbeat(
        identity: UUID,
        body: RuntimeHeartbeat,
        authorization: str | None = Header(default=None),
    ) -> RuntimeStatus:
        runtime_service().heartbeat(str(identity), authorization)
        runtime_service().desktop_enabled[str(identity)] = body.desktopEnabled
        return runtime_service().status()

    @app.post("/api/v1/runtime/{identity}/disconnect", response_model=RuntimeStatus)
    def runtime_disconnect(
        identity: UUID, authorization: str | None = Header(default=None)
    ) -> RuntimeStatus:
        return runtime_service().disconnect(str(identity), authorization)

    @app.post("/api/v1/runtime/revoke", response_model=RuntimeStatus)
    def runtime_revoke(body: RuntimeRevoke) -> RuntimeStatus:
        return runtime_service().revoke(str(body.runtimeId))

    @app.get("/api/v1/runtime/audit", response_model=list[RuntimeAudit])
    def runtime_history() -> list[RuntimeAudit]:
        return runtime_service().history()

    def voice_service() -> VoiceService:
        return cast(VoiceService, app.state.voice_service)

    @app.get("/api/v1/voice/status", response_model=VoiceStatus)
    def voice_status() -> VoiceStatus:
        return voice_service().status()

    async def voice_work(
        request: Request, work: Awaitable[Transcript | SpeechAudio]
    ) -> Transcript | SpeechAudio:
        task = asyncio.ensure_future(work)
        try:
            while not task.done():
                if await request.is_disconnected():
                    raise HTTPException(499, "Voice request cancelled")
                await asyncio.wait({task}, timeout=0.1)
            return await task
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @app.post("/api/v1/voice/transcribe", response_model=Transcript)
    async def voice_transcribe(
        request: Request, body: TranscriptionInput
    ) -> Transcript | SpeechAudio:
        return await voice_work(request, voice_service().transcribe(body))

    @app.post("/api/v1/voice/speak", response_model=SpeechAudio)
    async def voice_speak(
        request: Request, body: SpeechInput
    ) -> Transcript | SpeechAudio:
        return await voice_work(request, voice_service().speak(body))

    @app.get("/api/v1/memories", response_model=list[MemoryRecord])
    def memory_list() -> list[MemoryRecord]:
        return memories().list_records()

    @app.post("/api/v1/memories", response_model=MemoryRecord)
    def memory_create(body: MemoryInput) -> MemoryRecord:
        return memories().save(body)

    @app.post("/api/v1/memories/{identity}/update", response_model=MemoryRecord)
    def memory_update(identity: UUID, body: MemoryUpdate) -> MemoryRecord:
        return memories().save(body, str(identity))

    @app.post("/api/v1/memories/{identity}/delete", response_model=list[MemoryRecord])
    def memory_delete(identity: UUID) -> list[MemoryRecord]:
        memories().delete(str(identity))
        return memories().list_records()

    @app.get("/api/v1/runtime/desktop/jobs", response_model=list[DesktopJob])
    def desktop_jobs() -> list[DesktopJob]:
        return desktop_service().list_jobs()

    @app.get("/api/v1/runtime/desktop/{identity}/image")
    def desktop_image(identity: UUID) -> Response:
        desktop = desktop_service()
        with desktop.lock:
            desktop.expire()
            image = desktop.get(str(identity)).image
            if not image:
                raise LookupError("Capture expired or cleared")
            return Response(
                base64.b64decode(image),
                media_type="image/bmp",
                headers={
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )

    @app.post("/api/v1/runtime/desktop/jobs", response_model=DesktopJob)
    def desktop_create(body: DesktopRequest) -> DesktopJob:
        return desktop_service().create(body)

    @app.post("/api/v1/runtime/desktop/{identity}/decision", response_model=DesktopJob)
    def desktop_decide(identity: UUID, body: DesktopDecision) -> DesktopJob:
        return desktop_service().decide(str(identity), body)

    @app.post("/api/v1/runtime/desktop/stop", response_model=list[DesktopJob])
    def desktop_stop() -> list[DesktopJob]:
        return desktop_service().stop()

    @app.post("/api/v1/runtime/desktop/enable", response_model=list[DesktopJob])
    def desktop_enable() -> list[DesktopJob]:
        return desktop_service().stop(False)

    @app.post("/api/v1/runtime/{runtime_id}/poll", response_model=DesktopJob | None)
    def desktop_poll(
        runtime_id: UUID, authorization: str | None = Header(default=None)
    ) -> DesktopJob | None:
        return desktop_service().poll(str(runtime_id), authorization)

    @app.post(
        "/api/v1/runtime/{runtime_id}/{identity}/authorize", response_model=DesktopJob
    )
    def desktop_authorize(
        runtime_id: UUID,
        identity: UUID,
        authorization: str | None = Header(default=None),
    ) -> DesktopJob:
        return desktop_service().authorize(
            str(runtime_id), str(identity), authorization
        )

    @app.post(
        "/api/v1/runtime/{runtime_id}/{identity}/result", response_model=DesktopJob
    )
    def desktop_result(
        runtime_id: UUID,
        identity: UUID,
        body: DesktopResult,
        authorization: str | None = Header(default=None),
    ) -> DesktopJob:
        return desktop_service().finish(
            str(runtime_id), str(identity), authorization, body
        )

    @app.get("/api/v1/conversations", response_model=list[Conversation])
    def list_conversations() -> list[Conversation]:
        with service().store.transaction() as db:
            return [
                Conversation.model_validate(row)
                for row in db.execute(select(conversations.c.payload)).scalars()
            ][::-1]

    @app.post("/api/v1/conversations", response_model=Conversation, status_code=201)
    def create_conversation() -> Conversation:
        conversation = Conversation()
        with service().store.transaction() as db:
            service().store.save_conversation(db, conversation)
        return conversation

    @app.get("/api/v1/conversations/{identity}", response_model=Conversation)
    def conversation(identity: UUID) -> Conversation:
        with service().store.transaction() as db:
            return service().store.conversation(db, str(identity))

    @app.post(
        "/api/v1/conversations/{identity}/messages",
        response_model=Conversation,
        status_code=202,
    )
    async def message(identity: UUID, body: SendMessage) -> Conversation:
        return service().submit(str(identity), body.content, str(body.requestId))

    @app.get("/api/v1/tasks", response_model=list[Task])
    def list_tasks() -> list[Task]:
        with service().store.transaction() as db:
            return [
                Task.model_validate(row)
                for row in db.execute(select(tasks.c.payload)).scalars()
            ][::-1]

    @app.get("/api/v1/tasks/{identity}", response_model=Task)
    def task(identity: UUID) -> Task:
        return service().snapshot(str(identity))

    @app.get("/api/v1/approvals/pending", response_model=list[Approval])
    def pending() -> list[Approval]:
        return [
            item.approval
            for item in list_tasks()
            if item.approval
            and item.approval.status == "pending"
            and item.status == "awaiting_approval"
        ]

    @app.post("/api/v1/approvals/{identity}/decision", response_model=Task)
    async def decide(identity: UUID, body: Decision) -> Task:
        return await service().decide(str(identity), body)

    @app.post("/api/v1/tasks/{identity}/{action}", response_model=Task)
    async def control(
        identity: UUID, action: Literal["pause", "resume", "cancel"]
    ) -> Task:
        return await service().control(str(identity), action)

    @app.get("/api/v1/tasks/{identity}/events/history", response_model=list[TaskEvent])
    def history(identity: UUID, after: int = Query(default=0, ge=0)) -> list[TaskEvent]:
        task(identity)
        return service().store.event_rows(str(identity), after)

    @app.get("/api/v1/tasks/{identity}/events")
    async def events(
        identity: UUID,
        request: Request,
        after: int = Query(default=0, ge=0),
        last_event_id: str | None = Header(default=None),
    ) -> StreamingResponse:
        task(identity)
        try:
            cursor = max(0, int(last_event_id or after))
        except ValueError:
            raise HTTPException(400, "Invalid event cursor") from None

        async def stream() -> AsyncIterator[str]:
            nonlocal cursor
            while not await request.is_disconnected():
                for event in service().store.event_rows(str(identity), cursor):
                    cursor = event.id
                    yield f"id: {cursor}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
                if task(identity).status in TERMINAL:
                    for event in service().store.event_rows(str(identity), cursor):
                        cursor = event.id
                        yield f"id: {cursor}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.2)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Content-Encoding": "identity",
            },
        )

    return app


app = create_app()
