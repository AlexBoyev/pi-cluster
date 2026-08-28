import { FormEvent, useEffect, useState } from "react";
import {
  cordonNode,
  createWorkload,
  deleteWorkload,
  getCapacity,
  listWorkloads,
  scaleWorkload,
  uncordonNode,
} from "../api/workloads";
import LogsModal from "../components/LogsModal";
import type { NodeCapacity, Workload } from "../types/workload";
import "./WorkloadsPage.css";

const DEFAULT_NS = "pi-apps";

function cpuPct(c: NodeCapacity): number {
  if (c.cpu_allocatable_m === 0) return 0;
  return Math.round((c.cpu_requested_m / c.cpu_allocatable_m) * 100);
}
function memPct(c: NodeCapacity): number {
  if (c.memory_allocatable_mi === 0) return 0;
  return Math.round((c.memory_requested_mi / c.memory_allocatable_mi) * 100);
}
function fmtMi(mi: number): string {
  return mi >= 1024 ? `${(mi / 1024).toFixed(1)} Gi` : `${mi} Mi`;
}
function sevCls(pct: number): string {
  return pct >= 90 ? "crit" : pct >= 70 ? "warn" : "ok";
}

function StatusBadge({ status }: { status: Workload["status"] }) {
  return <span className={`wl-badge wb-${status}`}>{status}</span>;
}

export default function WorkloadsPage() {
  const [workloads, setWorkloads] = useState<Workload[]>([]);
  const [capacity, setCapacity] = useState<NodeCapacity[]>([]);
  const [loading, setLoading] = useState(true);
  const [capLoading, setCapLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting]   = useState<string | null>(null);
  const [scaling, setScaling]     = useState<string | null>(null);
  const [cordoning, setCordoning] = useState<string | null>(null);
  const [logsTarget, setLogsTarget] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    image: "",
    replicas: "1",
    namespace: DEFAULT_NS,
    target_node: "",
    container_port: "",
  });

  const refresh = async () => {
    try {
      const [wl, cap] = await Promise.all([
        listWorkloads(),
        getCapacity().catch(() => [] as NodeCapacity[]),
      ]);
      setWorkloads(wl);
      setCapacity(cap);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workloads");
    } finally {
      setLoading(false);
      setCapLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createWorkload({
        name: form.name,
        image: form.image,
        replicas: parseInt(form.replicas, 10),
        namespace: form.namespace,
        target_node: form.target_node || null,
        container_port: form.container_port ? parseInt(form.container_port, 10) : null,
      });
      setForm({ name: "", image: "", replicas: "1", namespace: DEFAULT_NS, target_node: "", container_port: "" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create workload");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(name: string) {
    setDeleting(name);
    try {
      await deleteWorkload(name);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete workload");
    } finally {
      setDeleting(null);
    }
  }

  async function handleScale(name: string, replicas: number) {
    setScaling(name);
    try {
      await scaleWorkload(name, replicas);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to scale workload");
    } finally {
      setScaling(null);
    }
  }

  async function handleCordon(node: NodeCapacity) {
    setCordoning(node.node_name);
    try {
      if (node.schedulable) {
        await cordonNode(node.node_name);
      } else {
        await uncordonNode(node.node_name);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cordon failed");
    } finally {
      setCordoning(null);
    }
  }

  const running = workloads.filter((w) => w.status === "running").length;
  const failed = workloads.filter((w) => w.status === "failed").length;
  const nodeNames = capacity.map((c) => c.node_name);

  return (
    <div className="wl-page">
      {error && <div className="err-banner">{error}</div>}

      {/* Summary */}
      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total workloads</div>
          <div className="summ-value sv-blue">{workloads.length}</div>
          <div className="summ-sub">across {capacity.length} K8s nodes</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Running</div>
          <div className="summ-value sv-green">{running}</div>
          <div className="summ-sub">{workloads.length ? `${Math.round((running / workloads.length) * 100)}% healthy` : "—"}</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Failed</div>
          <div className={`summ-value${failed > 0 ? " sv-red" : " sv-dim"}`}>{failed}</div>
          <div className="summ-sub">{failed === 0 ? "All workloads healthy" : `${failed} workload(s) failed`}</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">K8s nodes</div>
          <div className="summ-value sv-amber">{capacity.filter((c) => c.ready).length}</div>
          <div className="summ-sub">{capacity.filter((c) => !c.schedulable).length} cordoned</div>
        </div>
      </div>

      {/* Create form */}
      <div className="section-header">
        <span className="section-title">Deploy workload</span>
      </div>
      <div className="wl-form-card">
        <form className="wl-form" onSubmit={handleCreate}>
          <div className="wl-field">
            <label className="wl-label">Name</label>
            <input
              className="wl-input"
              placeholder="my-app"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              pattern="^[a-z][a-z0-9-]{0,62}$"
              required
              disabled={creating}
            />
          </div>
          <div className="wl-field wl-field-wide">
            <label className="wl-label">Image</label>
            <input
              className="wl-input"
              placeholder="nginx:alpine"
              value={form.image}
              onChange={(e) => setForm((f) => ({ ...f, image: e.target.value }))}
              required
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Replicas</label>
            <input
              className="wl-input"
              type="number"
              min={1}
              max={10}
              value={form.replicas}
              onChange={(e) => setForm((f) => ({ ...f, replicas: e.target.value }))}
              required
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Namespace</label>
            <input
              className="wl-input"
              value={form.namespace}
              onChange={(e) => setForm((f) => ({ ...f, namespace: e.target.value }))}
              required
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Target node (optional)</label>
            <select
              className="wl-input"
              value={form.target_node}
              onChange={(e) => setForm((f) => ({ ...f, target_node: e.target.value }))}
              disabled={creating}
            >
              <option value="">Auto (capacity-aware)</option>
              {nodeNames.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
          <div className="wl-field">
            <label className="wl-label">Container port (optional)</label>
            <input
              className="wl-input"
              type="number"
              min={1}
              max={65535}
              placeholder="e.g. 80"
              value={form.container_port}
              onChange={(e) => setForm((f) => ({ ...f, container_port: e.target.value }))}
              disabled={creating}
            />
          </div>
          <div className="wl-field wl-field-submit">
            <button className="wl-btn-primary" type="submit" disabled={creating}>
              {creating ? "Deploying…" : "Deploy"}
            </button>
          </div>
        </form>
      </div>

      {/* Workloads table */}
      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Active workloads</span>
        <span className="section-meta">{workloads.length} total</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading workloads…</span></div>
      ) : workloads.length === 0 ? (
        <div className="wl-empty">No workloads deployed yet.</div>
      ) : (
        <div className="wl-table-wrap">
          <table className="wl-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Image</th>
                <th>Namespace</th>
                <th>Replicas</th>
                <th>Node</th>
                <th>Ingress</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {workloads.map((w) => (
                <tr key={w.id}>
                  <td className="wl-name">{w.name}</td>
                  <td className="wl-mono">{w.image}</td>
                  <td className="wl-mono">{w.namespace}</td>
                  <td>
                    <div className="wl-scale">
                      <button
                        className="wl-scale-btn"
                        onClick={() => handleScale(w.name, w.replicas - 1)}
                        disabled={scaling === w.name || w.replicas <= 1}
                      >−</button>
                      <span className="wl-scale-val">{w.ready_replicas}/{w.replicas}</span>
                      <button
                        className="wl-scale-btn"
                        onClick={() => handleScale(w.name, w.replicas + 1)}
                        disabled={scaling === w.name || w.replicas >= 10}
                      >+</button>
                    </div>
                  </td>
                  <td className="wl-mono">{w.target_node ?? "—"}</td>
                  <td className="wl-mono">
                    {w.ingress_host
                      ? <a href={`https://${w.ingress_host}`} target="_blank" rel="noreferrer">{w.ingress_host}</a>
                      : "—"}
                  </td>
                  <td><StatusBadge status={w.status} /></td>
                  <td className="wl-date">{new Date(w.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="wl-row-actions">
                      <button
                        className="wl-btn-logs"
                        onClick={() => setLogsTarget(w.name)}
                      >
                        Logs
                      </button>
                      <button
                        className="wl-btn-del"
                        onClick={() => handleDelete(w.name)}
                        disabled={deleting === w.name}
                      >
                        {deleting === w.name ? "…" : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Cluster capacity */}
      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Cluster capacity</span>
        <span className="section-meta">K8s node resource usage</span>
      </div>

      {capLoading ? (
        <div className="loading"><div className="spinner" /><span>Fetching capacity…</span></div>
      ) : capacity.length === 0 ? (
        <div className="wl-empty">K8s cluster unreachable.</div>
      ) : (
        <div className="wl-cap-grid">
          {capacity.map((c) => {
            const cpu = cpuPct(c);
            const mem = memPct(c);
            return (
              <div key={c.node_name} className={`wl-cap-card${!c.schedulable ? " wl-cordoned" : ""}`}>
                <div className="wl-cap-head">
                  <span className="wl-cap-name">{c.node_name}</span>
                  <div className="wl-cap-badges">
                    {!c.schedulable && <span className="wl-badge wb-cordoned">CORDONED</span>}
                    <span className={`wl-badge wb-${c.ready ? "running" : "failed"}`}>
                      {c.ready ? "Ready" : "NotReady"}
                    </span>
                  </div>
                </div>
                <div className="wl-cap-row">
                  <span className="wl-cap-lbl">CPU</span>
                  <div className="wl-bar"><div className={`wl-bar-fill wl-bar-${sevCls(cpu)}`} style={{ width: `${Math.min(cpu, 100)}%` }} /></div>
                  <span className="wl-cap-val">{c.cpu_requested_m}m / {c.cpu_allocatable_m}m</span>
                </div>
                <div className="wl-cap-row">
                  <span className="wl-cap-lbl">RAM</span>
                  <div className="wl-bar"><div className={`wl-bar-fill wl-bar-${sevCls(mem)}`} style={{ width: `${Math.min(mem, 100)}%` }} /></div>
                  <span className="wl-cap-val">{fmtMi(c.memory_requested_mi)} / {fmtMi(c.memory_allocatable_mi)}</span>
                </div>
                <button
                  className={`wl-cordon-btn${!c.schedulable ? " wl-cordon-active" : ""}`}
                  onClick={() => handleCordon(c)}
                  disabled={cordoning === c.node_name}
                >
                  {cordoning === c.node_name ? "…" : c.schedulable ? "Cordon" : "Uncordon"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>

    {logsTarget && (
      <LogsModal workloadName={logsTarget} onClose={() => setLogsTarget(null)} />
    )}
  );
}
