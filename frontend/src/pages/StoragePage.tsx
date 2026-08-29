import React, { useEffect, useState } from "react";
import { createPVC, deletePVC, listPVCs, listPVs, listStorageClasses } from "../api/storage";
import { useAuth } from "../context/AuthContext";
import type { PVCCreate, PVCInfo, PVInfo, StorageClassInfo } from "../types/storage";
import "./StoragePage.css";

type Tab = "pvcs" | "pvs" | "classes";

function statusCls(s: string): string {
  if (s === "Bound")     return "st-bound";
  if (s === "Pending")   return "st-pending";
  if (s === "Available") return "st-avail";
  if (s === "Released")  return "st-released";
  return "st-lost";
}

const BLANK_FORM: PVCCreate = { name: "", namespace: "default", storage_class: "", access_modes: ["ReadWriteOnce"], size: "1Gi" };

export default function StoragePage() {
  const { role } = useAuth();
  const isAdmin = role === "admin";

  const [tab, setTab] = useState<Tab>("pvcs");
  const [pvcs, setPvcs]       = useState<PVCInfo[]>([]);
  const [pvs, setPvs]         = useState<PVInfo[]>([]);
  const [classes, setClasses] = useState<StorageClassInfo[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [nsFilter, setNsFilter]   = useState("");
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [deleting, setDeleting]     = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm]   = useState<PVCCreate>(BLANK_FORM);
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    const [pvcRes, pvRes, classRes] = await Promise.allSettled([listPVCs(), listPVs(), listStorageClasses()]);
    if (pvcRes.status === "fulfilled") setPvcs(pvcRes.value);
    if (pvRes.status === "fulfilled") setPvs(pvRes.value);
    if (classRes.status === "fulfilled") setClasses(classRes.value);
    const errs = [pvcRes, pvRes, classRes]
      .filter((r): r is PromiseRejectedResult => r.status === "rejected")
      .map((r) => (r.reason instanceof Error ? r.reason.message : "Request failed"));
    if (errs.length) setError(errs[0]);
    setLoading(false);
  }

  useEffect(() => { refresh(); }, []);

  async function handleDelete(pvc: PVCInfo) {
    const key = `${pvc.namespace}/${pvc.name}`;
    setDeleting(key);
    try {
      await deletePVC(pvc.namespace, pvc.name);
      setConfirmDel(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete PVC");
    } finally {
      setDeleting(null);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setCreateErr(null);
    try {
      await createPVC(form);
      setShowCreate(false);
      setForm(BLANK_FORM);
      await refresh();
    } catch (err) {
      setCreateErr(err instanceof Error ? err.message : "Failed to create PVC");
    } finally {
      setCreating(false);
    }
  }

  const namespaces = Array.from(new Set(pvcs.map((p) => p.namespace))).sort();
  const filteredPvcs = nsFilter ? pvcs.filter((p) => p.namespace === nsFilter) : pvcs;
  const boundCount   = pvcs.filter((p) => p.status === "Bound").length;
  const pendingCount = pvcs.filter((p) => p.status === "Pending").length;

  const defaultClass = classes.find((c) => c.is_default)?.name ?? classes[0]?.name ?? "";

  return (
    <div className="st-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">PVCs</div>
          <div className="summ-value sv-blue">{pvcs.length}</div>
          <div className="summ-sub">persistent volume claims</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Bound</div>
          <div className="summ-value sv-green">{boundCount}</div>
          <div className="summ-sub">in use</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Pending</div>
          <div className="summ-value sv-amber">{pendingCount}</div>
          <div className="summ-sub">awaiting binding</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">PVs</div>
          <div className="summ-value sv-blue">{pvs.length}</div>
          <div className="summ-sub">cluster volumes</div>
        </div>
      </div>

      <div className="st-toolbar">
        <div className="st-tabs">
          <button className={`st-tab${tab === "pvcs" ? " active" : ""}`} onClick={() => setTab("pvcs")}>
            Persistent Volume Claims
          </button>
          <button className={`st-tab${tab === "pvs" ? " active" : ""}`} onClick={() => setTab("pvs")}>
            Persistent Volumes
          </button>
          <button className={`st-tab${tab === "classes" ? " active" : ""}`} onClick={() => setTab("classes")}>
            Storage Classes
          </button>
        </div>
        <div className="st-toolbar-right">
          {tab === "pvcs" && namespaces.length > 1 && (
            <div className="st-ns-wrap">
              <label className="st-ns-lbl">Namespace:</label>
              <select className="st-ns-select" value={nsFilter} onChange={(e) => setNsFilter(e.target.value)}>
                <option value="">All</option>
                {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          )}
          {tab === "pvcs" && isAdmin && (
            <button className="st-btn-create" onClick={() => { setShowCreate(true); setForm({ ...BLANK_FORM, storage_class: defaultClass }); }}>
              + Create PVC
            </button>
          )}
        </div>
      </div>

      {showCreate && (
        <div className="st-create-card">
          <div className="st-create-title">Create Persistent Volume Claim</div>
          {createErr && <div className="err-banner" style={{ marginBottom: "0.75rem" }}>{createErr}</div>}
          <form className="st-create-form" onSubmit={handleCreate}>
            <div className="st-form-row">
              <label className="st-form-lbl">Name</label>
              <input
                className="st-form-input"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="my-pvc"
                required
              />
            </div>
            <div className="st-form-row">
              <label className="st-form-lbl">Namespace</label>
              <input
                className="st-form-input"
                value={form.namespace}
                onChange={(e) => setForm((f) => ({ ...f, namespace: e.target.value }))}
                placeholder="default"
                required
              />
            </div>
            <div className="st-form-row">
              <label className="st-form-lbl">Storage Class</label>
              <select
                className="st-form-input"
                value={form.storage_class}
                onChange={(e) => setForm((f) => ({ ...f, storage_class: e.target.value }))}
                required
              >
                {classes.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}{c.is_default ? " (default)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div className="st-form-row">
              <label className="st-form-lbl">Access Mode</label>
              <select
                className="st-form-input"
                value={form.access_modes[0]}
                onChange={(e) => setForm((f) => ({ ...f, access_modes: [e.target.value] }))}
              >
                <option value="ReadWriteOnce">ReadWriteOnce</option>
                <option value="ReadOnlyMany">ReadOnlyMany</option>
                <option value="ReadWriteMany">ReadWriteMany</option>
              </select>
            </div>
            <div className="st-form-row">
              <label className="st-form-lbl">Size</label>
              <input
                className="st-form-input"
                value={form.size}
                onChange={(e) => setForm((f) => ({ ...f, size: e.target.value }))}
                placeholder="1Gi"
                required
              />
            </div>
            <div className="st-form-actions">
              <button type="submit" className="st-btn-submit" disabled={creating}>
                {creating ? "Creating…" : "Create"}
              </button>
              <button type="button" className="st-btn-cancel" onClick={() => { setShowCreate(false); setCreateErr(null); }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading storage…</span></div>
      ) : tab === "pvcs" ? (
        filteredPvcs.length === 0 ? (
          <div className="st-empty">
            <div>No Persistent Volume Claims found.</div>
            {isAdmin && !showCreate && (
              <button className="st-btn-create" style={{ marginTop: "0.75rem" }} onClick={() => { setShowCreate(true); setForm({ ...BLANK_FORM, storage_class: defaultClass }); }}>
                + Create your first PVC
              </button>
            )}
          </div>
        ) : (
          <div className="st-table-wrap">
            <table className="st-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Namespace</th>
                  <th>Status</th>
                  <th>Capacity</th>
                  <th>Storage Class</th>
                  <th>Access Modes</th>
                  <th>Volume</th>
                  {isAdmin && <th></th>}
                </tr>
              </thead>
              <tbody>
                {filteredPvcs.map((pvc) => {
                  const key = `${pvc.namespace}/${pvc.name}`;
                  return (
                    <tr key={key}>
                      <td className="st-name">{pvc.name}</td>
                      <td className="st-mono">{pvc.namespace}</td>
                      <td><span className={`st-badge ${statusCls(pvc.status)}`}>{pvc.status}</span></td>
                      <td className="st-mono">{pvc.capacity ?? "—"}</td>
                      <td className="st-mono">{pvc.storage_class ?? "—"}</td>
                      <td className="st-modes">
                        {pvc.access_modes.map((m) => <span key={m} className="st-mode-tag">{m}</span>)}
                      </td>
                      <td className="st-mono st-dim">{pvc.volume_name ?? "—"}</td>
                      {isAdmin && (
                        <td>
                          {confirmDel === key ? (
                            <div className="st-confirm">
                              <button className="st-btn-del-confirm" onClick={() => handleDelete(pvc)} disabled={deleting === key}>
                                {deleting === key ? "…" : "Delete"}
                              </button>
                              <button className="st-btn-cancel" onClick={() => setConfirmDel(null)}>Cancel</button>
                            </div>
                          ) : (
                            <button className="st-btn-del" onClick={() => setConfirmDel(key)}>Delete</button>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      ) : tab === "pvs" ? (
        pvs.length === 0 ? (
          <div className="st-empty">No Persistent Volumes found.</div>
        ) : (
          <div className="st-table-wrap">
            <table className="st-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Capacity</th>
                  <th>Storage Class</th>
                  <th>Access Modes</th>
                  <th>Reclaim Policy</th>
                  <th>Bound Claim</th>
                </tr>
              </thead>
              <tbody>
                {pvs.map((pv) => (
                  <tr key={pv.name}>
                    <td className="st-name">{pv.name}</td>
                    <td><span className={`st-badge ${statusCls(pv.status)}`}>{pv.status}</span></td>
                    <td className="st-mono">{pv.capacity ?? "—"}</td>
                    <td className="st-mono">{pv.storage_class ?? "—"}</td>
                    <td className="st-modes">
                      {pv.access_modes.map((m) => <span key={m} className="st-mode-tag">{m}</span>)}
                    </td>
                    <td className="st-mono">{pv.reclaim_policy ?? "—"}</td>
                    <td className="st-mono st-dim">
                      {pv.claim_name ? `${pv.claim_namespace}/${pv.claim_name}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        classes.length === 0 ? (
          <div className="st-empty">No Storage Classes found.</div>
        ) : (
          <div className="st-table-wrap">
            <table className="st-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Provisioner</th>
                  <th>Reclaim Policy</th>
                  <th>Binding Mode</th>
                  <th>Default</th>
                </tr>
              </thead>
              <tbody>
                {classes.map((sc) => (
                  <tr key={sc.name}>
                    <td className="st-name">{sc.name}</td>
                    <td className="st-mono">{sc.provisioner}</td>
                    <td className="st-mono">{sc.reclaim_policy}</td>
                    <td className="st-mono">{sc.binding_mode}</td>
                    <td>
                      {sc.is_default && <span className="st-badge st-avail">Default</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
