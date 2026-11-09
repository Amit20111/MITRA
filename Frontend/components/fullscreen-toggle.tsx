"use client";

import { useState, useSyncExternalStore } from "react";
import { Maximize, Minimize } from "lucide-react";

function subscribe(onChange: () => void) {
  document.addEventListener("fullscreenchange", onChange);
  return () => document.removeEventListener("fullscreenchange", onChange);
}

export function FullscreenToggle({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const fullscreen = useSyncExternalStore(
    subscribe,
    () => Boolean(document.fullscreenElement),
    () => false,
  );
  const supported = useSyncExternalStore(
    subscribe,
    () => Boolean(document.fullscreenEnabled),
    () => false,
  );
  const [busy, setBusy] = useState(false);
  const label = fullscreen ? "Exit fullscreen" : "Enter fullscreen";

  async function toggle() {
    setBusy(true);
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      onError(
        "Fullscreen was blocked by your browser. You can try its fullscreen menu instead.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className="icon-button"
      aria-label={label}
      aria-pressed={fullscreen}
      title={
        supported
          ? `${label}${fullscreen ? " (Esc)" : ""}`
          : "Fullscreen is unavailable in this browser"
      }
      disabled={!supported || busy}
      onClick={() => void toggle()}
    >
      {fullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
    </button>
  );
}
