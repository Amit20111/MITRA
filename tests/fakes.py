import asyncio
from typing import Any

from apps.api.contracts import NormalizedResponse, ToolCall
from models.providers import DeltaHandler


class FakeProvider:
    name = "test-only"
    model = "scripted"

    def __init__(self, responses: list[NormalizedResponse], delay: float = 0):
        self.responses = list(responses)
        self.delay = delay
        self.seen: list[list[dict[str, Any]]] = []

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        options: dict[str, Any],
        on_delta: DeltaHandler | None = None,
    ) -> NormalizedResponse:
        self.seen.append(messages)
        if options.get("denied"):
            return NormalizedResponse(
                kind="final", text="The user denied the action.", raw={"denied": True}
            )
        if self.delay:
            await asyncio.sleep(self.delay)
        result = (
            self.responses.pop(0)
            if self.responses
            else NormalizedResponse(kind="final", text="Finished.")
        )
        result.raw = {"scripted": result.model_dump(exclude={"raw"})}
        if result.text and on_delta:
            for start in range(0, len(result.text), 8):
                await on_delta(result.text[start : start + 8])
        return result


def tool(name: str, **arguments: Any) -> NormalizedResponse:
    return NormalizedResponse(
        kind="tool", tool_call=ToolCall(name=name, arguments=arguments)
    )


def final(text: str = "The requested action is verified.") -> NormalizedResponse:
    return NormalizedResponse(kind="final", text=text)
