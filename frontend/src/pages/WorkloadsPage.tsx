import { FormEvent, useEffect, useRef, useState } from "react";

function fmtAge(s: number): string {
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s / 60)}m ago`;
}
import {
  cordonNode,
  createWorkload,
  deleteWorkload,
  drainNode,
  getCapacity,
  listWorkloads,
  restartWorkload,
  scaleWorkload,
  uncordonNode,
  updateWorkloadImage,
  updateWorkloadProbes,
} from "../api/workloads";
import EnvModal from "../components/EnvModal";
import EventsModal from "../components/EventsModal";
import LogsModal from "../components/LogsModal";
import MetricsModal from "../components/MetricsModal";
import PodsModal from "../components/PodsModal";
import ProbesModal from "../components/ProbesModal";
import ResourcesModal from "../components/ResourcesModal";
import RollbackModal from "../components/RollbackModal";
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

interface ImageCellProps {
  workload: Workload;
  onUpdate: (name: string, image: string) => Promise<void>;
  updating: boolean;
}

function ImageCell({ workload, onUpdate, updating }: ImageCellProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(workload.image);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function startEdit() {
    setValue(workload.image);
    setEditing(true);
  }

  function cancel() {
    setEditing(false);
    setValue(workload.image);
  }

  async function submit() {
    const trimmed = value.trim();
    if (!trimmed || trimmed === workload.image) { cancel(); return; }
    setEditing(false);
    await onUpdate(workload.name, trimmed);
  }

  if (editing) {
    return (
      <div className="wl-img-edit">
        <input
          ref={inputRef}
          className="wl-img-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
            if (e.key === "Escape") cancel();
          }}
          onBlur={submit}
          disabled={updating}
        />
      </div>
    );
  }

  return (
    <div className="wl-img-view" onClick={startEdit} title="Click to update image">
      <span className="wl-mono">{workload.image}</span>
      <span className="wl-img-edit-icon">✎</span>
    </div>
  );
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
  const [draining, setDraining] = useState<string | null>(null);
  const [updatingImage, setUpdatingImage] = useState<string | null>(null);
  const [logsTarget, setLogsTarget] = useState<string | null>(null);
  const [eventsTarget, setEventsTarget] = useState<string | null>(null);
  const [podsTarget, setPodsTarget] = useState<string | null>(null);
  const [envTarget, setEnvTarget] = useState<Workload | null>(null);
  const [resourcesTarget, setResourcesTarget] = useState<Workload | null>(null);
  const [probesTarget, setProbesTarget] = useState<Workload | null>(null);
  const [restarting, setRestarting] = useState<string | null>(null);
  const [metricsTarget, setMetricsTarget] = useState<string | null>(null);
  const [rollbackTarget, setRollbackTarget] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "pending" | "failed">("all");
  const [sortField, setSortField] = useState<"name" | "status" | "replicas" | "created_at">("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [lastRefresh, setLastRefresh] = useState<number>(Date.now());
  const [refreshAge, setRefreshAge] = useState<number>(0);

  const [form, setForm] = useState({
    name: "",
    image: "",
    replicas: "1",
    namespace: DEFAULT_NS,
    target_node: "",
    container_port: "",
    cpu_limit: "",
    memory_limit: "",
    liveness_path: "",
    readiness_path: "",
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
      setLastRefresh(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workloads");
    } finally {
      setLoading(false);
      setCapLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const modalOpen = !!(logsTarget || eventsTarget || podsTarget || envTarget || resourcesTarget || probesTarget || metricsTarget || rollbackTarget);
  const refreshRef = useRef(refresh);
  useEffect(() => { refreshRef.current = refresh; });

  useEffect(() => {
    if (modalOpen) return;
    const id = setInterval(() => { refreshRef.current(); }, 15_000);
    return () => clearInterval(id);
  }, [modalOpen]);

  useEffect(() => {
    const id = setInterval(() => {
      setRefreshAge(Math.floor((Date.now() - lastRefresh) / 1000));
    }, 1_000);
    return () => clearInterval(id);
  }, [lastRefresh]);

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
        cpu_limit: form.cpu_limit || undefined,
        memory_limit: form.memory_limit || undefined,
        liveness_path: form.liveness_path || null,
        readiness_path: form.readiness_path || null,
      });
      setForm({ name: "", image: "", replicas: "1", namespace: DEFAULT_NS, target_node: "", container_port: "", cpu_limit: "", memory_limit: "", liveness_path: "", readiness_path: "" });
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

  async function handleImageUpdate(name: string, image: string) {
    setUpdatingImage(name);
    try {
      await updateWorkloadImage(name, image);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update image");
    } finally {
      setUpdatingImage(null);
    }
  }

  async function handleRestart(name: string) {
    setRestarting(name);
    try {
      await restartWorkload(name);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to restart workload");
    } finally {
      setRestarting(null);
    }
  }

  async function handleDrain(node: NodeCapacity) {
    setDraining(node.node_name);
    try {
      await drainNode(node.node_name);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Drain failed");
    } finally {
      setDraining(null);
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

  const filtered = workloads.filter((w) => {
    const matchName = w.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || w.status === statusFilter;
    return matchName && matchStatus;
  });
  const isFiltered = search !== "" || statusFilter !== "all";

  function toggleSort(field: typeof sortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortField === "name") cmp = a.name.localeCompare(b.name);
    else if (sortField === "status") cmp = a.status.localeCompare(b.status);
    else if (sortField === "replicas") cmp = a.replicas - b.replicas;
    else cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return sortDir === "asc" ? cmp : -cmp;
  });

  function sortIcon(field: typeof sortField) {
    if (sortField !== field) return <span className="wl-sort-icon wl-sort-idle">↕</span>;
    return <span className="wl-sort-icon wl-sort-active">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

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
          <div className="wl-field">
            <label className="wl-label">CPU limit (optional)</label>
            <input
              className="wl-input"
              placeholder="500m"
              value={form.cpu_limit}
              onChange={(e) => setForm((f) => ({ ...f, cpu_limit: e.target.value }))}
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Memory limit (optional)</label>
            <input
              className="wl-input"
              placeholder="256Mi"
              value={form.memory_limit}
              onChange={(e) => setForm((f) => ({ ...f, memory_limit: e.target.value }))}
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Liveness path (optional)</label>
            <input
              className="wl-input"
              placeholder="/health"
              value={form.liveness_path}
              onChange={(e) => setForm((f) => ({ ...f, liveness_path: e.target.value }))}
              disabled={creating}
            />
          </div>
          <div className="wl-field">
            <label className="wl-label">Readiness path (optional)</label>
            <input
              className="wl-input"
              placeholder="/ready"
              value={form.readiness_path}
              onChange={(e) => setForm((f) => ({ ...f, readiness_path: e.target.value }))}
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
        <div className="wl-live-wrap">
          <span className={`wl-live-dot${modalOpen ? " wl-live-paused" : ""}`} />
          <span className={`wl-live-label${modalOpen ? " wl-live-paused" : ""}`}>
            {modalOpen ? "Paused" : "Live"}
          </span>
          <span className="wl-live-age">
            · {isFiltered ? `${filtered.length} of ${workloads.length}` : `${workloads.length} total`} · {fmtAge(refreshAge)}
          </span>
        </div>
      </div>

      <div className="wl-filter-bar">
        <input
          className="wl-filter-input"
          placeholder="Search by name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="wl-filter-pills">
          {(["all", "running", "pending", "failed"] as const).map((s) => (
            <button
              key={s}
              className={`wl-pill${statusFilter === s ? " wl-pill-active wl-pill-" + s : ""}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading workloads…</span></div>
      ) : workloads.length === 0 ? (
        <div className="wl-empty">No workloads deployed yet.</div>
      ) : filtered.length === 0 ? (
        <div className="wl-empty">No workloads match your filter.</div>
      ) : (
        <div className="wl-table-wrap">
          <table className="wl-table">
            <thead>
              <tr>
                <th className="wl-th-sort" onClick={() => toggleSort("name")}>Name {sortIcon("name")}</th>
                <th>Image</th>
                <th>Namespace</th>
                <th className="wl-th-sort" onClick={() => toggleSort("replicas")}>Replicas {sortIcon("replicas")}</th>
                <th>Node</th>
                <th>Ingress</th>
                <th className="wl-th-sort" onClick={() => toggleSort("status")}>Status {sortIcon("status")}</th>
                <th className="wl-th-sort" onClick={() => toggleSort("created_at")}>Created {sortIcon("created_at")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((w) => (
                <tr key={w.id} className={updatingImage === w.name ? "wl-row-updating" : ""}>
                  <td className="wl-name">{w.name}</td>
                  <td>
                    <ImageCell
                      workload={w}
                      onUpdate={handleImageUpdate}
                      updating={updatingImage === w.name}
                    />
                  </td>
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
                        className="wl-btn-pods"
                        onClick={() => setPodsTarget(w.name)}
                      >
                        Pods
                      </button>
                      <button
                        className="wl-btn-metrics"
                        onClick={() => setMetricsTarget(w.name)}
                      >
                        Metrics
                      </button>
                      <button
                        className="wl-btn-env"
                        onClick={() => setEnvTarget(w)}
                      >
                        Env
                      </button>
                      <button
                        className="wl-btn-resources"
                        onClick={() => setResourcesTarget(w)}
                      >
                        Resources
                      </button>
                      <button
                        className="wl-btn-probes"
                        onClick={() => setProbesTarget(w)}
                      >
                        Probes
                      </button>
                      <button
                        className="wl-btn-events"
                        onClick={() => setEventsTarget(w.name)}
                      >
                        Events
                      </button>
                      <button
                        className="wl-btn-logs"
                        onClick={() => setLogsTarget(w.name)}
                      >
                        Logs
                      </button>
                      <button
                        className="wl-btn-restart"
                        onClick={() => handleRestart(w.name)}
                        disabled={restarting === w.name}
                      >
                        {restarting === w.name ? "…" : "Restart"}
                      </button>
                      <button
                        className="wl-btn-history"
                        onClick={() => setRollbackTarget(w.name)}
                      >
                        History
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
                <div className="wl-cap-actions">
                  <button
                    className={`wl-cordon-btn${!c.schedulable ? " wl-cordon-active" : ""}`}
                    onClick={() => handleCordon(c)}
                    disabled={cordoning === c.node_name || draining === c.node_name}
                  >
                    {cordoning === c.node_name ? "…" : c.schedulable ? "Cordon" : "Uncordon"}
                  </button>
                  <button
                    className="wl-drain-btn"
                    onClick={() => handleDrain(c)}
                    disabled={draining === c.node_name || cordoning === c.node_name || !c.ready}
                    title="Cordon and evict all non-DaemonSet pods"
                  >
                    {draining === c.node_name ? "Draining…" : "Drain"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {envTarget && (
        <EnvModal
          workloadName={envTarget.name}
          initialEnv={envTarget.env_vars}
          onClose={() => setEnvTarget(null)}
          onSaved={refresh}
        />
      )}
      {resourcesTarget && (
        <ResourcesModal
          workload={resourcesTarget}
          onClose={() => setResourcesTarget(null)}
          onSaved={refresh}
        />
      )}
      {probesTarget && (
        <ProbesModal
          workload={probesTarget}
          onClose={() => setProbesTarget(null)}
          onSaved={refresh}
        />
      )}
      {podsTarget && (
        <PodsModal workloadName={podsTarget} onClose={() => setPodsTarget(null)} />
      )}
      {metricsTarget && (
        <MetricsModal name={metricsTarget} onClose={() => setMetricsTarget(null)} />
      )}
      {eventsTarget && (
        <EventsModal workloadName={eventsTarget} onClose={() => setEventsTarget(null)} />
      )}
      {logsTarget && (
        <LogsModal workloadName={logsTarget} onClose={() => setLogsTarget(null)} />
      )}
      {rollbackTarget && (
        <RollbackModal
          name={rollbackTarget}
          onClose={() => setRollbackTarget(null)}
          onRolledBack={refresh}
        />
      )}
    </div>
  );
}
