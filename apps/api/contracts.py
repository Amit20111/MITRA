from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat()


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_serialization_defaults_required=True
    )


TaskStatus = Literal[
    "queued",
    "planning",
    "awaiting_approval",
    "running",
    "verifying",
    "completed",
    "failed",
    "cancelled",
    "needs_user_input",
    "paused",
]
StepStatus = Literal["pending", "attempted", "succeeded", "failed", "verified"]


class Message(Contract):
    id: str = Field(default_factory=uid)
    role: Literal["user", "assistant"]
    content: str
    createdAt: str = Field(default_factory=now)


class ToolCall(Contract):
    name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any]


class Step(Contract):
    id: str = Field(default_factory=uid)
    title: str
    tool: str
    status: StepStatus = "pending"
    detail: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    verification: str | None = None


class ToolEvent(Contract):
    id: str = Field(default_factory=uid)
    tool: str
    input: str
    output: str
    status: StepStatus
    createdAt: str = Field(default_factory=now)


class Approval(Contract):
    id: str = Field(default_factory=uid)
    taskId: str
    stepId: str
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    target: str
    action: str
    risk: Literal["high"] = "high"
    expiresAt: str
    digest: str


class Task(Contract):
    id: str = Field(default_factory=uid)
    conversationId: str
    title: str
    status: TaskStatus = "queued"
    steps: list[Step] = Field(default_factory=list)
    events: list[ToolEvent] = Field(default_factory=list)
    approval: Approval | None = None
    summary: str | None = None
    draft: str | None = None
    provider: str
    model: str
    messageId: str = Field(default_factory=uid)
    outline: list[str] = Field(default_factory=list)
    iterations: int = 0
    resumeState: TaskStatus | None = None


class Conversation(Contract):
    id: str = Field(default_factory=uid)
    title: str = "New conversation"
    messages: list[Message] = Field(default_factory=list)
    task: Task | None = None


class SendMessage(Contract):
    content: str = Field(min_length=1, max_length=8000)
    requestId: UUID


class Decision(Contract):
    taskId: UUID
    decision: Literal["approve", "reject"]
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class RoleConfig(Contract):
    provider: Literal["local", "hosted"] = "local"
    baseUrl: str
    model: str
    configured: bool
    implemented: bool = False


class Settings(Contract):
    browserInteraction: bool = False
    browserEnabled: bool = False
    browserOrigins: list[str] = Field(default_factory=list)
    roles: dict[str, RoleConfig]
    workspace: str
    maxSteps: int
    retries: int
    approvalSeconds: int
    thinking: bool
    localRuntime: str = "not connected"


class Health(Contract):
    status: str = "ok"
    provider: str
    model: str
    mode: str = "local"


class RuntimeStatus(Contract):
    connected: bool = False
    paired: bool = False
    runtimeId: str | None = None
    name: str | None = None
    lastSeen: str | None = None
    credentialExpiresAt: str | None = None
    leaseSeconds: int = 15
    capabilities: list[str] = Field(default_factory=list)
    message: str = "No Windows runtime paired."


class PairingChallenge(Contract):
    pairingId: str
    pairingCode: str = Field(repr=False)
    expiresAt: str


class PairingClaim(Contract):
    pairingId: UUID
    code: str = Field(min_length=20, max_length=100, repr=False)
    name: str = Field(min_length=1, max_length=60, pattern=r".*\S.*")
    platform: Literal["windows"] = "windows"
    protocolVersion: Literal[1] = 1


class RuntimeCredential(Contract):
    runtimeId: str
    token: str = Field(repr=False)
    expiresAt: str
    heartbeatSeconds: int = 5


class RuntimeHeartbeat(Contract):
    protocolVersion: Literal[1] = 1
    runtimeVersion: Literal["0.1.0"] = "0.1.0"
    desktopEnabled: bool = False


class RuntimeRevoke(Contract):
    runtimeId: UUID


class RuntimeAudit(Contract):
    id: int
    event: str
    runtimeId: str | None
    timestamp: str


EventType = Literal[
    "message.created",
    "message.delta",
    "task.created",
    "task.status_changed",
    "plan.created",
    "step.started",
    "approval.requested",
    "approval.decided",
    "tool.started",
    "tool.completed",
    "tool.failed",
    "step.verified",
    "task.completed",
    "task.failed",
    "task.cancelled",
]


class TaskEvent(Contract):
    id: int
    type: EventType
    taskId: str
    conversationId: str
    timestamp: str
    payload: Task
    delta: str | None = None


class NormalizedResponse(Contract):
    kind: Literal["final", "clarification", "tool", "invalid", "error"]
    text: str = ""
    tool_call: ToolCall | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Trace(Contract):
    id: str = Field(default_factory=uid)
    taskId: str
    stepId: str | None = None
    kind: Literal["model", "tool", "approval"]
    request: dict[str, Any]
    rawResponse: dict[str, Any] = Field(default_factory=dict)
    parsed: dict[str, Any] | None = None
    validationErrors: list[str] = Field(default_factory=list)
    approvalState: str | None = None
    durationMs: float = 0
    usage: dict[str, Any] = Field(default_factory=dict)
    outcome: str
    verification: str | None = None
    createdAt: str = Field(default_factory=now)


class DesktopTarget(Contract):
    id: str = Field(max_length=80)
    title: str = Field(max_length=256)
    processId: int


class DesktopRequest(Contract):
    action: Literal["list_windows", "screenshot", "focus"]
    targetId: str | None = Field(default=None, max_length=80)


class DesktopJob(Contract):
    hasImage: bool = False
    id: str = Field(default_factory=uid)
    runtimeId: str
    action: Literal["list_windows", "screenshot", "focus"]
    targetId: str | None = None
    targetTitle: str = "Visible windows"
    digest: str
    expiresAt: str
    state: Literal[
        "pending", "approved", "dispatched", "completed", "failed", "cancelled"
    ] = "pending"
    message: str = "Review the exact operation before approval."
    targets: list[DesktopTarget] = Field(default_factory=list, max_length=50)
    image: str | None = Field(default=None, max_length=12000000, repr=False)


class DesktopDecision(Contract):
    digest: str
    approve: bool


class DesktopResult(Contract):
    success: bool
    message: str = Field(max_length=300)
    targets: list[DesktopTarget] = Field(default_factory=list, max_length=50)
    image: str | None = Field(default=None, max_length=12000000, repr=False)


class MemoryInput(Contract):
    key: str = Field(min_length=2, max_length=80, pattern=r".*\S.*")
    content: str = Field(min_length=1, max_length=1000, pattern=r".*\S.*")
    conversationId: UUID | None = None
    confirmed: bool = True


class MemoryRecord(MemoryInput):
    id: str = Field(default_factory=uid)
    source: Literal["user"] = "user"
    createdAt: str = Field(default_factory=now)
    updatedAt: str = Field(default_factory=now)
    revision: int = 1


class MemoryUpdate(MemoryInput):
    revision: int = Field(ge=1)


class VoiceStatus(Contract):
    enabled: bool
    transcription: bool
    speech: bool
    message: str
    maxRecordingSeconds: int = 30


class TranscriptionInput(Contract):
    audio: str = Field(min_length=1, max_length=2800000, repr=False)
    mime: Literal["audio/webm", "audio/ogg", "audio/wav", "audio/mp4"]


class Transcript(Contract):
    text: str = Field(max_length=8000)
    reviewRequired: bool = True


class SpeechInput(Contract):
    text: str = Field(min_length=1, max_length=2000, pattern=r".*\S.*")


class SpeechAudio(Contract):
    audio: str = Field(repr=False)
    mime: Literal["audio/mpeg"] = "audio/mpeg"


class LaunchCode(Contract):
    code: str = Field(repr=False)
    expiresAt: str


class LaunchRedeem(Contract):
    code: str = Field(min_length=20, max_length=100, pattern=r"^[A-Za-z0-9_-]+$", repr=False)


class SessionGrant(Contract):
    token: str = Field(repr=False)
    expiresAt: str


class SessionStatus(Contract):
    authenticated: bool = True
    expiresAt: str
    activeSessions: int
