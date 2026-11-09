"use client";
import { useEffect, useState } from "react";
import { agentClient } from "@/lib/api/client";
import type { MemoryRecord } from "@/lib/types";

export function MemoryPanel({
  conversationId,
}: {
  conversationId: string | null;
}) {
  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [editing, setEditing] = useState<MemoryRecord | null>(null);
  const [key, setKey] = useState("");
  const [content, setContent] = useState("");
  const [scope, setScope] = useState("");
  const [confirmed, setConfirmed] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    agentClient
      .memories()
      .then((r) => {
        if (active) {
          setRecords(r);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (active) setError("Could not load memory. Reload to try again.");
      });
    return () => {
      active = false;
    };
  }, []);
  async function save() {
    setBusy(true);
    setError("");
    try {
      const body = { key, content, conversationId: scope || null, confirmed };
      if (editing)
        await agentClient.updateMemory(editing.id, {
          ...body,
          revision: editing.revision,
        });
      else await agentClient.saveMemory(body);
      setRecords(await agentClient.memories());
      setEditing(null);
      setKey("");
      setContent("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save memory");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="feature-panel" aria-label="User-managed memory">
      <p>
        Only records you save here are remembered. Confirmed matching facts can
        be used in future requests; drafts stay out of model context. Memory
        never grants permissions.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
        className="feature-form"
      >
        <label>
          Memory key
          <input
            required
            maxLength={80}
            minLength={2}
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </label>
        <label>
          Fact or preference
          <textarea
            required
            maxLength={1000}
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </label>
        <label>
          Scope
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="">All my conversations</option>
            {conversationId && (
              <option value={conversationId}>Current conversation</option>
            )}
            {scope && scope !== conversationId && (
              <option value={scope}>Original conversation</option>
            )}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />{" "}
          Confirmed: allow matching retrieval
        </label>
        <button className="outline-badge" disabled={busy || !loaded}>
          {editing ? "Save memory changes" : "Add memory"}
        </button>
        {editing && (
          <button
            type="button"
            className="outline-badge"
            onClick={() => {
              setEditing(null);
              setKey("");
              setContent("");
            }}
          >
            Cancel edit
          </button>
        )}
      </form>
      {error && <p role="alert">{error}</p>}
      {!loaded && !error && <p>Loading memory...</p>}
      {loaded && !records.length && (
        <p>No memories saved. Conversations are not harvested automatically.</p>
      )}
      <div className="memory-grid">
        {records.map((record) => (
          <article key={record.id}>
            <strong>{record.key}</strong>
            <p>{record.content}</p>
            <small>
              {record.confirmed ? "Confirmed" : "Draft"} ?{" "}
              {record.conversationId
                ? "Conversation only"
                : "All conversations"}{" "}
              ? Source: {record.source} ? Updated{" "}
              {new Date(record.updatedAt).toLocaleString()} ? Revision{" "}
              {record.revision}
            </small>
            <footer>
              <button
                className="outline-badge"
                disabled={busy}
                onClick={() => {
                  setEditing(record);
                  setKey(record.key);
                  setContent(record.content);
                  setScope(record.conversationId || "");
                  setConfirmed(record.confirmed);
                }}
              >
                Edit {record.key}
              </button>
              <button
                className="outline-badge"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    setRecords(await agentClient.deleteMemory(record.id));
                    if (editing?.id === record.id) {
                      setEditing(null);
                      setKey("");
                      setContent("");
                    }
                  } catch {
                    setError("Could not delete memory");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Delete {record.key}
              </button>
            </footer>
          </article>
        ))}
      </div>
      <p>
        Deletion prevents future retrieval; it does not erase earlier
        conversation messages or private traces that already used the fact.
      </p>
    </section>
  );
}
