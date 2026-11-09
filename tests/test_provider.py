import asyncio
import json
from unittest.mock import patch

import httpx

from apps.api.config import Config
from models.providers import CompatibleProvider


def test_compatible_provider_streaming_and_thinking_off(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODEL", "test-model")
    config = Config(tmp_path)
    original = httpx.AsyncClient
    seen = []

    def handler(request):
        body = json.loads(request.content)
        assert body["chat_template_kwargs"]["enable_thinking"] is False
        assert body["parallel_tool_calls"] is False
        assert request.url.path == "/v1/chat/completions"
        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [], "usage": {"total_tokens": 2}},
        ]
        return httpx.Response(
            200,
            text="".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
            + "data: [DONE]\n\n",
        )

    async def delta(text):
        seen.append(text)

    with patch(
        "httpx.AsyncClient",
        side_effect=lambda **kwargs: original(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    ):
        result = asyncio.run(CompatibleProvider(config).generate([], [], {}, delta))
    assert result.text == "Hello"
    assert result.usage["total_tokens"] == 2
    assert seen == ["Hello"]


def test_roles_inherit_without_exposing_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODEL", "agent-model")
    monkeypatch.setenv("LLM_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_SUMMARIZER_MODEL", "future-model")
    config = Config(tmp_path)
    assert config.roles["stt"].model == "agent-model"
    assert config.roles["summarizer"].model == "future-model"
    assert not config.roles["summarizer"].implemented
    assert "secret-key" not in config.public().model_dump_json()
