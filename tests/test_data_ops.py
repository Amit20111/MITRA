import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from alembic.util.exc import CommandError
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.contracts import Conversation, Task, now
from apps.api.main import create_app
from memory.ops import backup_database, list_backups, prune_history, restore_database
from memory.store import Store, conversations, events, memory_records, tasks, traces
from tests.fakes import FakeProvider


def _task_payload(task_id: str, conversation_id: str, status: str) -> dict:
    return Task(
        id=task_id,
        conversationId=conversation_id,
        title="test task",
        status=status,  # type: ignore[arg-type]
        provider="fake",
        model="fake-model",
    ).model_dump(mode="json")


def test_conversation_rename_and_delete(tmp_path):
    provider = FakeProvider([])
    db_path = tmp_path / "mitra.db"
    app = create_app(db_path, provider, tmp_path / "workspace")
    with TestClient(app) as client:
        one = client.post("/api/v1/conversations").json()
        two = client.post("/api/v1/conversations").json()

        renamed = client.post(
            f"/api/v1/conversations/{one['id']}/rename",
            json={"title": "Renamed project"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "Renamed project"

        # Whitespace-only title rejected
        bad = client.post(
            f"/api/v1/conversations/{one['id']}/rename",
            json={"title": "   "},
        )
        assert bad.status_code == 422

        # Add conversation-scoped memory & global memory
        scoped_mem = client.post(
            "/api/v1/memories",
            json={
                "key": "note",
                "content": "Scoped note",
                "confirmed": True,
                "conversationId": one["id"],
            },
        ).json()
        global_mem = client.post(
            "/api/v1/memories",
            json={
                "key": "global_note",
                "content": "Global note",
                "confirmed": True,
            },
        ).json()

        # Insert an active (running) task in conversation one -> delete must be refused (409)
        store: Store = app.state.agent.store
        with store.engine.begin() as db:
            db.execute(
                tasks.insert().values(
                    id="task-active-1",
                    conversation_id=one["id"],
                    payload=_task_payload("task-active-1", one["id"], "running"),
                )
            )
        refused = client.post(f"/api/v1/conversations/{one['id']}/delete")
        assert refused.status_code == 409

        # Mark task completed and add event + trace -> delete succeeds and cleans up children
        with store.engine.begin() as db:
            db.execute(
                tasks.update()
                .where(tasks.c.id == "task-active-1")
                .values(payload=_task_payload("task-active-1", one["id"], "completed"))
            )
            db.execute(
                events.insert().values(
                    task_id="task-active-1",
                    payload={"type": "task.completed", "timestamp": now()},
                )
            )
            db.execute(
                traces.insert().values(
                    id="trace-1",
                    task_id="task-active-1",
                    payload={"id": "trace-1", "taskId": "task-active-1", "createdAt": now()},
                )
            )

        deleted = client.post(f"/api/v1/conversations/{one['id']}/delete")
        assert deleted.status_code == 200
        remaining_ids = [c["id"] for c in deleted.json()]
        assert one["id"] not in remaining_ids
        assert two["id"] in remaining_ids

        with store.engine.connect() as db:
            assert db.execute(select(tasks).where(tasks.c.id == "task-active-1")).fetchone() is None
            assert db.execute(select(events).where(events.c.task_id == "task-active-1")).fetchone() is None
            assert db.execute(select(traces).where(traces.c.id == "trace-1")).fetchone() is None
            assert (
                db.execute(
                    select(memory_records).where(memory_records.c.id == scoped_mem["id"])
                ).fetchone()
                is None
            )
            assert (
                db.execute(
                    select(memory_records).where(memory_records.c.id == global_mem["id"])
                ).fetchone()
                is not None
            )


def test_backup_restore_and_pre_upgrade_backup(tmp_path):
    db_path = tmp_path / "mitra.db"
    store = Store(db_path)
    with store.engine.begin() as db:
        db.execute(
            conversations.insert().values(
                id="conv-1",
                payload=Conversation(
                    id="conv-1", title="Before backup"
                ).model_dump(mode="json"),
            )
        )
    store.engine.dispose()

    backup_info = backup_database(db_path)
    backup_file = tmp_path / "backups" / backup_info.filename
    assert backup_file.exists()
    assert len(list_backups(db_path)) == 1

    # Mutate live database after backup
    store = Store(db_path)
    with store.engine.begin() as db:
        db.execute(
            conversations.insert().values(
                id="conv-2",
                payload=Conversation(
                    id="conv-2", title="After backup"
                ).model_dump(mode="json"),
            )
        )
    store.engine.dispose()

    # Restore from backup -> conv-2 is gone, conv-1 is present, and a pre-restore safety backup was created
    restore_database(backup_file, db_path)
    restored = Store(db_path)
    with restored.engine.connect() as db:
        ids = list(db.execute(select(conversations.c.id)).scalars())
    assert ids == ["conv-1"]
    assert any("pre-restore" in b.filename for b in list_backups(db_path))

    # Simulate an older Alembic revision -> Store.__init__ creates a pre-upgrade backup automatically
    restored.engine.dispose()
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE alembic_version SET version_num = '0001_initial'")
    conn.commit()
    conn.close()

    with pytest.raises(CommandError):
        # Downgrading version_num artificially causes 0002 migration to fail on existing tables,
        # but the pre-upgrade backup must already have been created before running migrations.
        Store(db_path)
    assert any("pre-upgrade" in b.filename for b in list_backups(db_path))


def test_prune_history_and_diagnostics_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv("MITRA_API_KEY", "sk-secret-token-12345")
    provider = FakeProvider([])
    db_path = tmp_path / "mitra.db"
    app = create_app(db_path, provider, tmp_path / "workspace")
    with TestClient(app) as client:
        conv = client.post("/api/v1/conversations").json()
        store: Store = app.state.agent.store
        old_ts = (datetime.now(UTC) - timedelta(days=45)).isoformat()
        recent_ts = datetime.now(UTC).isoformat()

        with store.engine.begin() as db:
            # Old completed task -> events & traces should be pruned
            db.execute(
                tasks.insert().values(
                    id="task-old-done",
                    conversation_id=conv["id"],
                    payload=_task_payload("task-old-done", conv["id"], "completed"),
                )
            )
            db.execute(
                events.insert().values(
                    task_id="task-old-done",
                    payload={"type": "task.completed", "timestamp": old_ts},
                )
            )
            db.execute(
                traces.insert().values(
                    id="trace-old",
                    task_id="task-old-done",
                    payload={"id": "trace-old", "taskId": "task-old-done", "createdAt": old_ts},
                )
            )
            # Old active (non-terminal) task -> must NOT be pruned
            db.execute(
                tasks.insert().values(
                    id="task-old-active",
                    conversation_id=conv["id"],
                    payload=_task_payload("task-old-active", conv["id"], "running"),
                )
            )
            db.execute(
                events.insert().values(
                    task_id="task-old-active",
                    payload={"type": "task.started", "timestamp": old_ts},
                )
            )
            # Recent completed task -> must NOT be pruned
            db.execute(
                tasks.insert().values(
                    id="task-recent-done",
                    conversation_id=conv["id"],
                    payload=_task_payload("task-recent-done", conv["id"], "completed"),
                )
            )
            db.execute(
                traces.insert().values(
                    id="trace-recent",
                    task_id="task-recent-done",
                    payload={"id": "trace-recent", "taskId": "task-recent-done", "createdAt": recent_ts},
                )
            )

        res = prune_history(store, days=30)
        assert res.deletedEvents == 1
        assert res.deletedTraces == 1

        with store.engine.connect() as db:
            assert db.execute(select(events).where(events.c.task_id == "task-old-active")).fetchone() is not None
            assert db.execute(select(traces).where(traces.c.id == "trace-recent")).fetchone() is not None

        # Data status, backup, prune, diagnostics endpoints
        status_resp = client.get("/api/v1/data/status")
        assert status_resp.status_code == 200
        assert status_resp.headers["cache-control"] == "no-store"

        backup_resp = client.post("/api/v1/data/backup")
        assert backup_resp.status_code == 200
        assert backup_resp.json()["filename"].endswith(".db")

        prune_resp = client.post("/api/v1/data/prune", json={"days": 30})
        assert prune_resp.status_code == 200

        diag_resp = client.get("/api/v1/data/diagnostics")
        assert diag_resp.status_code == 200
        assert "sk-secret-token-12345" not in diag_resp.text
        parsed = json.loads(diag_resp.text)
        assert "data" in parsed and "health" in parsed
