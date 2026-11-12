import asyncio
import base64

import httpx
import pytest

from apps.api.config import Config
from apps.api.contracts import SpeechInput, TranscriptionInput
from models.voice import VoiceService


def configured(monkeypatch, handler):
    monkeypatch.setenv("MITRA_VOICE_ENABLED", "true")
    for role in ("STT", "TTS"):
        monkeypatch.setenv(f"LLM_{role}_MODEL", "test-speech")
        monkeypatch.setenv(f"LLM_{role}_BASE_URL", "http://127.0.0.1:9999/v1")
    return VoiceService(Config(), asyncio.Semaphore(1), httpx.MockTransport(handler))


def test_voice_explicit_config_and_disabled_no_network(monkeypatch):
    monkeypatch.delenv("MITRA_VOICE_ENABLED", raising=False)
    service = VoiceService(Config(), asyncio.Semaphore(1))
    assert not service.status().enabled
    with pytest.raises(ValueError, match="disabled"):
        asyncio.run(service.speak(SpeechInput(text="Hello")))
    monkeypatch.setenv("MITRA_VOICE_ENABLED", "true")
    monkeypatch.delenv("LLM_STT_MODEL", raising=False)
    assert not VoiceService(Config(), asyncio.Semaphore(1)).status().transcription


def test_speech_adapters_and_transcript_review(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path.endswith("transcriptions"):
            assert b"recording.webm" in request.content
            return httpx.Response(200, json={"text": "Create a file"})
        return httpx.Response(200, content=b"ID3synthetic-mp3")

    service = configured(monkeypatch, handle)

    async def run():
        transcript = await service.transcribe(
            TranscriptionInput(
                audio=base64.b64encode(b"fixture").decode(), mime="audio/webm"
            )
        )
        assert transcript.text == "Create a file" and transcript.reviewRequired
        audio = await service.speak(SpeechInput(text="Hello"))
        assert base64.b64decode(audio.audio) == b"ID3synthetic-mp3"

    asyncio.run(run())
    assert len(requests) == 2


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://remote.invalid"}),
        httpx.Response(500, text="secret"),
        httpx.Response(200, content=b"not-mp3"),
        httpx.Response(200, content=b"ID3" + b"a" * 4000001),
    ],
)
def test_speech_errors_limits_and_no_redirect(monkeypatch, response):
    seen = []
    service = configured(monkeypatch, lambda r: seen.append(r) or response)
    with pytest.raises(ValueError):
        asyncio.run(service.speak(SpeechInput(text="Hello")))
    assert len(seen) == 1


def test_audio_invalid_blank_transcript_and_shared_slot(monkeypatch):
    service = configured(monkeypatch, lambda _: httpx.Response(200, json={"text": " "}))

    async def run():
        with pytest.raises(ValueError):
            await service.transcribe(
                TranscriptionInput(audio="!bad", mime="audio/webm")
            )
        with pytest.raises(ValueError):
            await service.transcribe(
                TranscriptionInput(audio="YQ==", mime="audio/webm")
            )
        async with service.slot:
            with pytest.raises(ValueError, match="busy"):
                await service.speak(SpeechInput(text="Hello"))

    asyncio.run(run())


def test_voice_cancel_releases_shared_slot(monkeypatch):
    started = asyncio.Event()

    async def handler(_):
        started.set()
        await asyncio.sleep(10)
        return httpx.Response(200, content=b"ID3test")

    service = configured(monkeypatch, handler)

    async def run():
        task = asyncio.create_task(service.speak(SpeechInput(text="Hello")))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not service.slot.locked()

    asyncio.run(run())


def test_voice_api_is_review_only_and_serializes_with_agent(tmp_path, monkeypatch):
    from apps.api.main import create_app
    from models.providers import CompatibleProvider
    from tests.client import ApiClient

    for role in ("STT", "TTS"):
        monkeypatch.setenv(f"LLM_{role}_MODEL", "synthetic")
        monkeypatch.setenv(f"LLM_{role}_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("MITRA_VOICE_ENABLED", "true")
    app = create_app(tmp_path / "voice.db", workspace=tmp_path / "workspace")
    with ApiClient(app) as client:
        assert isinstance(app.state.agent.provider, CompatibleProvider)
        assert app.state.voice_service.slot is app.state.agent.provider.slot
        app.state.voice_service.transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"text": "Write private.txt"})
        )
        response = client.post(
            "/api/v1/voice/transcribe", json={"audio": "YQ==", "mime": "audio/webm"}
        )
        assert response.status_code == 200 and response.json()["reviewRequired"]
        assert client.get("/api/v1/tasks").json() == []
        invalid = client.post(
            "/api/v1/voice/transcribe",
            json={"audio": "private audio", "mime": "unknown"},
        )
        assert invalid.status_code == 422 and "private audio" not in invalid.text
        assert (
            client.post(
                "/api/v1/voice/speak",
                json={"text": "hello"},
                headers={"Origin": "https://evil.invalid"},
            ).status_code
            == 403
        )
