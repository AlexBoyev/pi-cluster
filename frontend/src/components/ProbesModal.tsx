import { useEffect, useState } from "react";
import { updateWorkloadProbes } from "../api/workloads";
import type { Workload } from "../types/workload";
import "./ProbesModal.css";

interface Props {
  workload: Workload;
  onClose: () => void;
  onSaved: () => void;
}

export default function ProbesModal({ workload, onClose, onSaved }: Props) {
  const [liveness, setLiveness] = useState(workload.liveness_path ?? "");
  const [readiness, setReadiness] = useState(workload.readiness_path ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateWorkloadProbes(
        workload.name,
        liveness.trim() || null,
        readiness.trim() || null,
      );
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update probes");
    } finally {
      setSaving(false);
    }
  }

  const noPort = !workload.container_port;

  return (
    <div className="pm-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="pm-modal">
        <div className="pm-header">
          <div className="pm-title">
            <span className="pm-name">{workload.name}</span>
            <span className="pm-sub">health probes</span>
          </div>
          <button className="pm-btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="pm-body">
          {error && <div className="pm-error">{error}</div>}

          {noPort ? (
            <div className="pm-warn">
              This workload has no container port. Probes require a port and must be configured at deploy time.
            </div>
          ) : (
            <div className="pm-hint">
              Both probes use port <strong>{workload.container_port}</strong>. Liveness restarts the pod on failure; readiness stops traffic until the pod passes. Leave a field empty to remove that probe.
            </div>
          )}

          <div className="pm-grid">
            <div className="pm-field">
              <label className="pm-label">Liveness probe path</label>
              <input
                className="pm-input"
                value={liveness}
                onChange={(e) => setLiveness(e.target.value)}
                placeholder="/health"
                disabled={saving || noPort}
              />
              <span className="pm-hint-sm">Failure → pod is restarted (OOM equivalent)</span>
            </div>
            <div className="pm-field">
              <label className="pm-label">Readiness probe path</label>
              <input
                className="pm-input"
                value={readiness}
                onChange={(e) => setReadiness(e.target.value)}
                placeholder="/ready"
                disabled={saving || noPort}
              />
              <span className="pm-hint-sm">Failure → pod removed from Service endpoints</span>
            </div>
          </div>
        </div>

        <div className="pm-footer">
          <button className="pm-btn-cancel" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="pm-btn-save" onClick={handleSave} disabled={saving || noPort}>
            {saving ? "Applying…" : "Apply probes"}
          </button>
        </div>
      </div>
    </div>
  );
}
