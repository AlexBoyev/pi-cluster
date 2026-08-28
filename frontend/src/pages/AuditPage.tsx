import { useEffect, useState } from "react";
import { listAuditLogs } from "../api/audit";
import type { AuditLog } from "../types/audit";
import "./AuditPage.css";

const PAGE_SIZE = 50;

const ACTION_LABELS: Record<string, string> = {
  "workload.create": "Deploy",
  "workload.delete": "Delete",
  "node.cordon":     "Cordon",
  "node.uncordon":   "Uncordon",
};

function ActionBadge({ action }: { action: string }) {
  const cls = action.replace(".", "-");
  return (
    <span className={`al-badge al-act al-${cls}`}>
      {ACTION_LABELS[action] ?? action}
    </span>
  );
}

function StatusBadge({ status }: { status: AuditLog["status"] }) {
  return (
    <span className={`al-badge al-status al-${status}`}>
      {status === "success" ? "OK" : "FAIL"}
    </span>
  );
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export default function AuditPage() {
  const [logs, setLogs]       = useState<AuditLog[]>([]);
  const [offset, setOffset]   = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [filter, setFilter]   = useState<string>("all");

  const load = async (off: number, append: boolean) => {
    append ? setLoadingMore(true) : setLoading(true);
    setError(null);
    try {
      const data = await listAuditLogs(PAGE_SIZE, off);
      setLogs((prev) => append ? [...prev, ...data] : data);
      setHasMore(data.length === PAGE_SIZE);
      setOffset(off + data.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      append ? setLoadingMore(false) : setLoading(false);
    }
  };

  useEffect(() => { load(0, false); }, []);

  useEffect(() => {
    const id = setInterval(() => load(0, false), 30_000);
    return () => clearInterval(id);
  }, []);

  const filtered = filter === "all"
    ? logs
    : logs.filter((l) => l.action === filter);

  const failures = logs.filter((l) => l.status === "failure").length;
  const actions  = Array.from(new Set(logs.map((l) => l.action))).sort();

  return (
    <div className="al-page">
      {error && <div className="err-banner">{error}</div>}

      {/* Summary */}
      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total events</div>
          <div className="summ-value sv-blue">{logs.length}</div>
          <div className="summ-sub">last {logs.length} operations</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Successful</div>
          <div className="summ-value sv-green">{logs.length - failures}</div>
          <div className="summ-sub">{logs.length ? `${Math.round(((logs.length - failures) / logs.length) * 100)}% success rate` : "—"}</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Failures</div>
          <div className={`summ-value${failures > 0 ? " sv-red" : " sv-dim"}`}>{failures}</div>
          <div className="summ-sub">{failures === 0 ? "No failures recorded" : `${failures} failed operation(s)`}</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Action types</div>
          <div className="summ-value sv-amber">{actions.length}</div>
          <div className="summ-sub">distinct operation types</div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Event log</span>
        <div className="al-filters">
          <button
            className={`al-filter-btn${filter === "all" ? " active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All
          </button>
          {actions.map((a) => (
            <button
              key={a}
              className={`al-filter-btn al-filter-${a.replace(".", "-")}${filter === a ? " active" : ""}`}
              onClick={() => setFilter(a)}
            >
              {ACTION_LABELS[a] ?? a}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading audit log…</span></div>
      ) : filtered.length === 0 ? (
        <div className="wl-empty">No events recorded yet.</div>
      ) : (
        <>
          <div className="al-table-wrap">
            <table className="al-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Actor</th>
                  <th>Status</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id} className={l.status === "failure" ? "al-row-fail" : ""}>
                    <td className="al-time">{fmtTime(l.created_at)}</td>
                    <td><ActionBadge action={l.action} /></td>
                    <td>
                      <span className="al-resource-type">{l.resource_type}</span>
                      <span className="al-resource-name">{l.resource_name}</span>
                    </td>
                    <td className="al-actor">{l.actor}</td>
                    <td><StatusBadge status={l.status} /></td>
                    <td className="al-detail">{l.detail ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {hasMore && (
            <div className="al-load-more">
              <button
                className="wl-btn-primary"
                onClick={() => load(offset, true)}
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
