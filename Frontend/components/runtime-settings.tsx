"use client";

import { useEffect, useState } from "react";
import { agentClient } from "@/lib/api/client";
import type { PairingChallenge, RuntimeStatus } from "@/lib/types";

export function RuntimeSettings({
  status,
  onStatus,
}: {
  status: RuntimeStatus | null;
  onStatus: (value: RuntimeStatus) => void;
}) {
  const [challenge, setChallenge] = useState<PairingChallenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  useEffect(() => {
    if (!challenge) return;
    const timeout = window.setTimeout(
      () => setChallenge(null),
      Math.max(0, Date.parse(challenge.expiresAt) - Date.now()),
    );
    return () => window.clearTimeout(timeout);
  }, [challenge]);
  async function pair() {
    setBusy(true);
    setNote("");
    try {
      setChallenge(await agentClient.beginRuntimePairing());
    } catch {
      setNote(
        "Could not create a pairing code. Check the API connection or existing pairing.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function revoke() {
    if (!status?.runtimeId) return;
    setBusy(true);
    setNote("");
    try {
      onStatus(await agentClient.revokeRuntime(status.runtimeId));
      setChallenge(null);
      setNote("Runtime access revoked.");
    } catch {
      setNote(
        "Could not revoke access. Refresh the runtime status and try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="runtime-settings">
      <div className="setting-row">
        <div>
          <strong>Windows runtime</strong>
          <p>{status?.message || "Runtime status unavailable."}</p>
          {status?.name && (
            <p>
              {status.name} · Last heartbeat:{" "}
              {status.lastSeen
                ? new Date(status.lastSeen).toLocaleTimeString()
                : "not received"}
            </p>
          )}
        </div>
        <span className="outline-badge">
          {status?.connected
            ? "Connected"
            : status?.paired
              ? "Paired / offline"
              : "Not paired"}
        </span>
      </div>
      <div className="runtime-pairing-controls">
        <span>
          Pairing alone grants heartbeat only. Desktop access requires --desktop
          and exact operation approval.
        </span>
        {status?.paired ? (
          <button
            className="outline-badge"
            disabled={busy}
            onClick={() => void revoke()}
          >
            Revoke runtime access
          </button>
        ) : (
          <button
            className="outline-badge"
            disabled={busy || !status}
            onClick={() => void pair()}
          >
            Generate runtime pairing code
          </button>
        )}
      </div>
      {challenge && !status?.paired && (
        <div className="runtime-pairing-code">
          <strong>Pair your Windows helper</strong>
          <p>
            Run <code>.venv\Scripts\python -m apps.runtime pair</code> from the
            repository and paste this code at its prompt. Then run{" "}
            <code>.venv\Scripts\python -m apps.runtime run</code>.
          </p>
          <pre aria-label="Runtime pairing code">{challenge.pairingCode}</pre>
          <p>
            Single use · expires{" "}
            {new Date(challenge.expiresAt).toLocaleTimeString()}. Keep this code
            private.
          </p>
          <button
            className="outline-badge"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(challenge.pairingCode);
                setNote("Pairing code copied.");
              } catch {
                setNote(
                  "Clipboard unavailable. Select and copy the code above.",
                );
              }
            }}
          >
            Copy pairing code
          </button>
        </div>
      )}
      {note && (
        <p className="runtime-pairing-note" role="status">
          {note}
        </p>
      )}
    </div>
  );
}
