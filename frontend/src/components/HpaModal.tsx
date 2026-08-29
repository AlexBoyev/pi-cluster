import { useEffect, useState } from "react";
import { applyHpa, deleteHpa, getHpa } from "../api/workloads";
import type { HPAInfo, Workload } from "../types/workload";
import "./HpaModal.css";

interface Props {
  workload: Workload;
  onClose: () => void;
  onSaved: () => void;
}

export default function HpaModal({ workload, onClose, onSaved }: Props) {
  const [hpa, setHpa] = useState<HPAInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minReplicas, setMinReplicas] = useState("1");
  const [maxReplicas, setMaxReplicas] = useState("5");
  const [cpuTarget, setCpuTarget] = useState("70");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    getHpa(workload.name, workload.namespace)
      .then((data) => {
        setHpa(data);
        if (data) {
          setMinReplicas(String(data.min_replicas ?? 1));
          setMaxReplicas(String(data.max_replicas ?? 5));
          setCpuTarget(String(data.cpu_target_pct ?? 70));
        }
      })
      .catch(() => setHpa(null))
      .finally(() => setLoading(false));
  }, [workload.name, workload.namespace]);

  async function handleSave() {
    const min = parseInt(minReplicas, 10);
    const max = parseInt(maxReplicas, 10);
    const cpu = parseInt(cpuTarget, 10);
    if (isNaN(min) || isNaN(max) || isNaN(cpu)) return;
    if (min > max) { setError("Min replicas cannot exceed max replicas"); return; }
    setSaving(true);
    setError(null);
    try {
      const updated = await applyHpa(workload.name, workload.namespace, { min_replicas: min, max_replicas: max, cpu_target_pct: cpu });
      setHpa(updated);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply HPA");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteHpa(workload.name, workload.namespace);
      setHpa(null);
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete HPA");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="hpa-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="hpa-modal">
        <div className="hpa-header">
          <div className="hpa-title">
            <span className="hpa-name">{workload.name}</span>
            <span className="hpa-sub">horizontal pod autoscaler</span>
          </div>
          <button className="hpa-btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="hpa-body">
          {error && <div className="hpa-error">{error}</div>}

          {loading ? (
            <div className="hpa-loading"><div className="spinner" /> Loading HPA status…</div>
          ) : (
            <>
              {hpa ? (
                <div className="hpa-status-bar">
                  <div className="hpa-stat">
                    <span className="hpa-stat-lbl">Current replicas</span>
                    <span className="hpa-stat-val">{hpa.current_replicas ?? "—"}</span>
                  </div>
                  <div className="hpa-stat">
                    <span className="hpa-stat-lbl">CPU utilization</span>
                    <span className={`hpa-stat-val${hpa.current_cpu_pct != null && hpa.cpu_target_pct != null && hpa.current_cpu_pct > hpa.cpu_target_pct ? " hpa-over" : ""}`}>
                      {hpa.current_cpu_pct != null ? `${hpa.current_cpu_pct}%` : "—"}
                    </span>
                  </div>
                  <div className="hpa-stat">
                    <span className="hpa-stat-lbl">Target CPU</span>
                    <span className="hpa-stat-val">{hpa.cpu_target_pct != null ? `${hpa.cpu_target_pct}%` : "—"}</span>
                  </div>
                  <div className="hpa-stat">
                    <span className="hpa-stat-lbl">Replica range</span>
                    <span className="hpa-stat-val">{hpa.min_replicas ?? "—"} – {hpa.max_replicas ?? "—"}</span>
                  </div>
                </div>
              ) : (
                <div className="hpa-none">No HPA configured for this workload.</div>
              )}

              <div className="hpa-hint">
                Configure HPA to automatically scale pods based on CPU utilization.
                Requires metrics-server installed in the cluster.
              </div>

              <div className="hpa-grid">
                <div className="hpa-field">
                  <label className="hpa-label">Min replicas</label>
                  <input
                    className="hpa-input"
                    type="number"
                    min={1}
                    max={10}
                    value={minReplicas}
                    onChange={(e) => setMinReplicas(e.target.value)}
                    disabled={saving}
                  />
                </div>
                <div className="hpa-field">
                  <label className="hpa-label">Max replicas</label>
                  <input
                    className="hpa-input"
                    type="number"
                    min={1}
                    max={20}
                    value={maxReplicas}
                    onChange={(e) => setMaxReplicas(e.target.value)}
                    disabled={saving}
                  />
                </div>
                <div className="hpa-field">
                  <label className="hpa-label">CPU target utilization (%)</label>
                  <input
                    className="hpa-input"
                    type="number"
                    min={10}
                    max={100}
                    value={cpuTarget}
                    onChange={(e) => setCpuTarget(e.target.value)}
                    disabled={saving}
                  />
                  <span className="hpa-hint-sm">Scale up when average CPU exceeds this %</span>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="hpa-footer">
          {hpa && (
            <button className="hpa-btn-delete" onClick={handleDelete} disabled={deleting || saving}>
              {deleting ? "Removing…" : "Remove HPA"}
            </button>
          )}
          <div className="hpa-footer-right">
            <button className="hpa-btn-cancel" onClick={onClose} disabled={saving || deleting}>Cancel</button>
            <button className="hpa-btn-save" onClick={handleSave} disabled={saving || loading || deleting}>
              {saving ? "Applying…" : hpa ? "Update HPA" : "Enable HPA"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
