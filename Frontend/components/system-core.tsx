import { MitraMark } from "@/components/mitra-mark";

type CoreProps = {
  connected: boolean;
  loading: boolean;
  model: string;
  status?: string;
  activeCount: number;
  completedCount: number;
  approvalCount: number;
};

export function SystemCore(props: CoreProps) {
  const working = ["planning", "running", "verifying", "queued"].includes(
    props.status || "",
  );
  const state = props.loading
    ? "INITIALIZING"
    : !props.connected
      ? "OFFLINE"
      : props.status
        ? props.status.replaceAll("_", " ").toUpperCase()
        : "STANDBY";
  return (
    <section
      className={`system-core ${working ? "is-working" : ""}`}
      aria-label="System overview"
    >
      <div className="core-topline">
        <span>01 / INTELLIGENCE CORE</span>
        <span className="core-mode">SUPERVISED</span>
      </div>
      <div className="core-layout">
        <div className="core-readouts">
          <div>
            <span>ACTIVE TASKS</span>
            <strong>{String(props.activeCount).padStart(2, "0")}</strong>
            <small>Current sessions</small>
          </div>
          <div>
            <span>COMPLETED</span>
            <strong>{String(props.completedCount).padStart(2, "0")}</strong>
            <small>Recorded tasks</small>
          </div>
        </div>
        <div className="signal-core" aria-hidden="true">
          <svg viewBox="0 0 300 300" className="signal-sculpture">
            <circle cx="150" cy="150" r="146" className="orbit-outer" />
            <circle cx="150" cy="150" r="132" className="orbit-faint" />
            <g className="mechanical-collar">
              <circle cx="150" cy="150" r="119" />
              <path d="M150 31A119 119 0 0 1 269 150M150 269A119 119 0 0 1 31 150" />
            </g>
            <g className="signal-weave">
              <circle cx="150" cy="150" r="108" />
              <circle cx="150" cy="150" r="100" strokeDasharray="72 7 20 8" />
              <path d="M150 42l4 4-4 4-4-4zM150 250l4 4-4 4-4-4z" />
            </g>
            <circle cx="150" cy="150" r="88" className="orbit-faint" />
            <circle cx="150" cy="150" r="74" className="orbit-inner" />
            <g className="signal-satellites">
              <circle cx="150" cy="31" r="2.5" />
              <path d="M31 144l-5 6 5 6M269 144l5 6-5 6" />
            </g>
          </svg>
          <div className="signal-monogram">
            <MitraMark size={64} />
          </div>
        </div>
        <div className="core-readouts core-readouts-right">
          <div>
            <span>APPROVAL QUEUE</span>
            <strong className={props.approvalCount ? "approval-count" : ""}>
              {String(props.approvalCount).padStart(2, "0")}
            </strong>
            <small>Human authorization</small>
          </div>
          <div>
            <span>API CONNECTION</span>
            <strong className="core-connection">
              {props.loading
                ? "CHECKING"
                : props.connected
                  ? "CONNECTED"
                  : "OFFLINE"}
            </strong>
            <small>{props.model || "Model not configured"}</small>
          </div>
        </div>
      </div>
      <div className="core-status">
        <span
          className={working ? "core-status-light active" : "core-status-light"}
        />
        <span>{state}</span>
        <span className="core-status-line" />
        <small>
          {props.connected ? "API LINK ESTABLISHED" : "AWAITING API CONNECTION"}
        </small>
      </div>
    </section>
  );
}
