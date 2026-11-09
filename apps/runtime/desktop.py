"""Narrow Win32 observation and focus adapter; no arbitrary input injection."""

import base64
import ctypes
import hashlib
import json
import struct
import subprocess
import sys
import time
from ctypes import wintypes as w
from datetime import datetime
from typing import Any
from uuid import uuid4

from apps.api.contracts import DesktopJob, DesktopResult, DesktopTarget


def user32() -> Any:
    if sys.platform != "win32":
        raise OSError("Desktop operations require Windows")
    api = ctypes.WinDLL("user32", use_last_error=True)
    for name in ("GetForegroundWindow", "GetDC"):
        getattr(api, name).restype = w.HWND
    api.GetDC.argtypes = [w.HWND]
    api.ReleaseDC.argtypes = [w.HWND, w.HDC]
    api.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    api.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    api.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    for name in ("IsWindowVisible", "IsIconic", "SetForegroundWindow"):
        getattr(api, name).argtypes = [w.HWND]
    api.GetClientRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    api.PrintWindow.argtypes = [w.HWND, w.HDC, w.UINT]
    return api


def identity(hwnd: int) -> tuple[int, str, str, int, int]:
    api = user32()
    pid, title, klass, rect = (
        w.DWORD(),
        ctypes.create_unicode_buffer(257),
        ctypes.create_unicode_buffer(257),
        w.RECT(),
    )
    if not api.IsWindowVisible(hwnd) or api.IsIconic(hwnd):
        raise ValueError("Window closed, hidden or minimized")
    api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    api.GetWindowTextW(hwnd, title, 257)
    api.GetClassNameW(hwnd, klass, 257)
    if not api.GetClientRect(hwnd, ctypes.byref(rect)) or not pid.value:
        raise ValueError("Window unavailable")
    return pid.value, title.value, klass.value, rect.right, rect.bottom


def capture(hwnd: int) -> bytes:
    """Runs in a time-limited child; PrintWindow can otherwise block indefinitely."""
    api = user32()
    _, _, _, width, height = identity(hwnd)
    if not (1 <= width <= 1920 and 1 <= height <= 1080):
        raise ValueError("Window exceeds capture limit (1920 x 1080)")
    if sys.platform != "win32":
        raise OSError("Windows required")
    gdi = ctypes.WinDLL("gdi32", use_last_error=True)
    gdi.CreateCompatibleDC.argtypes = [w.HDC]
    gdi.CreateCompatibleDC.restype = w.HDC
    gdi.CreateCompatibleBitmap.argtypes = [w.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = w.HBITMAP
    gdi.SelectObject.argtypes = [w.HDC, w.HANDLE]
    gdi.SelectObject.restype = w.HANDLE
    gdi.DeleteObject.argtypes = [w.HANDLE]
    gdi.DeleteDC.argtypes = [w.HDC]
    gdi.GetDIBits.argtypes = [
        w.HDC,
        w.HBITMAP,
        w.UINT,
        w.UINT,
        ctypes.c_void_p,
        ctypes.c_void_p,
        w.UINT,
    ]
    dc = api.GetDC(hwnd)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        if not all((dc, memory, bitmap, old)) or not api.PrintWindow(hwnd, memory, 1):
            raise OSError("Window capture refused")
        gdi.SelectObject(memory, old)
        old = None
        size = width * height * 4
        header = struct.pack(
            "<IiiHHIIiiII", 40, width, height, 1, 32, 0, size, 0, 0, 0, 0
        )
        info = ctypes.create_string_buffer(header)
        pixels = ctypes.create_string_buffer(size)
        if gdi.GetDIBits(memory, bitmap, 0, height, pixels, info, 0) != height:
            raise OSError("Incomplete capture")
        return struct.pack("<2sIHHI", b"BM", 54 + size, 0, 0, 54) + header + pixels.raw
    finally:
        if old:
            gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        api.ReleaseDC(hwnd, dc)


class NativeDesktop:
    def __init__(self) -> None:
        self.targets: dict[str, tuple[int, tuple[int, str, str, int, int], float]] = {}
        self.used: set[str] = set()

    def inspect(self) -> list[DesktopTarget]:
        self.targets.clear()
        api = user32()
        if sys.platform != "win32":
            raise OSError("Windows required")
        callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        output: list[DesktopTarget] = []

        def visit(hwnd: int, _: int) -> bool:
            if len(output) >= 50:
                return False
            try:
                signature = identity(hwnd)
                if signature[1] and signature[3] > 0 and signature[4] > 0:
                    token = str(uuid4())
                    self.targets[token] = (hwnd, signature, time.monotonic() + 120)
                    output.append(
                        DesktopTarget(
                            id=token, title=signature[1], processId=signature[0]
                        )
                    )
            except (OSError, ValueError):
                pass
            return True

        callback = callback_type(visit)
        api.EnumWindows.argtypes = [callback_type, w.LPARAM]
        api.EnumWindows(callback, 0)
        return output

    def execute(self, job: DesktopJob) -> DesktopResult:
        expected = hashlib.sha256(
            json.dumps(
                {"action": job.action, "targetId": job.targetId}, sort_keys=True
            ).encode()
        ).hexdigest()
        if (
            job.state != "dispatched"
            or job.digest != expected
            or job.id in self.used
            or datetime.fromisoformat(job.expiresAt).timestamp() <= time.time()
        ):
            raise ValueError("Unapproved, expired, modified or repeated operation")
        if len(self.used) >= 1000:
            raise ValueError("Restart helper after 1000 operations")
        self.used.add(job.id)
        if job.action == "list_windows":
            return DesktopResult(
                success=True,
                message="Visible windows inspected; targets expire in two minutes",
                targets=self.inspect(),
            )
        target = self.targets.get(job.targetId or "")
        if not target:
            raise ValueError("Unknown target; inspect again")
        hwnd, signature, deadline = target
        if (
            time.monotonic() >= deadline
            or identity(hwnd) != signature
            or job.targetTitle != signature[1]
        ):
            raise ValueError("Window changed; inspect and approve again")
        if job.action == "focus":
            api = user32()
            api.SetForegroundWindow(hwnd)
            verified = api.GetForegroundWindow() == hwnd and identity(hwnd) == signature
            return DesktopResult(
                success=verified,
                message="Selected window focus verified"
                if verified
                else "Windows refused foreground activation",
            )
        # Fixed module entry point, no shell, maximum three seconds and 9 MB image.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apps.runtime.desktop",
                str(hwnd),
                json.dumps(signature),
            ],
            capture_output=True,
            timeout=3,
            check=False,
        )
        if (
            result.returncode
            or not result.stdout.startswith(b"BM")
            or len(result.stdout) > 9000000
            or identity(hwnd) != signature
        ):
            raise ValueError("Capture failed or target changed")
        return DesktopResult(
            success=True,
            message="Selected window client-area image captured; some apps render blank/protected content",
            image=base64.b64encode(result.stdout).decode(),
        )


if __name__ == "__main__":
    try:
        handle = int(sys.argv[1])
        if list(identity(handle)) != json.loads(sys.argv[2]):
            raise ValueError("Target changed")
        sys.stdout.buffer.write(capture(handle))
    except (OSError, ValueError):
        raise SystemExit(1) from None
