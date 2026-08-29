import { FormEvent, useEffect, useState } from "react";
import { createNamespace, deleteNamespace, listNamespaces } from "../api/namespaces";
import type { NamespaceInfo } from "../types/namespace";
import "./NamespacesPage.css";

const SYSTEM_NS = new Set(["kube-system", "kube-public", "kube-node-lease"]);

function fmtAge(iso: string | null): string {
  if (!iso) return "—";
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function NsBadge({ status }: { status: string }) {
  return (
    <span className={`ns-badge ns-badge-${status.toLowerCase()}`}>{status}</span>
  );
}

export default function NamespacesPage() {
  const [namespaces, setNs]       = useState<NamespaceInfo[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [creating, setCreating]   = useState(false);
  const [newName, setNewName]     = useState("");
  const [formErr, setFormErr]     = useState<string | null>(null);
  const [deleting, setDeleting]   = useState<string | null>(null);
  const [confirmDel, setConfirm]  = useState<string | null>(null);

  const load = () =>
    listNamespaces()
      .then((d) => { setNs(d.sort((a, b) => a.name.localeCompare(b.name))); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setFormErr(null);
    try {
      await createNamespace(newName.trim());
      setNewName("");
      await load();
    } catch (err: unknown) {
      setFormErr(err instanceof Error ? err.message : "Failed to create namespace");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (name: string) => {
    setDeleting(name);
    try {
      await deleteNamespace(name);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete namespace");
    } finally {
      setDeleting(null);
      setConfirm(null);
    }
  };

  const system    = namespaces.filter((n) => SYSTEM_NS.has(n.name));
  const userNs    = namespaces.filter((n) => !SYSTEM_NS.has(n.name));
  const active    = namespaces.filter((n) => n.status === "Active").length;

  return (
    <div className="ns-page">
      {error && <div className="err-banner">API error: {error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total</div>
          <div className="summ-value sv-blue">{namespaces.length}</div>
          <div className="summ-sub">namespaces</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Active</div>
          <div className="summ-value sv-green">{active}</div>
          <div className="summ-sub">running</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">User</div>
          <div className="summ-value sv-amber">{userNs.length}</div>
          <div className="summ-sub">non-system</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">System</div>
          <div className="summ-value sv-blue">{system.length}</div>
          <div className="summ-sub">protected</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Create namespace</span>
      </div>

      <form className="ns-create-form" onSubmit={handleCreate}>
        <input
          className={`ns-input${formErr ? " ns-input-err" : ""}`}
          placeholder="my-namespace"
          value={newName}
          onChange={(e) => { setNewName(e.target.value); setFormErr(null); }}
          disabled={creating}
        />
        <button className="ns-create-btn" type="submit" disabled={creating || !newName.trim()}>
          {creating ? "Creating…" : "Create"}
        </button>
        {formErr && <span className="ns-form-err">{formErr}</span>}
      </form>

      <div className="section-header" style={{ marginTop: "1.5rem" }}>
        <span className="section-title">Namespaces</span>
        <span className="section-meta">{namespaces.length} total</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading namespaces…</span></div>
      ) : (
        <div className="ns-table-wrap">
          <table className="ns-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Age</th>
                <th>Labels</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {namespaces.map((ns) => {
                const isSystem = SYSTEM_NS.has(ns.name) || ns.name === "default" || ns.name === "monitoring" || ns.name === "argocd";
                const labelCount = Object.keys(ns.labels).length;
                return (
                  <tr key={ns.name} className={isSystem ? "ns-row-system" : ""}>
                    <td className="ns-name">{ns.name}{isSystem && <span className="ns-system-tag">system</span>}</td>
                    <td><NsBadge status={ns.status} /></td>
                    <td className="ns-age">{fmtAge(ns.created_at)}</td>
                    <td className="ns-labels">
                      {labelCount > 0 ? (
                        <span className="ns-label-count">{labelCount} label{labelCount !== 1 ? "s" : ""}</span>
                      ) : <span className="ns-dim">—</span>}
                    </td>
                    <td className="ns-actions">
                      {!isSystem && (
                        confirmDel === ns.name ? (
                          <span className="ns-confirm">
                            Delete?{" "}
                            <button
                              className="ns-confirm-yes"
                              onClick={() => handleDelete(ns.name)}
                              disabled={deleting === ns.name}
                            >
                              {deleting === ns.name ? "…" : "Yes"}
                            </button>
                            {" "}
                            <button className="ns-confirm-no" onClick={() => setConfirm(null)}>No</button>
                          </span>
                        ) : (
                          <button
                            className="ns-del-btn"
                            onClick={() => setConfirm(ns.name)}
                            disabled={deleting !== null}
                          >
                            Delete
                          </button>
                        )
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
