import { useEffect, useState } from "react";
import { getClusterCapacity } from "../api/cluster";
import type { ClusterCapacity, NodeCapacityDetail } from "../types/cluster";
import "./CapacityPage.css";

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtBytes(b: number): string {
  if (b >= 1_073_741_824) return `${(b / 1_073_741_824).toFixed(1)} GB`;
  if (b >= 1_048_576) return `${(b / 1_048_576).toFixed(0)} MB`;
  return `${b} B`;
}
function pct(used: number, total: number): number {
  if (total === 0) return 0;
  return Math.min(100, (used / total) * 100);
}
function sevCls(p: number): string {
  return p >= 85 ? "crit" : p >= 65 ? "warn" : "ok";
}

// ── Stacked bar (used | requested | free) ────────────────────────────────────

function StackedBar({
  used, requested, total, labelUsed, labelReq,
}: {
  used: number; requested: number; total: number;
  labelUsed: string; labelReq: string;
}) {
  const usedPct = pct(used, total);
  const reqPct  = Math.max(0, pct(requested, total) - usedPct);
  const freePct = Math.max(0, 100 - usedPct - reqPct);
  const sev = sevCls(usedPct);

  return (
    <div className="cap-stack">
      <div className="cap-bar">
        <div className={`cap-seg cap-used cap-used-${sev}`} style={{ width: `${usedPct}%` }} title={`Used: ${labelUsed}`} />
        <div className="cap-seg cap-req" style={{ width: `${reqPct}%` }} title={`Requested: ${labelReq}`} />
        <div className="cap-seg cap-free" style={{ width: `${freePct}%` }} />
      </div>
      <div className="cap-bar-legend">
        <span className={`cap-leg-used cap-leg-${sev}`}>Used {usedPct.toFixed(1)}%</span>
        <span className="cap-leg-req">Requested {pct(requested, total).toFixed(1)}%</span>
        <span className="cap-leg-free">Free {freePct.toFixed(1)}%</span>
      </div>
    </div>
  );
}

// ── Per-node card ─────────────────────────────────────────────────────────────

function NodeCapCard({ n }: { n: NodeCapacityDetail }) {
  const cpuUsedPct = pct(n.cpu_used_cores, n.cpu_allocatable_cores);
  const memUsedPct = pct(n.memory_used_bytes, n.memory_allocatable_bytes);

  return (
    <div className={`cap-node-card${!n.ready ? " cap-node-notready" : ""}`}>
      <div className="cap-node-head">
        <span className="cap-node-name">{n.node_name}</span>
        <div className="cap-node-badges">
          {!n.ready && <span className="cap-badge cap-badge-notready">Not Ready</span>}
          {!n.schedulable && <span className="cap-badge cap-badge-cordoned">Cordoned</span>}
          {n.ready && n.schedulable && <span className="cap-badge cap-badge-ok">Ready</span>}
        </div>
      </div>

      <div className="cap-node-metric">
        <div className="cap-node-label">CPU</div>
        <div className="cap-node-vals">
          <span className={`cap-node-used cap-col-${sevCls(cpuUsedPct)}`}>{n.cpu_used_cores.toFixed(2)} cores</span>
          <span className="cap-node-dim">/ {n.cpu_allocatable_cores.toFixed(1)} alloc · {n.cpu_requested_cores.toFixed(2)} req</span>
        </div>
        <div className="cap-mini-bar">
          <div className={`cap-mini-fill cap-mini-${sevCls(cpuUsedPct)}`} style={{ width: `${cpuUsedPct}%` }} />
          <div className="cap-mini-req" style={{ width: `${Math.max(0, pct(n.cpu_requested_cores, n.cpu_allocatable_cores) - cpuUsedPct)}%` }} />
        </div>
      </div>

      <div className="cap-node-metric">
        <div className="cap-node-label">Memory</div>
        <div className="cap-node-vals">
          <span className={`cap-node-used cap-col-${sevCls(memUsedPct)}`}>{fmtBytes(n.memory_used_bytes)}</span>
          <span className="cap-node-dim">/ {fmtBytes(n.memory_allocatable_bytes)} alloc · {fmtBytes(n.memory_requested_bytes)} req</span>
        </div>
        <div className="cap-mini-bar">
          <div className={`cap-mini-fill cap-mini-${sevCls(memUsedPct)}`} style={{ width: `${memUsedPct}%` }} />
          <div className="cap-mini-req" style={{ width: `${Math.max(0, pct(n.memory_requested_bytes, n.memory_allocatable_bytes) - memUsedPct)}%` }} />
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CapacityPage() {
  const [data, setData]       = useState<ClusterCapacity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getClusterCapacity()
      .then((d) => { setData(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); const id = setInterval(load, 30_000); return () => clearInterval(id); }, []);

  const cpuUsedPct = data ? pct(data.cpu_used_cores, data.cpu_allocatable_cores) : 0;
  const memUsedPct = data ? pct(data.memory_used_bytes, data.memory_allocatable_bytes) : 0;

  return (
    <div className="cap-page">
      {error && <div className="err-banner">API error: {error}</div>}

      {data && (
        <div className="summary-row">
          <div className="summ-card sc-blue">
            <div className="summ-label">CPU Cores</div>
            <div className="summ-value sv-blue">{data.cpu_allocatable_cores.toFixed(1)}</div>
            <div className="summ-sub">{data.nodes.length} nodes · {data.cpu_used_cores.toFixed(2)} used</div>
          </div>
          <div className={`summ-card sc-${sevCls(cpuUsedPct) === "ok" ? "green" : sevCls(cpuUsedPct) === "warn" ? "amber" : "red"}`}>
            <div className="summ-label">CPU Used</div>
            <div className={`summ-value sv-${sevCls(cpuUsedPct) === "ok" ? "green" : sevCls(cpuUsedPct) === "warn" ? "amber" : "red"}`}>{cpuUsedPct.toFixed(1)}%</div>
            <div className="summ-sub">{data.cpu_requested_cores.toFixed(2)} cores requested</div>
          </div>
          <div className="summ-card sc-blue">
            <div className="summ-label">Memory</div>
            <div className="summ-value sv-blue">{fmtBytes(data.memory_allocatable_bytes)}</div>
            <div className="summ-sub">{fmtBytes(data.memory_used_bytes)} used</div>
          </div>
          <div className={`summ-card sc-${sevCls(memUsedPct) === "ok" ? "green" : sevCls(memUsedPct) === "warn" ? "amber" : "red"}`}>
            <div className="summ-label">Memory Used</div>
            <div className={`summ-value sv-${sevCls(memUsedPct) === "ok" ? "green" : sevCls(memUsedPct) === "warn" ? "amber" : "red"}`}>{memUsedPct.toFixed(1)}%</div>
            <div className="summ-sub">{fmtBytes(data.memory_requested_bytes)} requested</div>
          </div>
        </div>
      )}

      <div className="section-header">
        <span className="section-title">Cluster utilization</span>
        <span className="section-meta">used · requested · free · auto-refresh 30s</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading capacity…</span></div>
      ) : data ? (
        <>
          <div className="cap-cluster-bars">
            <div className="cap-bar-row">
              <span className="cap-bar-label">CPU</span>
              <div className="cap-bar-wrap">
                <StackedBar
                  used={data.cpu_used_cores}
                  requested={data.cpu_requested_cores}
                  total={data.cpu_allocatable_cores}
                  labelUsed={`${data.cpu_used_cores.toFixed(2)} cores`}
                  labelReq={`${data.cpu_requested_cores.toFixed(2)} cores`}
                />
              </div>
              <span className="cap-bar-total">{data.cpu_allocatable_cores.toFixed(1)} cores</span>
            </div>
            <div className="cap-bar-row">
              <span className="cap-bar-label">Memory</span>
              <div className="cap-bar-wrap">
                <StackedBar
                  used={data.memory_used_bytes}
                  requested={data.memory_requested_bytes}
                  total={data.memory_allocatable_bytes}
                  labelUsed={fmtBytes(data.memory_used_bytes)}
                  labelReq={fmtBytes(data.memory_requested_bytes)}
                />
              </div>
              <span className="cap-bar-total">{fmtBytes(data.memory_allocatable_bytes)}</span>
            </div>
          </div>

          <div className="section-header" style={{ marginTop: "1.5rem" }}>
            <span className="section-title">Per-node breakdown</span>
          </div>

          <div className="cap-node-grid">
            {data.nodes.map((n) => <NodeCapCard key={n.node_name} n={n} />)}
          </div>
        </>
      ) : null}
    </div>
  );
}
