from __future__ import annotations

"""Explicit user-managed facts; no automatic conversation harvesting."""

import re

from sqlalchemy import delete, insert, select, update

from apps.api.contracts import MemoryInput, MemoryRecord, MemoryUpdate, now
from memory.store import Store, memory_records


class MemoryService:
    def __init__(self, store: Store):
        self.store = store

    def list_records(self) -> list[MemoryRecord]:
        with self.store.transaction() as db:
            return [
                MemoryRecord.model_validate(p)
                for p in db.execute(select(memory_records.c.payload)).scalars()
            ]

    def save(self, body: MemoryInput, identity: str | None = None) -> MemoryRecord:
        with self.store.transaction() as db:
            records = [
                MemoryRecord.model_validate(p)
                for p in db.execute(select(memory_records.c.payload)).scalars()
            ]
            old = next((r for r in records if r.id == identity), None)
            if identity and not old:
                raise LookupError("Memory not found")
            if old and (
                not isinstance(body, MemoryUpdate) or body.revision != old.revision
            ):
                raise ValueError("Memory changed; reload before editing")
            if body.conversationId:
                self.store.conversation(db, str(body.conversationId))
            key = body.key.strip().casefold()
            if any(
                r.id != identity
                and r.key.casefold() == key
                and r.conversationId == body.conversationId
                for r in records
            ):
                raise ValueError(
                    "A record with this key and scope exists; edit it instead"
                )
            if not old and len(records) >= 200:
                raise ValueError("Memory limit reached (200 records)")
            record = MemoryRecord(**body.model_dump(exclude={"revision"}))
            record.key = body.key.strip()
            record.content = body.content.strip()
            if old:
                record.id, record.createdAt = old.id, old.createdAt
                record.revision = old.revision + 1
            record.updatedAt = now()
            values = {"id": record.id, "payload": record.model_dump(mode="json")}
            if old:
                db.execute(
                    update(memory_records)
                    .where(memory_records.c.id == old.id)
                    .values(**values)
                )
            else:
                db.execute(insert(memory_records).values(**values))
            return record

    def delete(self, identity: str) -> None:
        with self.store.transaction() as db:
            db.execute(delete(memory_records).where(memory_records.c.id == identity))

    def retrieve(self, query: str, conversation: str) -> list[MemoryRecord]:
        words = set(re.findall(r"[\w-]{3,}", query.casefold())) - {
            "the",
            "and",
            "with",
            "that",
            "this",
            "please",
            "can",
            "you",
            "for",
            "my",
        }
        scored = []
        records = self.list_records()
        scoped_keys = {
            r.key.casefold()
            for r in records
            if r.confirmed and str(r.conversationId) == conversation
        }
        for record in records:
            if record.conversationId is None and record.key.casefold() in scoped_keys:
                continue
            if not record.confirmed or (
                record.conversationId and str(record.conversationId) != conversation
            ):
                continue
            tokens = set(
                re.findall(r"[\w-]{3,}", (record.key + " " + record.content).casefold())
            )
            score = len(words & tokens)
            if score:
                scored.append((score, record.updatedAt, record))
        return [
            r
            for _, _, r in sorted(
                scored, key=lambda item: (item[0], item[1]), reverse=True
            )[:3]
        ]
