"use client";
import { useEffect, useRef, useState } from "react";
import type { VoiceStatus, Transcript, SpeechAudio } from "@/lib/types";

export function VoicePanel({
  onClose,
  onTranscript,
}: {
  onClose: () => void;
  onTranscript: (text: string) => void;
}) {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [text, setText] = useState("");
  const [state, setState] = useState("Idle");
  const [error, setError] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const abort = useRef<AbortController | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const generation = useRef(0);
  const mounted = useRef(true);
  const audioUrl = useRef("");
  function release() {
    generation.current++;
    abort.current?.abort();
    abort.current = null;
    if (timer.current) clearTimeout(timer.current);
    if (recorder.current && recorder.current.state !== "inactive") {
      recorder.current.onstop = null;
      recorder.current.stop();
    }
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    player.current?.pause();
    player.current = null;
    if (audioUrl.current) {
      URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = "";
    }
  }
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    fetch("/api/v1/voice/status", {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(setStatus)
      .catch(() => {
        if (mounted.current && !controller.signal.aborted)
          setError("Voice status unavailable");
      });
    return () => {
      mounted.current = false;
      controller.abort();
      release();
    };
  }, []);
  async function call<T>(path: string, body: unknown): Promise<T> {
    abort.current = new AbortController();
    const response = await fetch(`/api/v1/voice/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: abort.current.signal,
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string" ? data.detail : "Voice request failed",
      );
    return data as T;
  }
  async function record() {
    release();
    setError("");
    setState("Requesting microphone");
    const version = generation.current;
    try {
      if (!navigator.mediaDevices || typeof MediaRecorder === "undefined")
        throw new Error("Microphone recording is unavailable in this browser");
      const acquired = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      if (!mounted.current || version !== generation.current) {
        acquired.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = acquired;
      const mime = ["audio/webm", "audio/ogg", "audio/mp4"].find((m) =>
        MediaRecorder.isTypeSupported(m),
      );
      if (!mime) throw new Error("No supported recording format");
      const recording = new MediaRecorder(acquired, { mimeType: mime });
      recorder.current = recording;
      const chunks: Blob[] = [];
      let size = 0;
      recording.ondataavailable = (e) => {
        size += e.data.size;
        chunks.push(e.data);
        if (size > 2000000 && recording.state !== "inactive") recording.stop();
      };
      recording.onstop = async () => {
        acquired.getTracks().forEach((t) => t.stop());
        stream.current = null;
        if (timer.current) clearTimeout(timer.current);
        if (version !== generation.current || !mounted.current) return;
        try {
          if (size > 2000000)
            throw new Error("Recording too large; try a shorter request");
          setState("Transcribing");
          const bytes = new Uint8Array(
            await new Blob(chunks, { type: mime }).arrayBuffer(),
          );
          let binary = "";
          for (const byte of bytes) binary += String.fromCharCode(byte);
          if (version !== generation.current) return;
          const result = await call<Transcript>("transcribe", {
            audio: btoa(binary),
            mime,
          });
          if (version === generation.current && mounted.current) {
            setText(result.text);
            setState("Review transcript");
          }
        } catch (e) {
          if (version === generation.current && mounted.current) {
            setError(e instanceof Error ? e.message : "Transcription failed");
            setState("Idle");
          }
        }
      };
      recording.onerror = () => {
        release();
        setError("Microphone recording failed");
        setState("Idle");
      };
      recording.start(250);
      setState("Recording");
      timer.current = setTimeout(() => {
        if (recording.state !== "inactive") recording.stop();
      }, 30000);
    } catch (e) {
      if (version === generation.current && mounted.current) {
        release();
        setError(
          e instanceof Error ? e.message : "Microphone permission denied",
        );
        setState("Idle");
      }
    }
  }
  async function speak() {
    release();
    setError("");
    setState("Generating speech");
    const version = generation.current;
    try {
      const result = await call<SpeechAudio>("speak", {
        text: text.slice(0, 2000),
      });
      if (version !== generation.current || !mounted.current) return;
      const bytes = Uint8Array.from(atob(result.audio), (c) => c.charCodeAt(0));
      audioUrl.current = URL.createObjectURL(
        new Blob([bytes], { type: result.mime }),
      );
      const audio = new Audio(audioUrl.current);
      player.current = audio;
      audio.onended = () => {
        release();
        setState("Idle");
      };
      audio.onerror = () => {
        release();
        setError("Audio playback failed");
        setState("Idle");
      };
      await audio.play();
      if (version === generation.current && mounted.current)
        setState("Playing");
    } catch (e) {
      if (version === generation.current && mounted.current) {
        release();
        setError(e instanceof Error ? e.message : "Speech failed");
        setState("Idle");
      }
    }
  }
  const working = [
    "Transcribing",
    "Generating speech",
    "Requesting microphone",
    "Recording",
  ].includes(state);
  return (
    <div className="modal-backdrop">
      <section
        className="voice-modal feature-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-title"
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
          if (e.key === "Tab") {
            const controls = Array.from(
              e.currentTarget.querySelectorAll<HTMLElement>(
                "button:not(:disabled), textarea, input:not(:disabled), select",
              ),
            );
            const first = controls[0],
              last = controls.at(-1);
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last?.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first?.focus();
            }
          }
        }}
      >
        <button
          autoFocus
          className="modal-close"
          aria-label="Close voice"
          onClick={onClose}
        >
          ?
        </button>
        <h2 id="voice-title">Voice, with you in control</h2>
        <p>{status?.message || "Checking voice configuration..."}</p>
        <p role="status">{state} ? Recording limit: 30 seconds</p>
        <div className="feature-actions">
          <button
            className="outline-badge"
            disabled={!status?.transcription || working}
            onClick={() => void record()}
          >
            Start recording
          </button>
          <button
            className="outline-badge"
            disabled={state !== "Recording"}
            onClick={() => recorder.current?.stop()}
          >
            Stop & transcribe
          </button>
          <button
            className="outline-badge"
            onClick={() => {
              release();
              setState("Idle");
            }}
          >
            Cancel recording / stop playback
          </button>
        </div>
        {error && <p role="alert">{error}</p>}
        <label>
          Review transcript or enter text
          <textarea
            aria-label="Voice transcript"
            value={text}
            maxLength={8000}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <p>
          Nothing is sent as a task until you review this text and press Send in
          the main prompt. Recordings are not saved by MITRA; your configured
          provider may have its own retention policy.
        </p>
        <div className="feature-actions">
          <button
            className="outline-badge"
            disabled={!text.trim() || working}
            onClick={() => {
              onTranscript(text);
              onClose();
            }}
          >
            Use reviewed transcript
          </button>
          <button
            className="outline-badge"
            disabled={
              !status?.speech || !text.trim() || working || text.length > 2000
            }
            onClick={() => void speak()}
          >
            Read text aloud
          </button>
        </div>
      </section>
    </div>
  );
}
