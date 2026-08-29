import { useEffect, useState } from "react";
import { getAlertHistory } from "../api/alertHistory";
import type { AlertHistoryEntry } from "../types/alert";
import "./AlertHistoryPage.css";

const PAGE_SIZE = 50;

type SeverityFilter = "all" | "critical" | "warning" | "info";
type StateFilter = "all" | "active" | "resolved";

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtAge(iso: string): string {
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function fmtDuration(entry: AlertHistoryEntry): string {
  const start = new Date(entry.fired_at).getTime();
  const end = entry.resolved_at ? new Date(entry.resolved_at).getTime() : Date.now();
  const sec = Math.floor((end - start) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
}

// ── Severity badge ────────────────────────────────────────────────────────────

function SevBadge({ sev }: { sev: string }) {
  return (
    <span className={`ah-sev ah-sev-${sev}`}>{sev}</span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AlertHistoryPage() {
  const [entries, setEntries]     = useState<AlertHistoryEntry[]>([]);
  const [loading, setLoading]     = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [hasMore, setHasMore]     = useState(false);
  const [severity, setSeverity]   = useState<SeverityFilter>("all");
  const [state, setState]         = useState<StateFilter>("all");

  const sevParam   = severity === "all" ? undefined : severity;
  const stateParam = state === "all"    ? undefined : state;

  const load = (reset: boolean) => {
    const offset = reset ? 0 : entries.length;
    if (reset) { setLoading(true); setEntries([]); }
    else setLoadingMore(true);

    getAlertHistory(PAGE_SIZE, offset, sevParam, stateParam)
      .then((data) => {
        setEntries((prev) => reset ? data : [...prev, ...data]);
        setHasMore(data.length === PAGE_SIZE);
        setError(null);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => { setLoading(false); setLoadingMore(false); });
  };

  useEffect(() => { load(true); }, [severity, state]); // eslint-disable-line react-hooks/exhaustive-deps

  const active   = entries.filter((e) => !e.resolved_at).length;
  const resolved = entries.filter((e) =>  e.resolved_at).length;
  const critical = entries.filter((e) => e.severity === "critical").length;

  const SEV_PILLS: SeverityFilter[]  = ["all", "critical", "warning", "info"];
  const STATE_PILLS: StateFilter[]   = ["all", "active", "resolved"];

  return (
    <div className="ah-page">
      {error && <div className="err-banner">API error: {error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total shown</div>
          <div className="summ-value sv-blue">{entries.length}</div>
          <div className="summ-sub">alert firings</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Active now</div>
          <div className={`summ-value${active > 0 ? " sv-red" : " sv-dim"}`}>{active}</div>
          <div className="summ-sub">{active === 0 ? "All clear" : "still firing"}</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Resolved</div>
          <div className="summ-value sv-green">{resolved}</div>
          <div className="summ-sub">in current view</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Critical</div>
          <div className={`summ-value${critical > 0 ? " sv-amber" : " sv-dim"}`}>{critical}</div>
          <div className="summ-sub">in current view</div>
        </div>
      </div>

      <div className="ah-filters">
        <div className="ah-filter-group">
          <span className="ah-filter-label">Severity</span>
          {SEV_PILLS.map((s) => (
            <button
              key={s}
              className={`ah-pill${severity === s ? " ah-pill-active" : ""}`}
              onClick={() => setSeverity(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div className="ah-filter-group">
          <span className="ah-filter-label">State</span>
          {STATE_PILLS.map((s) => (
            <button
              key={s}
              className={`ah-pill${state === s ? " ah-pill-active" : ""}`}
              onClick={() => setState(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Alert firings</span>
        <span className="section-meta">newest first · auto-recorded by background poller</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading alert history…</span></div>
      ) : entries.length === 0 ? (
        <div className="ah-empty">No alert history yet — alerts will be recorded automatically as they fire.</div>
      ) : (
        <>
          <div className="ah-table-wrap">
            <table className="ah-table">
              <thead>
                <tr>
                  <th>Alert</th>
                  <th>Severity</th>
                  <th>Node</th>
                  <th>Summary</th>
                  <th>Fired</th>
                  <th>Duration</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} className={e.resolved_at ? "" : "ah-row-active"}>
                    <td className="ah-name">{e.alert_name}</td>
                    <td><SevBadge sev={e.severity} /></td>
                    <td className="ah-node">{e.node_name ?? <span className="ah-dim">cluster</span>}</td>
                    <td className="ah-summary">{e.summary ?? <span className="ah-dim">—</span>}</td>
                    <td className="ah-time">{fmtAge(e.fired_at)}</td>
                    <td className="ah-dur">{fmtDuration(e)}</td>
                    <td>
                      {e.resolved_at
                        ? <span className="ah-state-resolved">Resolved</span>
                        : <span className="ah-state-active">Active</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {hasMore && (
            <div className="ah-load-more">
              <button
                className="load-more-btn"
                onClick={() => load(false)}
                disabled={loadingMore}
              >
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
