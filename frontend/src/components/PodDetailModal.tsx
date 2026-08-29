import { useEffect, useState } from "react";
import { getPodDetail } from "../api/pods";
import type { PodDetail } from "../types/pod";
import "./PodDetailModal.css";

interface Props {
  podName: string;
  namespace: string;
  onClose: () => void;
}

function phaseCls(p: string): string {
  if (p === "Running")   return "pd-running";
  if (p === "Pending")   return "pd-pending";
  if (p === "Failed")    return "pd-failed";
  if (p === "Succeeded") return "pd-succeeded";
  return "pd-unknown";
}

function condCls(s: string): string {
  return s === "True" ? "pd-cond-true" : s === "False" ? "pd-cond-false" : "pd-cond-unknown";
}

function evtCls(t: string): string {
  return t === "Warning" ? "pd-evt-warn" : "pd-evt-normal";
}

function fmtAge(s: string | null): string {
  if (!s) return "—";
  const sec = Math.floor((Date.now() - new Date(s).getTime()) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h`;
  return `${Math.floor(sec / 86400)}d`;
}

export default function PodDetailModal({ podName, namespace, onClose }: Props) {
  const [detail, setDetail] = useState<PodDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPodDetail(namespace, podName)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load pod"))
      .finally(() => setLoading(false));
  }, [podName, namespace]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="pd-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="pd-modal">
        <div className="pd-header">
          <div className="pd-header-left">
            <span className="pd-title">{podName}</span>
            <span className="pd-ns">{namespace}</span>
            {detail && (
              <span className={`pd-phase ${phaseCls(detail.phase)}`}>{detail.phase}</span>
            )}
          </div>
          <button className="pd-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div className="pd-loading"><div className="spinner" /><span>Loading pod detail…</span></div>
        ) : error ? (
          <div className="pd-error">{error}</div>
        ) : detail ? (
          <div className="pd-body">
            {/* Meta */}
            <div className="pd-meta-grid">
              <div className="pd-meta-item">
                <span className="pd-meta-lbl">Node</span>
                <span className="pd-meta-val">{detail.node ?? "—"}</span>
              </div>
              <div className="pd-meta-item">
                <span className="pd-meta-lbl">Pod IP</span>
                <span className="pd-meta-val pd-mono">{detail.pod_ip ?? "—"}</span>
              </div>
              <div className="pd-meta-item">
                <span className="pd-meta-lbl">QoS Class</span>
                <span className="pd-meta-val">{detail.qos_class ?? "—"}</span>
              </div>
              <div className="pd-meta-item">
                <span className="pd-meta-lbl">Age</span>
                <span className="pd-meta-val">{fmtAge(detail.start_time)}</span>
              </div>
            </div>

            {/* Containers */}
            <div className="pd-section-title">Containers</div>
            <div className="pd-table-wrap">
              <table className="pd-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Image</th>
                    <th>Ready</th>
                    <th>Restarts</th>
                    <th>CPU req / limit</th>
                    <th>Mem req / limit</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.containers.map((c) => (
                    <tr key={c.name}>
                      <td className="pd-mono pd-bold">{c.name}</td>
                      <td className="pd-mono pd-img">{c.image}</td>
                      <td>
                        <span className={`pd-ready-badge ${c.ready ? "pd-ready" : "pd-not-ready"}`}>
                          {c.ready ? "Ready" : "Not ready"}
                        </span>
                      </td>
                      <td className={`pd-mono ${c.restart_count > 0 ? "pd-warn-text" : ""}`}>
                        {c.restart_count}
                      </td>
                      <td className="pd-mono pd-dim">
                        {c.cpu_request ?? "—"} / {c.cpu_limit ?? "—"}
                      </td>
                      <td className="pd-mono pd-dim">
                        {c.memory_request ?? "—"} / {c.memory_limit ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Conditions */}
            {detail.conditions.length > 0 && (
              <>
                <div className="pd-section-title">Conditions</div>
                <div className="pd-conditions">
                  {detail.conditions.map((cond) => (
                    <div key={cond.type} className="pd-condition">
                      <span className="pd-cond-type">{cond.type}</span>
                      <span className={`pd-cond-status ${condCls(cond.status)}`}>{cond.status}</span>
                      {cond.reason && <span className="pd-cond-reason">{cond.reason}</span>}
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Events */}
            {detail.events.length > 0 && (
              <>
                <div className="pd-section-title">Recent Events</div>
                <div className="pd-events">
                  {detail.events.map((evt, i) => (
                    <div key={i} className={`pd-event ${evtCls(evt.type)}`}>
                      <div className="pd-evt-header">
                        <span className="pd-evt-reason">{evt.reason}</span>
                        <span className="pd-evt-age">{fmtAge(evt.last_time)}</span>
                        {evt.count > 1 && <span className="pd-evt-count">×{evt.count}</span>}
                      </div>
                      <div className="pd-evt-msg">{evt.message}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
