import { ShieldCheck } from "lucide-react";
import { MitraMark } from "@/components/mitra-mark";

const REASONS: Record<string, string> = {
  expired:
    "Your browser session or launch link has expired. Open a fresh launch link to continue.",
  invalid:
    "That launch link is invalid or was opened from an untrusted origin.",
  offline:
    "MITRA's backend API is offline or its local key is not ready. Start the API on port 8000 first.",
  locked:
    "Your MITRA session was locked. Open a new launch link whenever you are ready.",
};

export default async function LockedPage({
  searchParams,
}: {
  searchParams: Promise<{ reason?: string }>;
}) {
  const { reason } = await searchParams;
  const message =
    (reason && REASONS[reason]) ||
    "MITRA requires a one-time launch link from your local machine before the workspace unlocks.";

  return (
    <main className="app-shell" aria-label="MITRA locked screen">
      <section
        className="secondary-page"
        style={{
          maxWidth: 620,
          margin: "auto",
          padding: "2.5rem 2rem",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.85rem",
            marginBottom: "1.25rem",
          }}
        >
          <MitraMark size={44} />
          <div>
            <div className="eyebrow">LOCAL SECURITY BOUNDARY</div>
            <h1 style={{ margin: 0, fontSize: "1.75rem" }}>MITRA is locked</h1>
          </div>
        </div>
        <p className="page-description" role="status">
          {message}
        </p>
        <div className="settings-list" style={{ marginTop: "1.5rem" }}>
          <div className="setting-row">
            <div>
              <strong>Unlock from your terminal</strong>
              <p>
                With the FastAPI backend and Next.js frontend running on this
                machine, generate a one-time launch link and open it in your
                browser:
              </p>
              <pre
                aria-label="Unlock command"
                style={{
                  marginTop: "0.75rem",
                  padding: "0.75rem 1rem",
                  overflowX: "auto",
                }}
              >
                npm run unlock
              </pre>
            </div>
            <span className="green-label">
              <ShieldCheck size={14} /> Loopback only
            </span>
          </div>
          <div className="settings-footnote">
            <ShieldCheck size={18} />
            <p>
              Launch links are single-use, expire after two minutes, and issue
              an HttpOnly SameSite=Strict session cookie bound to your local
              MITRA instance.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
