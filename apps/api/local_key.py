"""Per-install local key shared only by the API and the trusted Next.js server.

The key lives in the current user's profile, never in the repository, the
frontend bundle or the environment of the browser. Derived web keys let the
Next.js server forward browser requests without ever forwarding the raw key.
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

KEY_NAME = "local-api.key"
WEB_LABEL = b"mitra-web-v1"
_FORMAT = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
logger = logging.getLogger("mitra.security")


def secret_dir() -> Path:
    configured = os.getenv("MITRA_SECRET_DIR")
    if configured:
        return Path(configured)
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "MITRA"
    state = os.getenv("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "mitra"


@lru_cache(maxsize=1)
def _current_sid() -> str | None:
    try:
        output = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r'"(S-1-[0-9-]+)"', output)
    return match.group(1) if match else None


def restrict(path: Path) -> bool:
    """Limit the key file to the current user. Returns whether it was applied."""
    if sys.platform != "win32":
        os.chmod(path, 0o600)
        return True
    sid = _current_sid()
    if sid is None:
        return False
    try:
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:F"],
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def load_or_create(directory: Path | None = None) -> str:
    folder = directory or secret_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / KEY_NAME
    if not path.exists():
        # Write and restrict a private temporary file, then publish it with an
        # exclusive hard link so readers never observe a partial or unrestricted key.
        key = secrets.token_urlsafe(32)
        temporary = folder / f".{KEY_NAME}.{secrets.token_hex(8)}.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                handle.write(key)
            if not restrict(temporary):
                logger.warning(
                    "Could not restrict %s to the current user; it relies on the "
                    "parent directory's permissions",
                    path,
                )
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    value = path.read_text(encoding="ascii").strip()
    if not _FORMAT.fullmatch(value):
        raise RuntimeError(
            f"Local API key at {path} is malformed. Stop MITRA, delete the file "
            "and restart the API to create a new one."
        )
    return value


def web_key(key: str) -> str:
    return hmac.new(key.encode(), WEB_LABEL, hashlib.sha256).hexdigest()
