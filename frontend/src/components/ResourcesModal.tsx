import { useEffect, useState } from "react";
import { updateWorkloadResources } from "../api/workloads";
import type { Workload } from "../types/workload";
import "./ResourcesModal.css";

interface Props {
  workload: Workload;
  onClose: () => void;
  onSaved: () => void;
}

export default function ResourcesModal({ workload, onClose, onSaved }: Props) {
  const [cpuLimit, setCpuLimit] = useState(workload.cpu_limit);
  const [memLimit, setMemLimit] = useState(workload.memory_limit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSave() {
    if (!cpuLimit.trim() || !memLimit.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await updateWorkloadResources(workload.name, cpuLimit.trim(), memLimit.trim());
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update resources");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rm-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="rm-modal">
        <div className="rm-header">
          <div className="rm-title">
            <span className="rm-name">{workload.name}</span>
            <span className="rm-sub">resource limits</span>
          </div>
          <button className="rm-btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="rm-body">
          {error && <div className="rm-error">{error}</div>}

          <div className="rm-hint">
            Requests are set at deploy time. Limits cap the maximum a pod may consume —
            exceeding memory causes an OOM kill; exceeding CPU causes throttling.
          </div>

          <div className="rm-grid">
            <div className="rm-field">
              <label className="rm-label">CPU request (fixed at deploy)</label>
              <div className="rm-static">{workload.image ? "100m" : "—"}</div>
            </div>
            <div className="rm-field">
              <label className="rm-label">CPU limit</label>
              <input
                className="rm-input"
                value={cpuLimit}
                onChange={(e) => setCpuLimit(e.target.value)}
                placeholder="500m"
                disabled={saving}
              />
              <span className="rm-hint-sm">e.g. 250m, 500m, 1</span>
            </div>
            <div className="rm-field">
              <label className="rm-label">Memory request (fixed at deploy)</label>
              <div className="rm-static">{workload.image ? "128Mi" : "—"}</div>
            </div>
            <div className="rm-field">
              <label className="rm-label">Memory limit</label>
              <input
                className="rm-input"
                value={memLimit}
                onChange={(e) => setMemLimit(e.target.value)}
                placeholder="256Mi"
                disabled={saving}
              />
              <span className="rm-hint-sm">e.g. 128Mi, 256Mi, 1Gi</span>
            </div>
          </div>
        </div>

        <div className="rm-footer">
          <button className="rm-btn-cancel" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="rm-btn-save" onClick={handleSave} disabled={saving}>
            {saving ? "Applying…" : "Apply limits"}
          </button>
        </div>
      </div>
    </div>
  );
}
