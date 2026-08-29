import { useEffect, useRef, useState } from "react";
import { listAuditLogs } from "../api/audit";
import type { AuditLog } from "../types/audit";
import "./AuditPage.css";

const PAGE_SIZE = 50;

const ACTION_LABELS: Record<string, string> = {
  "workload.create":       "Deploy",
  "workload.delete":       "Delete",
  "workload.scale":        "Scale",
  "workload.image_update": "Image",
  "workload.env_update":   "Env",
  "workload.restart":      "Restart",
  "workload.probes_update":"Probes",
  "workload.resources_update": "Resources",
  "node.cordon":           "Cordon",
  "node.uncordon":         "Uncordon",
  "node.drain":            "Drain",
};

function ActionBadge({ action }: { action: string }) {
  const cls = action.replace(/\./g, "-").replace(/_/g, "-");
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

type StatusFilter = "all" | "success" | "failure";
type ResourceFilter = "all" | "workload" | "node";

export default function AuditPage() {
  const [logs, setLogs]           = useState<AuditLog[]>([]);
  const [offset, setOffset]       = useState(0);
  const [hasMore, setHasMore]     = useState(true);
  const [loading, setLoading]     = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [statusFilter, setStatusFilter]     = useState<StatusFilter>("all");
  const [resourceFilter, setResourceFilter] = useState<ResourceFilter>("all");

  const statusRef   = useRef(statusFilter);
  const resourceRef = useRef(resourceFilter);
  useEffect(() => { statusRef.current = statusFilter; });
  useEffect(() => { resourceRef.current = resourceFilter; });

  const loadData = async (off: number, append: boolean, sf: StatusFilter, rf: ResourceFilter) => {
    append ? setLoadingMore(true) : setLoading(true);
    setError(null);
    try {
      const data = await listAuditLogs(
        PAGE_SIZE, off,
        sf !== "all" ? sf : undefined,
        rf !== "all" ? rf : undefined,
      );
      setLogs((prev) => append ? [...prev, ...data] : data);
      setHasMore(data.length === PAGE_SIZE);
      setOffset(off + data.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      append ? setLoadingMore(false) : setLoading(false);
    }
  };

  useEffect(() => {
    setLogs([]);
    setOffset(0);
    setHasMore(true);
    loadData(0, false, statusFilter, resourceFilter);
  }, [statusFilter, resourceFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const failures    = logs.filter((l) => l.status === "failure").length;
  const actionTypes = Array.from(new Set(logs.map((l) => l.action))).sort();

  return (
    <div className="al-page">
      {error && <div className="err-banner">{error}</div>}

      {/* Summary */}
      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total events</div>
          <div className="summ-value sv-blue">{logs.length}</div>
          <div className="summ-sub">loaded in this view</div>
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
          <div className="summ-value sv-amber">{actionTypes.length}</div>
          <div className="summ-sub">distinct operation types</div>
        </div>
      </div>

      {/* Section header + filter pills */}
      <div className="section-header" style={{ marginTop: "1.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <span className="section-title">
          Event log
          {(statusFilter !== "all" || resourceFilter !== "all") && logs.length > 0 && (
            <span className="al-filter-count"> — {logs.length} result{logs.length !== 1 ? "s" : ""}</span>
          )}
        </span>
        <div className="al-filters">
          <span className="al-filter-label">Status</span>
          {(["all", "success", "failure"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              className={`al-pill al-pill-status-${s}${statusFilter === s ? " al-pill-active" : ""}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "All" : s === "success" ? "Success" : "Failure"}
            </button>
          ))}

          <span className="al-filter-sep" />

          <span className="al-filter-label">Type</span>
          {(["all", "workload", "node"] as ResourceFilter[]).map((r) => (
            <button
              key={r}
              className={`al-pill al-pill-type-${r}${resourceFilter === r ? " al-pill-active" : ""}`}
              onClick={() => setResourceFilter(r)}
            >
              {r === "all" ? "All" : r === "workload" ? "Workload" : "Node"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading audit log…</span></div>
      ) : logs.length === 0 ? (
        <div className="wl-empty">No events match the current filter.</div>
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
                {logs.map((l) => (
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
                onClick={() => loadData(offset, true, statusFilter, resourceFilter)}
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
