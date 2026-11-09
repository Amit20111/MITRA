"use client";
import { useEffect, useState } from "react";
import { agentClient } from "@/lib/api/client";
import type { DesktopJob, DesktopRequest, RuntimeStatus } from "@/lib/types";

export function DesktopPanel({ status }: { status: RuntimeStatus | null }) {
  const [jobs, setJobs] = useState<DesktopJob[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const enabled = status?.connected && status.capabilities.includes("desktop");
  useEffect(() => {
    let active = true,
      running = false;
    const refresh = async () => {
      if (running || document.hidden) return;
      running = true;
      try {
        const data = await agentClient.desktopJobs();
        if (active) setJobs(data);
      } catch {
        if (active) {
          setJobs([]);
          setError("Desktop connection unavailable");
        }
      } finally {
        running = false;
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);
  async function perform(work: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await work();
      setJobs(await agentClient.desktopJobs());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Desktop request failed");
    } finally {
      setBusy(false);
    }
  }
  const pending = jobs.some((j) =>
    ["pending", "approved", "dispatched"].includes(j.state),
  );
  const targets =
    jobs
      .filter((j) => j.action === "list_windows" && j.state === "completed")
      .at(-1)?.targets || [];
  const propose = (body: DesktopRequest) =>
    perform(() => agentClient.proposeDesktop(body));
  return (
    <section className="feature-panel" aria-label="Desktop controls">
      <h3>Desktop observation & focus</h3>
      <p>
        {enabled
          ? "Opted-in helper connected. Every operation requires exact approval."
          : "Start the paired helper with run --desktop to opt in. No desktop access by default."}
      </p>
      <div className="feature-actions">
        <button
          className="outline-badge"
          disabled={!enabled || busy || pending}
          onClick={() => void propose({ action: "list_windows" })}
        >
          Inspect windows
        </button>
        <button
          className="outline-badge"
          disabled={busy}
          onClick={() => void perform(agentClient.stopDesktop)}
        >
          Stop desktop & clear captures
        </button>
        <button
          className="outline-badge"
          disabled={!enabled || busy || pending}
          onClick={() => void perform(agentClient.enableDesktop)}
        >
          Enable new desktop requests
        </button>
      </div>
      <p>
        Targets and images expire after two minutes. Captures stay in temporary
        memory, are not sent to the model, and may include private content
        inside the selected window. Focus is the only supported desktop action;
        typing and clicking are unavailable.
      </p>
      {error && <p role="alert">{error}</p>}
      {targets.map((t) => (
        <div className="setting-row" key={t.id}>
          <span>
            {t.title} ? PID {t.processId}
          </span>
          <div className="feature-actions">
            <button
              className="outline-badge"
              disabled={!enabled || busy || pending}
              onClick={() =>
                void propose({ action: "screenshot", targetId: t.id })
              }
            >
              Capture {t.title}
            </button>
            <button
              className="outline-badge"
              disabled={!enabled || busy || pending}
              onClick={() => void propose({ action: "focus", targetId: t.id })}
            >
              Focus {t.title}
            </button>
          </div>
        </div>
      ))}
      {[...jobs].reverse().map((job) => (
        <article className="desktop-job" key={job.id}>
          <strong>
            {job.action} ? {job.targetTitle}
          </strong>
          <p>
            {job.state}: {job.message}
          </p>
          {job.state === "pending" && (
            <>
              <p>
                Approve this exact operation on this target? Expires{" "}
                {new Date(job.expiresAt).toLocaleTimeString()}.
              </p>
              <code>{job.digest}</code>
              <div className="feature-actions">
                <button
                  className="outline-badge"
                  disabled={busy}
                  onClick={() =>
                    void perform(() => agentClient.decideDesktop(job, true))
                  }
                >
                  Approve desktop operation
                </button>
                <button
                  className="outline-badge"
                  disabled={busy}
                  onClick={() =>
                    void perform(() => agentClient.decideDesktop(job, false))
                  }
                >
                  Reject desktop operation
                </button>
              </div>
            </>
          )}
          {/* Raw BMP has no executable content; images are never remote URLs. */}
          {job.hasImage && (
            // eslint-disable-next-line @next/next/no-img-element -- private expiring capture must not enter an image optimization cache
            <img
              className="desktop-capture"
              src={`/api/v1/runtime/desktop/${job.id}/image`}
              alt={`Approved capture of ${job.targetTitle}`}
            />
          )}
        </article>
      ))}
    </section>
  );
}
