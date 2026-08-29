import { useEffect, useState } from "react";
import { getWorkloadHistory, rollbackWorkload } from "../api/workloads";
import type { DeploymentRevision } from "../types/workload";
import "./RollbackModal.css";

interface Props {
  name: string;
  onClose: () => void;
  onRolledBack: () => void;
}

function fmtAge(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function RollbackModal({ name, onClose, onRolledBack }: Props) {
  const [revisions, setRevisions] = useState<DeploymentRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const history = await getWorkloadHistory(name);
        setRevisions(history.revisions);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    })();
  }, [name]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleRollback() {
    if (selected === null) return;
    setRolling(true);
    setError(null);
    try {
      await rollbackWorkload(name, selected);
      onRolledBack();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rollback failed");
      setRolling(false);
    }
  }

  const selectedRevision = revisions.find((r) => r.revision === selected);
  const canRollback = selected !== null && !selectedRevision?.is_current;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box rb-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Rollback — {name}</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /><span>Loading revision history…</span></div>
        ) : error ? (
          <div className="err-banner">{error}</div>
        ) : revisions.length === 0 ? (
          <div className="rb-empty">No revision history available. Deploy or update the workload to build history.</div>
        ) : (
          <div className="rb-body">
            <p className="rb-hint">Select a previous revision to restore. The deployment will perform a rolling update to that pod template.</p>
            <div className="rb-list">
              {revisions.map((r) => (
                <div
                  key={r.revision}
                  className={`rb-row${r.is_current ? " rb-row-current" : ""}${selected === r.revision ? " rb-row-selected" : ""}`}
                  onClick={() => !r.is_current && setSelected(r.revision)}
                >
                  <div className="rb-rev-head">
                    <span className="rb-rev-num">#{r.revision}</span>
                    {r.is_current && <span className="rb-badge-current">current</span>}
                  </div>
                  <div className="rb-rev-image">{r.image}</div>
                  <div className="rb-rev-age">{fmtAge(r.created_at)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rb-footer">
          <button
            className="wl-btn-primary"
            onClick={handleRollback}
            disabled={!canRollback || rolling}
          >
            {rolling ? "Rolling back…" : "Roll back"}
          </button>
          <button className="modal-cancel-btn" onClick={onClose}>Cancel</button>
          {selected !== null && selectedRevision?.is_current && (
            <span className="rb-warn">This is the current revision</span>
          )}
        </div>
      </div>
    </div>
  );
}
