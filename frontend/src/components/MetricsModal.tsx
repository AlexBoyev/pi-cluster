import { useEffect, useState } from "react";
import { getWorkloadMetrics } from "../api/workloads";
import type { WorkloadMetrics } from "../types/workload";
import "./MetricsModal.css";

interface Props {
  name: string;
  onClose: () => void;
}

function fmtCpu(cores: number): string {
  const m = Math.round(cores * 1000);
  return m < 1000 ? `${m} m` : `${(cores).toFixed(2)} cores`;
}

function fmtMem(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} Gi`;
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} Mi`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} Ki`;
  return `${bytes} B`;
}

function UsageBar({ pct, label }: { pct: number; label: string }) {
  const clamped = Math.min(100, pct);
  const cls = clamped >= 90 ? "mm-bar-crit" : clamped >= 70 ? "mm-bar-warn" : "mm-bar-ok";
  return (
    <div className="mm-bar-wrap">
      <div className="mm-bar-track">
        <div className={`mm-bar-fill ${cls}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="mm-bar-pct">{label}</span>
    </div>
  );
}

export default function MetricsModal({ name, onClose }: Props) {
  const [metrics, setMetrics] = useState<WorkloadMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setMetrics(await getWorkloadMetrics(name));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const cpuPct = metrics && metrics.cpu_limit_cores > 0
    ? (metrics.cpu_cores / metrics.cpu_limit_cores) * 100
    : 0;
  const memPct = metrics && metrics.memory_limit_bytes > 0
    ? (metrics.memory_bytes / metrics.memory_limit_bytes) * 100
    : 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box mm-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Live Metrics — {name}</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /><span>Querying Prometheus…</span></div>
        ) : error ? (
          <div className="err-banner">{error}</div>
        ) : metrics && !metrics.available ? (
          <div className="mm-unavailable">
            Prometheus is unavailable or no data has been collected yet for this workload.
            The workload may not be running, or metrics collection may still be starting.
          </div>
        ) : metrics ? (
          <div className="mm-body">
            <div className="mm-stat-row">
              <div className="mm-stat">
                <div className="mm-stat-label">Pods contributing</div>
                <div className="mm-stat-value">{metrics.pod_count}</div>
              </div>
            </div>

            <div className="mm-section">
              <div className="mm-section-label">CPU</div>
              <div className="mm-metric-row">
                <span className="mm-metric-name">Usage</span>
                <span className="mm-metric-val">{fmtCpu(metrics.cpu_cores)}</span>
              </div>
              <div className="mm-metric-row">
                <span className="mm-metric-name">Limit</span>
                <span className="mm-metric-val">{fmtCpu(metrics.cpu_limit_cores)}</span>
              </div>
              <UsageBar
                pct={cpuPct}
                label={`${cpuPct.toFixed(1)}% of limit`}
              />
            </div>

            <div className="mm-section">
              <div className="mm-section-label">Memory</div>
              <div className="mm-metric-row">
                <span className="mm-metric-name">Usage (working set)</span>
                <span className="mm-metric-val">{fmtMem(metrics.memory_bytes)}</span>
              </div>
              <div className="mm-metric-row">
                <span className="mm-metric-name">Limit</span>
                <span className="mm-metric-val">{fmtMem(metrics.memory_limit_bytes)}</span>
              </div>
              <UsageBar
                pct={memPct}
                label={`${memPct.toFixed(1)}% of limit`}
              />
            </div>

            <div className="mm-note">
              CPU averaged over 5-minute window · memory is working set bytes · data from Prometheus
            </div>
          </div>
        ) : null}

        <div className="mm-footer">
          <button className="wl-btn-primary" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button className="modal-cancel-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
