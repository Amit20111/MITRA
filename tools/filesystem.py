import hashlib
import os
import stat
import tempfile
from pathlib import Path

from pydantic import Field

from apps.api.contracts import Contract


class PathInput(Contract):
    path: str = Field(min_length=1, max_length=500)


class WriteInput(PathInput):
    content: str = Field(max_length=32000)


class FileOutput(Contract):
    path: str
    content: str | None = None
    entries: list[str] | None = None
    sha256: str | None = None
    verified: bool


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, value: str) -> Path:
        if "\x00" in value or ".." in value.replace("\\", "/").split("/"):
            raise ValueError("Path traversal is not allowed")
        path = Path(value)
        if ":" in value and (os.name != "nt" or ":" in value[2:]):
            raise ValueError(
                "Alternate streams and non-workspace drive paths are not allowed"
            )
        candidate = path if path.is_absolute() else self.root / path
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError("Path is outside the workspace")
        # Reject all links/junctions, including links staying inside the workspace.
        for part in [candidate, *candidate.parents]:
            if part == self.root.parent:
                break
            if part.is_symlink() or (
                part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400
            ):
                raise ValueError("Symlinks and reparse points are not allowed")
        return resolved

    def list_directory(self, args: PathInput) -> FileOutput:
        path = self.resolve(args.path)
        if not path.is_dir():
            raise ValueError("Directory does not exist")
        entries = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
        if len(entries) > 500:
            raise ValueError("Directory exceeds the 500-entry limit")
        return FileOutput(
            path=str(path.relative_to(self.root)), entries=entries, verified=True
        )

    def read_file(self, args: PathInput) -> FileOutput:
        path = self.resolve(args.path)
        if not path.is_file() or path.stat().st_size > 32000:
            raise ValueError("File missing or exceeds the 32 KB read limit")
        with path.open("rb") as stream:
            data = stream.read(32001)
        if len(data) > 32000:
            raise ValueError("File exceeds the read limit")
        return FileOutput(
            path=str(path.relative_to(self.root)),
            content=data.decode("utf-8"),
            sha256=hashlib.sha256(data).hexdigest(),
            verified=True,
        )

    def write_file(self, args: WriteInput) -> FileOutput:
        path = self.resolve(args.path)
        if path == self.root or not path.parent.is_dir() or path.is_dir():
            raise ValueError("Choose a file in an existing workspace directory")
        data = args.content.encode("utf-8")
        if len(data) > 32000:
            raise ValueError("Write exceeds the 32 KB limit")
        if path.exists() and not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Target is not a regular file")
        fd, temp = tempfile.mkstemp(prefix=".mitra-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if self.resolve(args.path) != path:
                raise ValueError("Target changed during execution")
            os.replace(temp, path)
            observed = self.read_file(PathInput(path=str(path)))
            if observed.sha256 != hashlib.sha256(data).hexdigest():
                raise ValueError("File hash verification failed")
            return FileOutput(
                path=str(path.relative_to(self.root)),
                sha256=observed.sha256,
                verified=True,
            )
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
