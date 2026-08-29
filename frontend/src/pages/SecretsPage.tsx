import { FormEvent, useEffect, useState } from "react";
import { createSecret, deleteSecret, getSecret, listSecrets, updateSecret } from "../api/secrets";
import { listNamespaces } from "../api/namespaces";
import type { SecretDetail, SecretSummary } from "../types/secret";
import "./SecretsPage.css";

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
  return Object.entries(data).map(([k, v]) => `${k}=${v}`).join("\n");
}

function TypeBadge({ type }: { type: string }) {
  const short = type.split("/").pop() || type;
  const cls = type === "Opaque" ? "sc-opaque" : type.includes("tls") ? "sc-tls" : type.includes("dockerconfig") ? "sc-docker" : "sc-other";
  return <span className={`sec-type-badge ${cls}`}>{short}</span>;
}

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretSummary[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>(["pi-apps"]);
  const [ns, setNs] = useState("pi-apps");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingName, setDeletingName] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<SecretDetail | null>(null);
  const [editRaw, setEditRaw] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const [form, setForm] = useState({ name: "", data: "", type: "Opaque" });

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await listSecrets(ns);
      setSecrets(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load secrets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    listNamespaces()
      .then((list) => setNamespaces(list.map((n) => n.name)))
      .catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [ns]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createSecret(form.name, ns, parseKv(form.data), form.type);
      setForm({ name: "", data: "", type: "Opaque" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create secret");
    } finally {
      setCreating(false);
    }
  }

  async function handleOpenEdit(name: string) {
    try {
      const detail = await getSecret(name, ns);
      setEditTarget(detail);
      setEditRaw(toKv(detail.data));
      setRevealed(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load secret");
    }
  }

  async function handleSaveEdit() {
    if (!editTarget) return;
    setEditSaving(true);
    setError(null);
    try {
      await updateSecret(editTarget.name, editTarget.namespace, parseKv(editRaw));
      setEditTarget(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update secret");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleDelete(name: string) {
    setDeletingName(name);
    setError(null);
    try {
      await deleteSecret(name, ns);
      setConfirmDelete(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete secret");
    } finally {
      setDeletingName(null);
    }
  }

  function toggleReveal(key: string) {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  return (
    <div className="sec-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Secrets</div>
          <div className="summ-value sv-blue">{secrets.length}</div>
          <div className="summ-sub">in {ns}</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Total keys</div>
          <div className="summ-value sv-amber">{secrets.reduce((a, s) => a + s.data_keys.length, 0)}</div>
          <div className="summ-sub">across all secrets</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">TLS secrets</div>
          <div className="summ-value sv-red">{secrets.filter(s => s.type.includes("tls")).length}</div>
          <div className="summ-sub">certificates</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Create secret</span>
        <div className="sec-ns-wrap">
          <label className="sec-ns-lbl">Namespace:</label>
          <select className="sec-ns-select" value={ns} onChange={(e) => setNs(e.target.value)}>
            {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      <div className="sec-form-card">
        <form className="sec-form" onSubmit={handleCreate}>
          <div className="sec-field">
            <label className="sec-label">Name</label>
            <input
              className="sec-input"
              placeholder="my-secret"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              pattern="^[a-z][a-z0-9-]{0,62}$"
              required
              disabled={creating}
            />
          </div>
          <div className="sec-field">
            <label className="sec-label">Type</label>
            <select
              className="sec-input"
              value={form.type}
              onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              disabled={creating}
            >
              <option value="Opaque">Opaque</option>
              <option value="kubernetes.io/tls">kubernetes.io/tls</option>
              <option value="kubernetes.io/dockerconfigjson">kubernetes.io/dockerconfigjson</option>
            </select>
          </div>
          <div className="sec-field sec-field-wide">
            <label className="sec-label">Key=value pairs (one per line)</label>
            <textarea
              className="sec-textarea"
              placeholder={"DB_PASSWORD=supersecret\nAPI_KEY=abc123"}
              value={form.data}
              onChange={(e) => setForm((f) => ({ ...f, data: e.target.value }))}
              rows={4}
              disabled={creating}
            />
          </div>
          <div className="sec-field sec-field-submit">
            <button className="sec-btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create secret"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Secrets in {ns}</span>
        <span className="sec-warn">⚠ Values are masked by default. Admin-only access.</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading secrets…</span></div>
      ) : secrets.length === 0 ? (
        <div className="sec-empty">No secrets in namespace <code>{ns}</code>.</div>
      ) : (
        <div className="sec-table-wrap">
          <table className="sec-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Keys</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {secrets.map((s) => (
                <tr key={s.name}>
                  <td className="sec-name">{s.name}</td>
                  <td><TypeBadge type={s.type} /></td>
                  <td>
                    <div className="sec-keys">
                      {s.data_keys.length === 0 ? (
                        <span className="sec-no-keys">empty</span>
                      ) : (
                        s.data_keys.map((k) => (
                          <span key={k} className="sec-key-tag">{k}</span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="sec-date">{fmtDate(s.created_at)}</td>
                  <td>
                    <div className="sec-actions">
                      <button className="sec-btn-edit" onClick={() => handleOpenEdit(s.name)}>
                        View / Edit
                      </button>
                      {confirmDelete === s.name ? (
                        <div className="sec-confirm">
                          <span className="sec-confirm-txt">Delete?</span>
                          <button
                            className="sec-btn-del-confirm"
                            onClick={() => handleDelete(s.name)}
                            disabled={deletingName === s.name}
                          >
                            {deletingName === s.name ? "…" : "Yes"}
                          </button>
                          <button className="sec-btn-cancel" onClick={() => setConfirmDelete(null)}>No</button>
                        </div>
                      ) : (
                        <button className="sec-btn-del" onClick={() => setConfirmDelete(s.name)}>
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
        <div className="sec-overlay" onClick={(e) => { if (e.target === e.currentTarget) setEditTarget(null); }}>
          <div className="sec-modal">
            <div className="sec-modal-header">
              <div className="sec-modal-title">
                <span className="sec-modal-name">{editTarget.name}</span>
                <TypeBadge type={editTarget.type} />
              </div>
              <button className="sec-modal-close" onClick={() => setEditTarget(null)}>✕</button>
            </div>
            <div className="sec-modal-body">
              <div className="sec-modal-hint">
                Secret values are stored base64-encoded in Kubernetes. Edit as plain text below.
              </div>
              <div className="sec-kv-list">
                {Object.entries(editTarget.data).map(([k, v]) => (
                  <div key={k} className="sec-kv-row">
                    <span className="sec-kv-key">{k}</span>
                    <span className="sec-kv-val">
                      {revealed.has(k) ? v : "••••••••"}
                    </span>
                    <button className="sec-kv-reveal" onClick={() => toggleReveal(k)}>
                      {revealed.has(k) ? "Hide" : "Reveal"}
                    </button>
                  </div>
                ))}
              </div>
              <div className="sec-modal-divider" />
              <div className="sec-modal-edit-lbl">Edit (KEY=value, one per line):</div>
              <textarea
                className="sec-modal-textarea"
                value={editRaw}
                onChange={(e) => setEditRaw(e.target.value)}
                rows={10}
                disabled={editSaving}
              />
            </div>
            <div className="sec-modal-footer">
              <button className="sec-btn-cancel" onClick={() => setEditTarget(null)} disabled={editSaving}>
                Cancel
              </button>
              <button className="sec-btn-save" onClick={handleSaveEdit} disabled={editSaving}>
                {editSaving ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
