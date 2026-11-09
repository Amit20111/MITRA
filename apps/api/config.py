import os
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from pydantic import SecretStr

from apps.api.contracts import RoleConfig, Settings
from tools.browser import parse_origins

ROOT = Path(__file__).resolve().parents[2]


class Config:
    def __init__(self, workspace: Path | None = None, database: Path | None = None):
        self.browser_origins = parse_origins(os.getenv("MITRA_BROWSER_ORIGINS", ""))
        self.browser_interaction = (
            bool(self.browser_origins)
            and os.getenv("MITRA_BROWSER_INTERACTION", "false").lower() == "true"
        )
        self.web_origin = os.getenv("MITRA_WEB_ORIGIN", "http://127.0.0.1:3000")
        if urlparse(self.web_origin).hostname not in ("localhost", "127.0.0.1"):
            raise ValueError("Web origin must be loopback for this local-only slice")
        self.workspace = (
            workspace or Path(os.getenv("MITRA_WORKSPACE", str(ROOT / "workspace")))
        ).resolve()
        current_database = ROOT / ".data" / "mitra-slice1.db"
        legacy_database = ROOT / ".data" / "jaris-slice1.db"
        default_database = (
            legacy_database
            if legacy_database.exists() and not current_database.exists()
            else current_database
        )
        self.database = database or Path(
            os.getenv("MITRA_DATABASE", str(default_database))
        )
        self.max_steps = max(1, min(8, int(os.getenv("MITRA_MAX_STEPS", "8"))))
        self.retries = max(0, min(1, int(os.getenv("MITRA_STEP_RETRIES", "1"))))
        self.approval_seconds = max(1, int(os.getenv("MITRA_APPROVAL_SECONDS", "600")))
        self.timeout = max(1, min(300, float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))))
        self.thinking = os.getenv("LLM_THINKING", "false").lower() == "true"
        self.keys: dict[str, SecretStr] = {}
        self.roles: dict[str, RoleConfig] = {}
        base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
        model = os.getenv("LLM_MODEL", "")
        key = os.getenv("LLM_API_KEY", "")
        for role in ("agent", "summarizer", "embedder", "stt", "tts"):
            prefix = "LLM_" + role.upper() + "_"
            fallback = self.roles.get("agent")
            role_base = os.getenv(
                prefix + "BASE_URL", fallback.baseUrl if fallback else base
            ).rstrip("/")
            role_model = os.getenv(
                prefix + "MODEL", fallback.model if fallback else model
            )
            provider = os.getenv(
                prefix + "PROVIDER", fallback.provider if fallback else "local"
            )
            if provider not in ("local", "hosted"):
                raise ValueError("Provider must be local or hosted")
            parsed = urlparse(role_base)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError(
                    "Credentials and query parameters are not allowed in provider URLs"
                )
            if provider == "local" and parsed.hostname not in (
                "localhost",
                "127.0.0.1",
                "::1",
            ):
                raise ValueError(
                    "Local providers must use loopback. Select hosted explicitly for remote endpoints."
                )
            if parsed.scheme not in ("http", "https") or (
                provider == "hosted" and parsed.scheme != "https"
            ):
                raise ValueError("Hosted providers require HTTPS")
            role_key = os.getenv(
                prefix + "API_KEY",
                self.keys["agent"].get_secret_value() if fallback else key,
            )
            self.keys[role] = SecretStr(role_key)
            self.roles[role] = RoleConfig(
                provider=cast(Literal["local", "hosted"], provider),
                baseUrl=role_base,
                model=role_model,
                configured=bool(role_model),
                implemented=role in ("agent", "stt", "tts"),
            )

    def public(self) -> Settings:
        return Settings(
            roles=self.roles,
            workspace=str(self.workspace),
            maxSteps=self.max_steps,
            retries=self.retries,
            approvalSeconds=self.approval_seconds,
            thinking=self.thinking,
            browserOrigins=list(self.browser_origins),
            browserEnabled=bool(self.browser_origins),
            browserInteraction=self.browser_interaction,
        )
