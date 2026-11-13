"""SQLite backup, restore, retention pruning, and redacted diagnostics."""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from agent.state import TERMINAL
from apps.api.config import ROOT, Config
from apps.api.contracts import (
    BackupInfo,
    DataStatus,
    Health,
    PruneResult,
    RuntimeAudit,
    RuntimeStatus,
    Settings,
    Task,
    now,
)
from memory.store import (
    Store,
    conversations,
    events,
    memory_records,
    requests,
    tasks,
    traces,
)
from security.redaction import Redactor


def backups_dir(database: Path) -> Path:
    return database.resolve().parent / "backups"


def _verify_sqlite(path: Path, require_schema: bool = False) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Database file not found: {path}")
    connection = sqlite3.connect(str(path))
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            raise ValueError(f"SQLite integrity check failed for {path}")
        if require_schema:
            tables = {
                r[0]
                for r in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing = {"conversations", "tasks", "alembic_version"} - tables
            if missing:
                raise ValueError(
                    f"Backup is missing required MITRA tables: {', '.join(sorted(missing))}"
                )
    finally:
        connection.close()


def backup_database(source: Path, destination: Path | None = None) -> BackupInfo:
    """Create a consistent online SQLite backup and verify its integrity."""
    resolved = source.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Database file not found: {resolved}")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = (
        destination.resolve()
        if destination is not None
        else backups_dir(resolved) / f"{resolved.stem}-{stamp}.db"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    src = sqlite3.connect(str(resolved))
    dst = sqlite3.connect(str(temporary))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    _verify_sqlite(temporary, require_schema=False)
    os.replace(temporary, target)
    stat = target.stat()
    return BackupInfo(
        filename=target.name,
        sizeBytes=stat.st_size,
        createdAt=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    )


def list_backups(database: Path) -> list[BackupInfo]:
    folder = backups_dir(database)
    if not folder.exists():
        return []
    items: list[tuple[float, BackupInfo]] = []
    for entry in folder.iterdir():
        if entry.is_file() and entry.suffix == ".db":
            stat = entry.stat()
            items.append(
                (
                    stat.st_mtime,
                    BackupInfo(
                        filename=entry.name,
                        sizeBytes=stat.st_size,
                        createdAt=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    ),
                )
            )
    items.sort(key=lambda pair: pair[0], reverse=True)
    return [info for _, info in items[:20]]


def restore_database(source: Path, destination: Path) -> Path:
    """Validate a backup and replace the target SQLite database safely."""
    src_path = source.resolve()
    dst_path = destination.resolve()
    _verify_sqlite(src_path, require_schema=True)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if dst_path.exists() and dst_path.stat().st_size > 0:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safety = backups_dir(dst_path) / f"{dst_path.stem}-pre-restore-{stamp}.db"
        backup_database(dst_path, safety)
    temporary = dst_path.with_name(f".{dst_path.name}.{os.getpid()}.restore.tmp")
    src = sqlite3.connect(str(src_path))
    dst = sqlite3.connect(str(temporary))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    _verify_sqlite(temporary, require_schema=True)
    os.replace(temporary, dst_path)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(dst_path) + suffix)
        sidecar.unlink(missing_ok=True)
    return dst_path


def _alembic_revision(store: Store) -> str:
    with store.engine.connect() as db:
        try:
            row = db.exec_driver_sql(
                "SELECT version_num FROM alembic_version LIMIT 1"
            ).fetchone()
            return str(row[0]) if row else "none"
        except SQLAlchemyError:
            return "unknown"


def data_status(store: Store, database: Path) -> DataStatus:
    resolved = database.resolve()
    with store.engine.connect() as db:
        conv_count = int(
            db.execute(select(func.count()).select_from(conversations)).scalar_one()
        )
        task_count = int(
            db.execute(select(func.count()).select_from(tasks)).scalar_one()
        )
        event_count = int(
            db.execute(select(func.count()).select_from(events)).scalar_one()
        )
        trace_count = int(
            db.execute(select(func.count()).select_from(traces)).scalar_one()
        )
        mem_count = int(
            db.execute(select(func.count()).select_from(memory_records)).scalar_one()
        )
    return DataStatus(
        databasePath=str(resolved),
        sizeBytes=resolved.stat().st_size if resolved.exists() else 0,
        alembicRevision=_alembic_revision(store),
        conversations=conv_count,
        tasks=task_count,
        events=event_count,
        traces=trace_count,
        memories=mem_count,
        backups=list_backups(resolved),
    )


def _is_older_than(timestamp_value: Any, cutoff: datetime) -> bool:
    if not isinstance(timestamp_value, str) or not timestamp_value:
        return False
    try:
        parsed = datetime.fromisoformat(timestamp_value)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed < cutoff


def prune_history(store: Store, days: int) -> PruneResult:
    """Delete events and traces older than `days` for terminal tasks only."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with store.transaction() as db:
        terminal_ids = {
            task.id
            for raw in db.execute(select(tasks.c.payload)).scalars()
            for task in [Task.model_validate(raw)]
            if task.status in TERMINAL
        }
        old_events = [
            row["id"]
            for row in db.execute(select(events.c.id, events.c.task_id, events.c.payload)).mappings()
            if row["task_id"] in terminal_ids
            and isinstance(row["payload"], dict)
            and _is_older_than(row["payload"].get("timestamp"), cutoff)
        ]
        old_traces = [
            row["id"]
            for row in db.execute(select(traces.c.id, traces.c.task_id, traces.c.payload)).mappings()
            if row["task_id"] in terminal_ids
            and isinstance(row["payload"], dict)
            and _is_older_than(row["payload"].get("createdAt"), cutoff)
        ]
        if old_events:
            db.execute(delete(events).where(events.c.id.in_(old_events)))
        if old_traces:
            db.execute(delete(traces).where(traces.c.id.in_(old_traces)))
    return PruneResult(deletedEvents=len(old_events), deletedTraces=len(old_traces))


def build_diagnostics(
    store: Store,
    database: Path,
    api_version: str,
    health: Health,
    settings: Settings,
    runtime: RuntimeStatus,
    audit: list[RuntimeAudit],
) -> dict[str, Any]:
    with store.engine.connect() as db:
        recent_traces = [
            store.redactor.clean(item)
            for item in db.execute(select(traces.c.payload)).scalars().all()[-20:]
        ]
        request_count = int(
            db.execute(select(func.count()).select_from(requests)).scalar_one()
        )
    bundle = {
        "generatedAt": now(),
        "apiVersion": api_version,
        "health": health.model_dump(mode="json"),
        "settings": settings.model_dump(mode="json"),
        "runtime": runtime.model_dump(mode="json"),
        "runtimeAudit": [item.model_dump(mode="json") for item in audit],
        "data": data_status(store, database).model_dump(mode="json"),
        "idempotencyRequests": request_count,
        "recentTraces": recent_traces,
    }
    return dict(store.redactor.clean(bundle))


def main() -> None:
    parser = argparse.ArgumentParser(description="MITRA SQLite data operations")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("backup", help="Create a verified online SQLite backup")
    b.add_argument("--output", type=Path, default=None)

    r = sub.add_parser("restore", help="Restore a verified SQLite backup (stop API first)")
    r.add_argument("--input", type=Path, required=True)

    p = sub.add_parser("prune", help="Prune terminal task events/traces older than N days")
    p.add_argument("--days", type=int, default=30)

    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = Config()
    if args.command == "backup":
        info = backup_database(config.database, args.output)
        print(f"Created backup {info.filename} ({info.sizeBytes} bytes)")
    elif args.command == "restore":
        target = restore_database(args.input, config.database)
        print(f"Restored database to {target}")
    elif args.command == "prune":
        redactor = Redactor([k.get_secret_value() for k in config.keys.values()])
        store = Store(config.database, redactor)
        try:
            result = prune_history(store, max(1, args.days))
            print(
                f"Pruned {result.deletedEvents} events and {result.deletedTraces} traces"
            )
        finally:
            store.close()


if __name__ == "__main__":
    main()
