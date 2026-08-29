import { useEffect, useRef, useState } from "react";
import { getClusterEvents } from "../api/events";
import { listNamespaces } from "../api/namespaces";
import type { ClusterEvent } from "../types/k8s_event";
import "./EventsPage.css";

type TypeFilter = "all" | "Warning" | "Normal";

function fmtAge(iso: string | null): string {
  if (!iso) return "—";
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export default function EventsPage() {
  const [events, setEvents]       = useState<ClusterEvent[]>([]);
  const [namespaces, setNs]       = useState<string[]>([]);
  const [nsFilter, setNsFilter]   = useState("");
  const [typeFilter, setType]     = useState<TypeFilter>("all");
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [autoRefresh, setAuto]    = useState(true);
  const intervalRef               = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = () => {
    getClusterEvents(nsFilter || undefined, typeFilter === "all" ? undefined : typeFilter)
      .then((d) => { setEvents(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    listNamespaces()
      .then((ns) => setNs(ns.map((n) => n.name).sort()))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
  }, [nsFilter, typeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (autoRefresh) intervalRef.current = setInterval(load, 15_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, nsFilter, typeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const warnings = events.filter((e) => e.type === "Warning").length;

  return (
    <div className="ev-page">
      {error && <div className="err-banner">API error: {error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total events</div>
          <div className="summ-value sv-blue">{events.length}</div>
          <div className="summ-sub">across all namespaces</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Warnings</div>
          <div className={`summ-value${warnings > 0 ? " sv-amber" : " sv-dim"}`}>{warnings}</div>
          <div className="summ-sub">{warnings === 0 ? "No warnings" : "require attention"}</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Normal</div>
          <div className="summ-value sv-green">{events.length - warnings}</div>
          <div className="summ-sub">informational</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">Namespaces</div>
          <div className="summ-value sv-blue">{namespaces.length}</div>
          <div className="summ-sub">in cluster</div>
        </div>
      </div>

      <div className="ev-filter-bar">
        <div className="ev-filter-group">
          <span className="ev-filter-label">Namespace</span>
          <select
            className="ev-ns-select"
            value={nsFilter}
            onChange={(e) => setNsFilter(e.target.value)}
          >
            <option value="">All</option>
            {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="ev-filter-group">
          <span className="ev-filter-label">Type</span>
          {(["all", "Warning", "Normal"] as TypeFilter[]).map((t) => (
            <button
              key={t}
              className={`ev-pill${typeFilter === t ? ` ev-pill-active ev-pill-${t}` : ""}`}
              onClick={() => setType(t)}
            >
              {t === "all" ? "All" : t}
            </button>
          ))}
        </div>
        <div className="ev-filter-group ev-filter-right">
          <button
            className={`ev-pill${autoRefresh ? " ev-pill-active" : ""}`}
            onClick={() => setAuto((a) => !a)}
          >
            {autoRefresh ? "● Live" : "○ Paused"}
          </button>
          <button className="ev-pill" onClick={() => { setLoading(true); load(); }}>Refresh</button>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Cluster events</span>
        <span className="section-meta">newest first · {events.length} shown</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading events…</span></div>
      ) : events.length === 0 ? (
        <div className="ev-empty">No events found for the current filter.</div>
      ) : (
        <div className="ev-table-wrap">
          <table className="ev-table">
            <thead>
              <tr>
                <th>Age</th>
                <th>Type</th>
                <th>Reason</th>
                <th>Namespace / Object</th>
                <th>Message</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={i} className={e.type === "Warning" ? "ev-row-warn" : ""}>
                  <td className="ev-age">{fmtAge(e.last_time)}</td>
                  <td>
                    <span className={`ev-type ev-type-${e.type}`}>{e.type}</span>
                  </td>
                  <td className="ev-reason">{e.reason}</td>
                  <td className="ev-obj">
                    <span className="ev-ns">{e.namespace}</span>
                    <span className="ev-obj-name">{e.object_kind}/{e.object_name}</span>
                  </td>
                  <td className="ev-msg">{e.message}</td>
                  <td className="ev-count">{e.count > 1 ? e.count : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
