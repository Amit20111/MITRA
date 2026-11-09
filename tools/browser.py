"""Opt-in read-only browser adapter. No browser starts until a tool is dispatched."""

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field

from apps.api.contracts import Contract


async def stop_browser_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    if os.name == "nt":
        cleanup = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await cleanup.wait()
    else:
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), 5)
    except TimeoutError:
        process.kill()
        await process.wait()


class BrowserInput(Contract):
    url: str = Field(min_length=1, max_length=2000)


class BrowserOutput(Contract):
    url: str
    title: str
    text: str
    links: list[dict[str, str]]
    truncated: bool
    verified: bool


def canonical_url(value: str) -> str:
    if any(ord(char) <= 32 for char in value) or "\\" in value:
        raise ValueError("Browser URL contains forbidden characters")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Browser requires an HTTP(S) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Browser URL credentials and fragments are forbidden")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    authority = (
        host
        if port in (None, 80 if parsed.scheme == "http" else 443)
        else f"{host}:{port}"
    )
    return urlunsplit((parsed.scheme, authority, parsed.path or "/", parsed.query, ""))


def parse_origins(value: str) -> tuple[str, ...]:
    origins = []
    for item in value.split(","):
        if not item.strip():
            continue
        url = urlsplit(canonical_url(item.strip()))
        if url.path != "/" or url.query or "*" in url.netloc:
            raise ValueError(
                "Browser allowlist requires exact origins, without paths or wildcards"
            )
        origins.append(f"{url.scheme}://{url.netloc}")
    return tuple(dict.fromkeys(origins))


class BrowserInspector:
    def __init__(self, origins: tuple[str, ...] = ()):
        self.origins = origins
        self.lock = asyncio.Semaphore(1)

    def validate(self, value: str) -> str:
        url = canonical_url(value)
        parsed = urlsplit(url)
        if f"{parsed.scheme}://{parsed.netloc}" not in self.origins:
            raise ValueError("Browser origin is not explicitly allowlisted")
        return url

    async def inspect(self, value: str) -> BrowserOutput:
        url = self.validate(value)
        async with self.lock:
            driver = Path(__file__).with_name("browser_driver.mjs")
            process = await asyncio.create_subprocess_exec(
                "node",
                str(driver),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            payload = json.dumps({"url": url, "origins": self.origins}).encode()
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(payload), 40)
            except (TimeoutError, asyncio.CancelledError):
                await stop_browser_process(process)
                raise
            if process.returncode:
                raise ValueError(
                    "Browser inspection failed; check allowlist, browser installation, and page availability"
                )
            return BrowserOutput.model_validate_json(stdout)
