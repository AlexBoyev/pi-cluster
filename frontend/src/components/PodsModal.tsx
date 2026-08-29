import { useCallback, useEffect, useState } from "react";
import { getWorkloadPods } from "../api/workloads";
import type { PodInfo } from "../types/workload";
import "./PodsModal.css";

interface Props {
  workloadName: string;
  onClose: () => void;
}

function age(ts: string | null): string {
  if (!ts) return "—";
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

function phaseCls(phase: string): string {
  if (phase === "Running") return "pod-phase-running";
  if (phase === "Pending") return "pod-phase-pending";
  if (phase === "Failed") return "pod-phase-failed";
  if (phase === "Succeeded") return "pod-phase-succeeded";
  return "pod-phase-unknown";
}

export default function PodsModal({ workloadName, onClose }: Props) {
  const [pods, setPods] = useState<PodInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPods(await getWorkloadPods(workloadName));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch pods");
    } finally {
      setLoading(false);
    }
  }, [workloadName]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="pods-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="pods-modal">
        <div className="pods-header">
          <div className="pods-title">
            <span className="pods-name">{workloadName}</span>
            <span className="pods-sub">pods</span>
          </div>
          <div className="pods-header-actions">
            <button className="pods-btn-refresh" onClick={load} disabled={loading}>
              {loading ? "…" : "Refresh"}
            </button>
            <button className="pods-btn-close" onClick={onClose}>✕</button>
          </div>
        </div>

        <div className="pods-body">
          {error && <div className="pods-error">{error}</div>}
          {loading && !pods.length ? (
            <div className="pods-loading"><div className="spinner" /><span>Loading pods…</span></div>
          ) : pods.length === 0 ? (
            <div className="pods-empty">No pods found for this workload.</div>
          ) : (
            <table className="pods-table">
              <thead>
                <tr>
                  <th>Pod name</th>
                  <th>Phase</th>
                  <th>Ready</th>
                  <th>Node</th>
                  <th>IP</th>
                  <th>Age</th>
                </tr>
              </thead>
              <tbody>
                {pods.map((p) => (
                  <tr key={p.name}>
                    <td className="pods-pod-name">{p.name}</td>
                    <td><span className={`pods-phase ${phaseCls(p.phase)}`}>{p.phase}</span></td>
                    <td className="pods-mono">{p.ready}/{p.total}</td>
                    <td className="pods-mono">{p.node ?? "—"}</td>
                    <td className="pods-mono">{p.pod_ip ?? "—"}</td>
                    <td className="pods-mono">{age(p.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
