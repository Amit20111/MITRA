"use client";

import { useEffect, useState } from "react";
import { agentClient } from "@/lib/api/client";
import type { SessionStatus } from "@/lib/types";

export function SessionControls() {
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  useEffect(() => {
    let active = true;
    agentClient
      .session()
      .then((value) => {
        if (active) setSession(value);
      })
      .catch(() => {
        if (active) setSession(null);
      });
    return () => {
      active = false;
    };
  }, []);

  async function lock(all: boolean) {
    setBusy(true);
    setNote("");
    try {
      if (all) {
        await agentClient.revokeAllSessions();
      } else {
        await agentClient.logout();
      }
      // A full document load discards in-memory workspace data after locking.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/locked?reason=locked");
    } catch {
      setNote("Could not lock session. Check the API connection.");
      setBusy(false);
    }
  }

  return (
    <div className="setting-row">
      <div>
        <strong>Browser session</strong>
        <p>
          {session
            ? `Active sessions: ${session.activeSessions} · Expires ${new Date(session.expiresAt).toLocaleString()}`
            : "Authenticated via HttpOnly SameSite=Strict session cookie."}
        </p>
        {note && <p role="status">{note}</p>}
      </div>
      <div className="feature-actions">
        <button
          className="outline-badge"
          disabled={busy}
          onClick={() => void lock(false)}
        >
          Lock session
        </button>
        <button
          className="outline-badge"
          disabled={busy}
          onClick={() => void lock(true)}
        >
          Revoke all sessions
        </button>
      </div>
    </div>
  );
}
