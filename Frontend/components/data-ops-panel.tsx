"use client";

import { useCallback, useEffect, useState } from "react";
import { agentClient } from "../lib/api/client";
import type { DataStatus } from "../lib/types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function DataOpsPanel() {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [pruneDays, setPruneDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await agentClient.dataStatus();
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data status.");
    }
  }, []);

  useEffect(() => {
    let active = true;
    agentClient
      .dataStatus()
      .then((next) => {
        if (!active) return;
        setStatus(next);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load data status.");
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleBackup() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const info = await agentClient.createBackup();
      setNotice(`Backup created: ${info.filename} (${formatBytes(info.sizeBytes)})`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePrune() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await agentClient.pruneData(pruneDays);
      setNotice(
        `Pruned ${result.deletedEvents} events and ${result.deletedTraces} traces older than ${pruneDays} days.`,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prune failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="feature-panel" data-testid="data-ops-panel">
      <div className="setting-row">
        <div>
          <strong>Data &amp; Backups</strong>
          <p className="muted-line">
            {status
              ? `${formatBytes(status.sizeBytes)} · ${status.conversations} conversations · ${status.tasks} tasks · ${status.events} events · ${status.traces} traces · ${status.memories} memories`
              : "Loading database status..."}
          </p>
        </div>
        {status?.alembicRevision && (
          <span className="outline-badge">{status.alembicRevision}</span>
        )}
      </div>

      <div className="feature-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={busy}
          onClick={() => void handleBackup()}
        >
          Create backup
        </button>

        <label className="muted-line" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
          <span>Prune &gt;</span>
          <input
            type="number"
            min={1}
            max={3650}
            value={pruneDays}
            disabled={busy}
            onChange={(e) => setPruneDays(Math.max(1, Number(e.target.value) || 1))}
            style={{ width: "4.5rem" }}
            aria-label="Prune retention days"
          />
          <span>days</span>
        </label>

        <button
          type="button"
          className="secondary-button"
          disabled={busy}
          onClick={() => void handlePrune()}
        >
          Prune old history
        </button>

        <a
          className="secondary-button"
          href={agentClient.diagnosticsUrl()}
          download="mitra-diagnostics.json"
        >
          Download diagnostics
        </a>
      </div>

      {notice && (
        <p className="muted-line" role="status" data-testid="data-ops-notice">
          {notice}
        </p>
      )}
      {error && (
        <p className="muted-line" role="alert" data-testid="data-ops-error">
          {error}
        </p>
      )}

      {status && status.backups.length > 0 && (
        <div className="setting-row" style={{ flexDirection: "column", alignItems: "stretch", gap: "0.35rem" }}>
          <strong style={{ fontSize: "0.85rem" }}>Recent backups ({status.backups.length})</strong>
          {status.backups.slice(0, 5).map((b) => (
            <div
              key={b.filename}
              className="muted-line"
              style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem" }}
            >
              <span>{b.filename}</span>
              <span>{formatBytes(b.sizeBytes)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
