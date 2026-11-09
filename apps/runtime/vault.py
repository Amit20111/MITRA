"""Current-user Windows DPAPI storage. There is no plaintext fallback."""

import ctypes
import os
import sys
import tempfile
from pathlib import Path

from apps.api.contracts import Contract, RuntimeCredential


class SavedCredential(Contract):
    api: str
    credential: RuntimeCredential


class Blob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint32), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def transform(data: bytes, decrypt: bool = False) -> bytes:
    if sys.platform != "win32":
        raise OSError("Runtime credential storage requires Windows DPAPI")
    loader = ctypes.WinDLL
    crypt = loader("crypt32", use_last_error=True)
    kernel = loader("kernel32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p if decrypt else ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(Blob),
    ]
    function.restype = ctypes.c_int
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    # CRYPTPROTECT_UI_FORBIDDEN, deliberately not CRYPTPROTECT_LOCAL_MACHINE.
    if not function(
        ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)
    ):
        raise OSError(
            "Windows could not protect/unprotect this user's runtime credential"
        )
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.memset(output.data, 0, output.size)
        kernel.LocalFree(ctypes.cast(output.data, ctypes.c_void_p))


def default_path() -> Path:
    local = os.getenv("LOCALAPPDATA")
    if not local:
        raise OSError(
            "LOCALAPPDATA is unavailable; select a credential file explicitly"
        )
    current = Path(local) / "MITRA" / "runtime.dpapi"
    legacy = Path(local) / "JARIS" / "runtime.dpapi"
    return legacy if legacy.exists() and not current.exists() else current


def save(path: Path, value: SavedCredential, replace: bool = False) -> None:
    if path.exists() and not replace:
        raise FileExistsError(
            "Credential exists; revoke it in Settings before pairing with --replace"
        )
    protected = transform(value.model_dump_json().encode())
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix="runtime-", suffix=".dpapi", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(protected)
            stream.flush()
            os.fsync(stream.fileno())
        if not replace and path.exists():
            raise FileExistsError("Credential file already exists")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load(path: Path) -> SavedCredential:
    if path.stat().st_size > 16000:
        raise ValueError("Invalid credential file")
    return SavedCredential.model_validate_json(
        transform(path.read_bytes(), decrypt=True)
    )
