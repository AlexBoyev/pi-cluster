import { useEffect, useState } from "react";
import { listAlerts } from "../api/alerts";
import type { Alert } from "../types/alert";
import "./AlertsPanel.css";

const POLL_MS = 30_000;

function fmtDuration(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

function SeverityBadge({ severity }: { severity: Alert["severity"] }) {
  return <span className={`al-sev al-sev-${severity}`}>{severity.toUpperCase()}</span>;
}

function StateBadge({ state }: { state: Alert["state"] }) {
  return <span className={`al-state al-state-${state}`}>{state}</span>;
}

export default function AlertsPanel() {
  const [alerts, setAlerts]   = useState<Alert[]>([]);
  const [error, setError]     = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = () =>
    listAlerts()
      .then((d) => { setAlerts(d); setError(false); })
      .catch(() => setError(true))
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const firing  = alerts.filter((a) => a.state === "firing");
  const pending = alerts.filter((a) => a.state === "pending");
  const critical = firing.filter((a) => a.severity === "critical").length;

  return (
    <div className={`ap-panel${critical > 0 ? " ap-critical" : firing.length > 0 ? " ap-warning" : ""}`}>
      <div className="ap-header">
        <span className="ap-title">
          <span className="ap-icon">{critical > 0 ? "⚠" : firing.length > 0 ? "⚡" : "✓"}</span>
          Active Alerts
        </span>
        <span className="ap-meta">
          {loading ? "…" : error ? "Prometheus unreachable" : `${firing.length} firing · ${pending.length} pending`}
        </span>
      </div>

      {!loading && !error && alerts.length === 0 && (
        <div className="ap-clear">All systems nominal — no active alerts</div>
      )}

      {!loading && alerts.length > 0 && (
        <div className="ap-list">
          {alerts.map((a, i) => (
            <div key={i} className={`ap-item ap-item-${a.severity}`}>
              <div className="ap-item-head">
                <SeverityBadge severity={a.severity} />
                <StateBadge state={a.state} />
                <span className="ap-name">{a.name}</span>
                {a.node_name && <span className="ap-node">{a.node_name}</span>}
                <span className="ap-dur">{fmtDuration(a.duration_seconds)}</span>
              </div>
              <div className="ap-summary">{a.summary}</div>
              {a.description && a.description !== a.summary && (
                <div className="ap-desc">{a.description}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
