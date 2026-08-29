import { FormEvent, useEffect, useState } from "react";
import { createConfigMap, deleteConfigMap, getConfigMap, listConfigMaps, updateConfigMap } from "../api/configmaps";
import { listNamespaces } from "../api/namespaces";
import type { ConfigMapDetail, ConfigMapSummary } from "../types/configmap";
import "./ConfigMapsPage.css";

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function parseKv(raw: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of raw.split("\n")) {
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const k = line.slice(0, eq).trim();
    const v = line.slice(eq + 1);
    if (k) out[k] = v;
  }
  return out;
}

function toKv(data: Record<string, string>): string {
  return Object.entries(data)
    .map(([k, v]) => `${k}=${v}`)
    .join("\n");
}

export default function ConfigMapsPage() {
  const [configMaps, setConfigMaps] = useState<ConfigMapSummary[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>(["pi-apps"]);
  const [ns, setNs] = useState("pi-apps");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingName, setDeletingName] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<ConfigMapDetail | null>(null);
  const [editRaw, setEditRaw] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [form, setForm] = useState({ name: "", data: "" });

  const refresh = async () => {
    setLoading(true);
    try {
      const cms = await listConfigMaps(ns);
      setConfigMaps(cms);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load ConfigMaps");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    listNamespaces()
      .then((nsList) => setNamespaces(nsList.map((n) => n.name)))
      .catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [ns]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createConfigMap(form.name, ns, parseKv(form.data));
      setForm({ name: "", data: "" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create ConfigMap");
    } finally {
      setCreating(false);
    }
  }

  async function handleOpenEdit(name: string) {
    try {
      const detail = await getConfigMap(name, ns);
      setEditTarget(detail);
      setEditRaw(toKv(detail.data));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load ConfigMap");
    }
  }

  async function handleSaveEdit() {
    if (!editTarget) return;
    setEditSaving(true);
    setError(null);
    try {
      await updateConfigMap(editTarget.name, editTarget.namespace, parseKv(editRaw));
      setEditTarget(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update ConfigMap");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleDelete(name: string) {
    setDeletingName(name);
    setError(null);
    try {
      await deleteConfigMap(name, ns);
      setConfirmDelete(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete ConfigMap");
    } finally {
      setDeletingName(null);
    }
  }

  return (
    <div className="cm-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">ConfigMaps</div>
          <div className="summ-value sv-blue">{configMaps.length}</div>
          <div className="summ-sub">in {ns}</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Total keys</div>
          <div className="summ-value sv-amber">{configMaps.reduce((a, c) => a + c.data_keys.length, 0)}</div>
          <div className="summ-sub">across all maps</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Create ConfigMap</span>
        <div className="cm-ns-wrap">
          <label className="cm-ns-lbl">Namespace:</label>
          <select className="cm-ns-select" value={ns} onChange={(e) => setNs(e.target.value)}>
            {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      <div className="cm-form-card">
        <form className="cm-form" onSubmit={handleCreate}>
          <div className="cm-field">
            <label className="cm-label">Name</label>
            <input
              className="cm-input"
              placeholder="my-config"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              pattern="^[a-z][a-z0-9-]{0,62}$"
              required
              disabled={creating}
            />
          </div>
          <div className="cm-field cm-field-wide">
            <label className="cm-label">Key=value pairs (one per line)</label>
            <textarea
              className="cm-textarea"
              placeholder={"DB_HOST=postgres\nDB_PORT=5432\nAPP_ENV=production"}
              value={form.data}
              onChange={(e) => setForm((f) => ({ ...f, data: e.target.value }))}
              rows={4}
              disabled={creating}
            />
          </div>
          <div className="cm-field cm-field-submit">
            <button className="cm-btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">ConfigMaps in {ns}</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading ConfigMaps…</span></div>
      ) : configMaps.length === 0 ? (
        <div className="cm-empty">No ConfigMaps in namespace <code>{ns}</code>.</div>
      ) : (
        <div className="cm-table-wrap">
          <table className="cm-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Keys</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {configMaps.map((cm) => (
                <tr key={cm.name}>
                  <td className="cm-name">{cm.name}</td>
                  <td>
                    <div className="cm-keys">
                      {cm.data_keys.length === 0 ? (
                        <span className="cm-no-keys">empty</span>
                      ) : (
                        cm.data_keys.map((k) => (
                          <span key={k} className="cm-key-tag">{k}</span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="cm-date">{fmtDate(cm.created_at)}</td>
                  <td>
                    <div className="cm-actions">
                      <button className="cm-btn-edit" onClick={() => handleOpenEdit(cm.name)}>
                        Edit
                      </button>
                      {confirmDelete === cm.name ? (
                        <div className="cm-confirm">
                          <span className="cm-confirm-txt">Delete?</span>
                          <button
                            className="cm-btn-del-confirm"
                            onClick={() => handleDelete(cm.name)}
                            disabled={deletingName === cm.name}
                          >
                            {deletingName === cm.name ? "…" : "Yes"}
                          </button>
                          <button className="cm-btn-cancel" onClick={() => setConfirmDelete(null)}>No</button>
                        </div>
                      ) : (
                        <button className="cm-btn-del" onClick={() => setConfirmDelete(cm.name)}>
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editTarget && (
        <div className="cm-overlay" onClick={(e) => { if (e.target === e.currentTarget) setEditTarget(null); }}>
          <div className="cm-modal">
            <div className="cm-modal-header">
              <div className="cm-modal-title">
                <span className="cm-modal-name">{editTarget.name}</span>
                <span className="cm-modal-sub">{editTarget.namespace}</span>
              </div>
              <button className="cm-modal-close" onClick={() => setEditTarget(null)}>✕</button>
            </div>
            <div className="cm-modal-body">
              <div className="cm-modal-hint">
                Edit key=value pairs below (one per line). Empty lines are ignored.
              </div>
              <textarea
                className="cm-modal-textarea"
                value={editRaw}
                onChange={(e) => setEditRaw(e.target.value)}
                rows={12}
                disabled={editSaving}
              />
            </div>
            <div className="cm-modal-footer">
              <button className="cm-btn-cancel" onClick={() => setEditTarget(null)} disabled={editSaving}>
                Cancel
              </button>
              <button className="cm-btn-save" onClick={handleSaveEdit} disabled={editSaving}>
                {editSaving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
