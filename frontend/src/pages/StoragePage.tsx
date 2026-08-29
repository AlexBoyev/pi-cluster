import { useEffect, useState } from "react";
import { deletePVC, listPVCs, listPVs } from "../api/storage";
import { useAuth } from "../context/AuthContext";
import type { PVCInfo, PVInfo } from "../types/storage";
import "./StoragePage.css";

type Tab = "pvcs" | "pvs";

function statusCls(s: string): string {
  if (s === "Bound")     return "st-bound";
  if (s === "Pending")   return "st-pending";
  if (s === "Available") return "st-avail";
  if (s === "Released")  return "st-released";
  return "st-lost";
}

export default function StoragePage() {
  const { role } = useAuth();
  const isAdmin = role === "admin";

  const [tab, setTab] = useState<Tab>("pvcs");
  const [pvcs, setPvcs] = useState<PVCInfo[]>([]);
  const [pvs, setPvs]   = useState<PVInfo[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [nsFilter, setNsFilter] = useState("");
  const [confirmDel, setConfirmDel] = useState<string | null>(null);
  const [deleting, setDeleting]     = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [p, v] = await Promise.all([listPVCs(), listPVs()]);
      setPvcs(p);
      setPvs(v);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load storage");
    } finally {
      setLoading(false);
    }
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

  const namespaces = Array.from(new Set(pvcs.map((p) => p.namespace))).sort();
  const filteredPvcs = nsFilter ? pvcs.filter((p) => p.namespace === nsFilter) : pvcs;

  const boundCount  = pvcs.filter((p) => p.status === "Bound").length;
  const pendingCount = pvcs.filter((p) => p.status === "Pending").length;

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
            PVCs
          </button>
          <button className={`st-tab${tab === "pvs" ? " active" : ""}`} onClick={() => setTab("pvs")}>
            PVs
          </button>
        </div>
        {tab === "pvcs" && namespaces.length > 1 && (
          <div className="st-ns-wrap">
            <label className="st-ns-lbl">Namespace:</label>
            <select className="st-ns-select" value={nsFilter} onChange={(e) => setNsFilter(e.target.value)}>
              <option value="">All</option>
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading storage…</span></div>
      ) : tab === "pvcs" ? (
        filteredPvcs.length === 0 ? (
          <div className="st-empty">No PVCs found.</div>
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
                      <td>
                        <span className={`st-badge ${statusCls(pvc.status)}`}>{pvc.status}</span>
                      </td>
                      <td className="st-mono">{pvc.capacity ?? "—"}</td>
                      <td className="st-mono">{pvc.storage_class ?? "—"}</td>
                      <td className="st-modes">
                        {pvc.access_modes.map((m) => (
                          <span key={m} className="st-mode-tag">{m}</span>
                        ))}
                      </td>
                      <td className="st-mono st-dim">{pvc.volume_name ?? "—"}</td>
                      {isAdmin && (
                        <td>
                          {confirmDel === key ? (
                            <div className="st-confirm">
                              <button
                                className="st-btn-del-confirm"
                                onClick={() => handleDelete(pvc)}
                                disabled={deleting === key}
                              >
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
      ) : (
        pvs.length === 0 ? (
          <div className="st-empty">No PVs found.</div>
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
                    <td>
                      <span className={`st-badge ${statusCls(pv.status)}`}>{pv.status}</span>
                    </td>
                    <td className="st-mono">{pv.capacity ?? "—"}</td>
                    <td className="st-mono">{pv.storage_class ?? "—"}</td>
                    <td className="st-modes">
                      {pv.access_modes.map((m) => (
                        <span key={m} className="st-mode-tag">{m}</span>
                      ))}
                    </td>
                    <td className="st-mono">{pv.reclaim_policy ?? "—"}</td>
                    <td className="st-mono st-dim">
                      {pv.claim_name
                        ? `${pv.claim_namespace}/${pv.claim_name}`
                        : "—"}
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
