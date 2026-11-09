"""Explicit opt-in speech endpoints, bounded payloads, shared inference slot."""

import asyncio
import base64
import json
import os
from typing import Any

import httpx

from apps.api.config import Config
from apps.api.contracts import (
    SpeechAudio,
    SpeechInput,
    Transcript,
    TranscriptionInput,
    VoiceStatus,
)


class VoiceService:
    def __init__(
        self,
        config: Config,
        slot: asyncio.Semaphore,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.config, self.slot, self.transport = config, slot, transport
        self.enabled = os.getenv("MITRA_VOICE_ENABLED", "false").lower() == "true"
        self.ready = {
            role: self.enabled
            and bool(os.getenv("LLM_" + role.upper() + "_BASE_URL"))
            and bool(os.getenv("LLM_" + role.upper() + "_MODEL"))
            for role in ("stt", "tts")
        }
        self.voice = os.getenv("MITRA_TTS_VOICE", "alloy")

    def status(self) -> VoiceStatus:
        return VoiceStatus(
            enabled=self.enabled,
            transcription=self.ready["stt"],
            speech=self.ready["tts"],
            message="Voice uses explicitly configured speech providers. Recordings/text are sent only on request; review transcripts before sending."
            if self.enabled
            else "Voice disabled. Configure speech providers and MITRA_VOICE_ENABLED=true; no model starts automatically.",
        )

    async def call(self, role: str, endpoint: str, limit: int, **kwargs: Any) -> bytes:
        if not self.ready[role]:
            raise ValueError("Speech provider is disabled or not explicitly configured")
        if self.slot.locked():
            raise ValueError(
                "Inference is busy; wait for the current model/voice request"
            )
        model = self.config.roles[role]
        key = self.config.keys[role].get_secret_value()
        headers = {"Authorization": "Bearer " + key} if key else {}
        async with self.slot:
            try:
                async with (  # noqa: SIM117 - bound response lifetime inside client
                    asyncio.timeout(45),
                    httpx.AsyncClient(
                        timeout=40,
                        trust_env=False,
                        follow_redirects=False,
                        transport=self.transport,
                    ) as client,
                ):
                    async with client.stream(
                        "POST", model.baseUrl + endpoint, headers=headers, **kwargs
                    ) as response:
                        if response.status_code != 200:
                            raise ValueError("Speech provider refused the request")
                        output = bytearray()
                        async for chunk in response.aiter_bytes():
                            output.extend(chunk)
                            if len(output) > limit:
                                raise ValueError("Speech response exceeds limit")
                        return bytes(output)
            except (httpx.HTTPError, TimeoutError) as error:
                raise ValueError("Speech provider unavailable or timed out") from error

    async def transcribe(self, body: TranscriptionInput) -> Transcript:
        try:
            audio = base64.b64decode(body.audio, validate=True)
        except ValueError as error:
            raise ValueError("Invalid audio encoding") from error
        if not 1 <= len(audio) <= 2000000:
            raise ValueError("Audio exceeds two MB limit")
        extension = body.mime.split("/")[1]
        data = await self.call(
            "stt",
            "/audio/transcriptions",
            40000,
            files={"file": ("recording." + extension, audio, body.mime)},
            data={"model": self.config.roles["stt"].model},
        )
        try:
            text = json.loads(data)["text"]
            if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                raise ValueError("Unclear or oversized transcription; try again")
            return Transcript(text=text.strip())
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                "Speech provider returned an invalid transcript"
            ) from error

    async def speak(self, body: SpeechInput) -> SpeechAudio:
        data = await self.call(
            "tts",
            "/audio/speech",
            4000000,
            json={
                "model": self.config.roles["tts"].model,
                "input": body.text,
                "voice": self.voice,
                "response_format": "mp3",
            },
        )
        if not data or not (
            data.startswith(b"ID3")
            or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224)
        ):
            raise ValueError("Speech provider did not return MP3 audio")
        return SpeechAudio(audio=base64.b64encode(data).decode())
