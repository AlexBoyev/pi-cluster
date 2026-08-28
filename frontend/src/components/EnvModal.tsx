import { useEffect, useState } from "react";
import { updateWorkloadEnv } from "../api/workloads";
import "./EnvModal.css";

interface Props {
  workloadName: string;
  initialEnv: Record<string, string>;
  onClose: () => void;
  onSaved: () => void;
}

interface KVPair { key: string; value: string; }

function envToRows(env: Record<string, string>): KVPair[] {
  const rows = Object.entries(env).map(([key, value]) => ({ key, value }));
  return rows.length ? rows : [{ key: "", value: "" }];
}

export default function EnvModal({ workloadName, initialEnv, onClose, onSaved }: Props) {
  const [rows, setRows] = useState<KVPair[]>(envToRows(initialEnv));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function setRow(i: number, field: "key" | "value", val: string) {
    setRows((prev) => prev.map((r, idx) => idx === i ? { ...r, [field]: val } : r));
  }

  function addRow() {
    setRows((prev) => [...prev, { key: "", value: "" }]);
  }

  function removeRow(i: number) {
    setRows((prev) => prev.length === 1 ? [{ key: "", value: "" }] : prev.filter((_, idx) => idx !== i));
  }

  async function handleSave() {
    const env: Record<string, string> = {};
    for (const { key, value } of rows) {
      if (key.trim()) env[key.trim()] = value;
    }
    setSaving(true);
    setError(null);
    try {
      await updateWorkloadEnv(workloadName, env);
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update env vars");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="env-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="env-modal">
        <div className="env-header">
          <div className="env-title">
            <span className="env-name">{workloadName}</span>
            <span className="env-sub">environment variables</span>
          </div>
          <button className="env-btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="env-body">
          {error && <div className="env-error">{error}</div>}
          <div className="env-table">
            <div className="env-thead">
              <span>Key</span>
              <span>Value</span>
              <span></span>
            </div>
            {rows.map((row, i) => (
              <div className="env-row" key={i}>
                <input
                  className="env-input"
                  placeholder="KEY"
                  value={row.key}
                  onChange={(e) => setRow(i, "key", e.target.value)}
                  disabled={saving}
                />
                <input
                  className="env-input"
                  placeholder="value"
                  value={row.value}
                  onChange={(e) => setRow(i, "value", e.target.value)}
                  disabled={saving}
                />
                <button className="env-btn-remove" onClick={() => removeRow(i)} disabled={saving}>✕</button>
              </div>
            ))}
          </div>
          <button className="env-btn-add" onClick={addRow} disabled={saving}>+ Add variable</button>
        </div>

        <div className="env-footer">
          <button className="env-btn-cancel" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="env-btn-save" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save & restart pods"}
          </button>
        </div>
      </div>
    </div>
  );
}
