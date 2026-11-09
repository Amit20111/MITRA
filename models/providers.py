import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx

from apps.api.config import Config
from apps.api.contracts import NormalizedResponse, ToolCall

DeltaHandler = Callable[[str], Awaitable[None]]


class Provider(Protocol):
    name: str
    model: str

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
        on_delta: DeltaHandler | None = None,
    ) -> NormalizedResponse: ...


class CompatibleProvider:
    name: str

    def __init__(self, config: Config):
        self.config = config
        role = config.roles["agent"]
        self.name, self.model, self.base_url = role.provider, role.model, role.baseUrl
        self.key = config.keys["agent"].get_secret_value()
        self.slot = asyncio.Semaphore(1)

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
        on_delta: DeltaHandler | None = None,
    ) -> NormalizedResponse:
        if not self.model:
            return NormalizedResponse(
                kind="error",
                error="Agent model is not configured. Set LLM_MODEL and start llama-server.",
            )
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0,
            "max_tokens": 1024,
        }
        if self.name == "local":
            body["chat_template_kwargs"] = {"enable_thinking": self.config.thinking}
        headers = {"Authorization": "Bearer " + self.key} if self.key else {}
        attempts: list[dict[str, Any]] = []
        async with self.slot:
            for attempt in range(self.config.retries + 1):
                attempt_started = time.monotonic()
                chunks: list[dict[str, Any]] = []
                text = ""
                calls: dict[int, dict[str, str]] = {}
                usage: dict[str, Any] = {}
                try:
                    async with (  # noqa: SIM117 - keep HTTP response lifetime scoped inside the client
                        asyncio.timeout(self.config.timeout),
                        httpx.AsyncClient(
                            timeout=self.config.timeout, trust_env=False
                        ) as client,
                    ):
                        async with client.stream(
                            "POST",
                            self.base_url + "/chat/completions",
                            json=body,
                            headers=headers,
                        ) as response:
                            if response.status_code != 200:
                                raw = (await response.aread()).decode(
                                    "utf-8", errors="replace"
                                )
                                return NormalizedResponse(
                                    kind="error",
                                    error=f"Provider returned HTTP {response.status_code}; check server/model configuration.",
                                    raw={
                                        "request": body,
                                        "status": response.status_code,
                                        "body": raw,
                                        "attempts": attempts,
                                    },
                                )
                            async for line in response.aiter_lines():
                                if not line.startswith("data:"):
                                    continue
                                data = line[5:].strip()
                                if data == "[DONE]":
                                    break
                                chunk = json.loads(data)
                                chunks.append(chunk)
                                if chunk.get("usage"):
                                    usage = chunk["usage"]
                                choices = chunk.get("choices") or []
                                if not choices:
                                    continue
                                delta = choices[0].get("delta") or {}
                                content = delta.get("content") or ""
                                text += content
                                if len(text) > 32000 or len(chunks) > 10000:
                                    raise ValueError("Provider output limit exceeded")
                                if content and on_delta:
                                    await on_delta(content)
                                for call in delta.get("tool_calls") or []:
                                    part = calls.setdefault(
                                        call.get("index", 0),
                                        {"name": "", "arguments": ""},
                                    )
                                    function = call.get("function") or {}
                                    part["name"] += function.get("name") or ""
                                    part["arguments"] += function.get("arguments") or ""
                    raw_response = {
                        "request": body,
                        "chunks": chunks,
                        "text": text,
                        "calls": calls,
                        "attempts": attempts,
                    }
                    if calls:
                        if len(calls) != 1:
                            return NormalizedResponse(
                                kind="invalid",
                                raw=raw_response,
                                usage=usage,
                                error="Exactly one tool call is allowed",
                            )
                        call = next(iter(calls.values()))
                        try:
                            parsed = ToolCall(
                                name=call["name"],
                                arguments=json.loads(call["arguments"]),
                            )
                        except (ValueError, TypeError):
                            return NormalizedResponse(
                                kind="invalid",
                                raw=raw_response,
                                usage=usage,
                                error="Tool call is not valid JSON",
                            )
                        return NormalizedResponse(
                            kind="tool", tool_call=parsed, raw=raw_response, usage=usage
                        )
                    if not text.strip():
                        return NormalizedResponse(
                            kind="invalid",
                            raw=raw_response,
                            error="Provider returned neither text nor a tool call",
                        )
                    try:
                        content_json = json.loads(text)
                    except ValueError:
                        content_json = None
                    if isinstance(content_json, dict) and isinstance(
                        content_json.get("clarification"), str
                    ):
                        return NormalizedResponse(
                            kind="clarification",
                            text=content_json["clarification"],
                            raw=raw_response,
                            usage=usage,
                        )
                    return NormalizedResponse(
                        kind="final", text=text, raw=raw_response, usage=usage
                    )
                except (
                    httpx.HTTPError,
                    TimeoutError,
                    ValueError,
                    TypeError,
                    KeyError,
                    AttributeError,
                ) as error:
                    attempts.append(
                        {
                            "errorType": type(error).__name__,
                            "durationMs": (time.monotonic() - attempt_started) * 1000,
                            "chunks": chunks,
                        }
                    )
                    # Never repeat a partially delivered response, or switch providers.
                    if attempt < self.config.retries and not chunks:
                        continue
                    return NormalizedResponse(
                        kind="error",
                        error="Provider connection or response failed. Check llama-server and model configuration.",
                        raw={
                            "request": body,
                            "errorType": type(error).__name__,
                            "chunks": chunks,
                            "attempts": attempts,
                        },
                        usage=usage,
                    )
        raise RuntimeError("Unreachable provider retry state")
