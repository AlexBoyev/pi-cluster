import { useEffect, useState } from "react";
import { getAllHealth } from "../api/health";
import { getNodeMetricsHistory } from "../api/nodes";
import type { MetricPoint, NodeHealth, NodeMetricsHistory } from "../types/node";
import "./NodesPage.css";

const CTRL_IP = "10.100.102.10";
type Period = "1h" | "6h" | "24h";

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtBytes(b: number): string {
  if (b >= 1_073_741_824) return `${(b / 1_073_741_824).toFixed(1)} GB`;
  return `${(b / 1_048_576).toFixed(0)} MB`;
}
function fmtUptime(s: number): string {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
function fmtBps(bps: number): string {
  if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} MB/s`;
  if (bps >= 1_000) return `${(bps / 1_000).toFixed(0)} KB/s`;
  return `${bps.toFixed(0)} B/s`;
}

// ── SVG Sparkline ─────────────────────────────────────────────────────────────

function Sparkline({
  points, color, height = 72, softMin, softMax,
}: {
  points: MetricPoint[];
  color: string;
  height?: number;
  softMin?: number;
  softMax?: number;
}) {
  if (points.length < 2) {
    return (
      <div className="sp-empty" style={{ height }}>
        No data
      </div>
    );
  }

  const W = 400;
  const H = height;
  const PAD = 4;
  const values = points.map((p) => p.v);
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const yMin = softMin !== undefined ? Math.min(softMin, dataMin) : dataMin;
  const yMax = softMax !== undefined ? Math.max(softMax, dataMax) : dataMax;
  const yRange = yMax - yMin || 1;

  const toX = (i: number) => (i / (points.length - 1)) * W;
  const toY = (v: number) => H - PAD - ((v - yMin) / yRange) * (H - PAD * 2);

  const ptStr = points.map((p, i) => `${toX(i)},${toY(p.v)}`).join(" ");
  const last = points[points.length - 1];
  const lastX = toX(points.length - 1);
  const lastY = toY(last.v);

  const areaD = [
    `M ${toX(0)},${H}`,
    ...points.map((p, i) => `L ${toX(i)},${toY(p.v)}`),
    `L ${lastX},${H}`,
    "Z",
  ].join(" ");

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="sp-svg"
      style={{ height }}
    >
      {/* Subtle grid lines at 25%, 50%, 75% */}
      {[0.25, 0.5, 0.75].map((f) => (
        <line
          key={f}
          x1={0} y1={H - PAD - f * (H - PAD * 2)}
          x2={W} y2={H - PAD - f * (H - PAD * 2)}
          stroke="var(--border)"
          strokeWidth={0.5}
        />
      ))}
      {/* Area fill */}
      <path d={areaD} fill={color} fillOpacity={0.12} />
      {/* Line */}
      <polyline points={ptStr} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
      {/* Last-value dot */}
      <circle cx={lastX} cy={lastY} r={3} fill={color} />
    </svg>
  );
}

// ── Chart card ────────────────────────────────────────────────────────────────

function ChartCard({
  label, points, color, fmt, unit, softMax,
}: {
  label: string;
  points: MetricPoint[];
  color: string;
  fmt: (v: number) => string;
  unit: string;
  softMax?: number;
}) {
  const values = points.map((p) => p.v);
  const current = values.length ? values[values.length - 1] : null;
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;

  return (
    <div className="nd-chart-card">
      <div className="nd-chart-head">
        <span className="nd-chart-label">{label}</span>
        {current !== null && (
          <span className="nd-chart-current" style={{ color }}>
            {fmt(current)}{unit}
          </span>
        )}
      </div>
      <Sparkline points={points} color={color} softMin={0} softMax={softMax} />
      {min !== null && max !== null && (
        <div className="nd-chart-range">
          <span>min {fmt(min)}{unit}</span>
          <span>max {fmt(max)}{unit}</span>
        </div>
      )}
    </div>
  );
}

// ── Node list card ────────────────────────────────────────────────────────────

function NodeListCard({ h, onSelect }: { h: NodeHealth; onSelect: () => void }) {
  const m = h.metrics;
  const isCtrl = h.ip_address === CTRL_IP;

  return (
    <div className={`nd-card s-${h.status}`}>
      <div className="nd-card-bar" style={{ background: `var(--status-${h.status.toLowerCase()})` }} />
      <div className="nd-card-head">
        <div>
          <div className="nd-card-name">{h.node_name}</div>
          <div className="nd-card-ip">{h.ip_address}</div>
        </div>
        <div className="nd-card-badges">
          {isCtrl && <span className="nd-badge nd-badge-ctrl">CTRL</span>}
          <span className={`nd-badge nd-badge-status s-${h.status}`}>{h.status}</span>
        </div>
      </div>
      {m ? (
        <div className="nd-card-stats">
          <div className="nd-stat"><span className="nd-stat-label">CPU</span><span className="nd-stat-val">{m.cpu_load_1m.toFixed(2)}</span></div>
          <div className="nd-stat"><span className="nd-stat-label">RAM</span><span className="nd-stat-val">{m.memory_percent.toFixed(0)}%</span></div>
          <div className="nd-stat"><span className="nd-stat-label">Disk</span><span className="nd-stat-val">{m.disk_percent.toFixed(0)}%</span></div>
          <div className="nd-stat">
            <span className="nd-stat-label">Temp</span>
            <span className="nd-stat-val">
              {m.temperature_celsius !== null ? `${m.temperature_celsius.toFixed(0)}°C` : "—"}
            </span>
          </div>
        </div>
      ) : (
        <div className="nd-card-offline">{h.error ?? "Node unreachable"}</div>
      )}
      <button className="nd-details-btn" onClick={onSelect}>Details →</button>
    </div>
  );
}

// ── Detail view ───────────────────────────────────────────────────────────────

export function NodeDetailView({ node, onBack }: { node: NodeHealth; onBack: () => void }) {
  const [period, setPeriod] = useState<Period>("1h");
  const [history, setHistory] = useState<NodeMetricsHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const m = node.metrics;
  const isCtrl = node.ip_address === CTRL_IP;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setHistory(null);
    getNodeMetricsHistory(node.node_id, period)
      .then((h) => { if (!cancelled) { setHistory(h); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e instanceof Error ? e.message : "Failed"); setLoading(false); } });
    return () => { cancelled = true; };
  }, [node.node_id, period]);

  const pct = (v: number) => v.toFixed(1);
  const temp = (v: number) => v.toFixed(1);

  return (
    <div className="nd-detail">
      <div className="nd-detail-top">
        <button className="nd-back-btn" onClick={onBack}>← Back</button>
        <div className="nd-detail-header">
          <div className="nd-detail-title">
            <span className="nd-detail-name">{node.node_name}</span>
            <span className="nd-detail-ip">{node.ip_address}</span>
            <div className="nd-card-badges">
              {isCtrl && <span className="nd-badge nd-badge-ctrl">CTRL</span>}
              <span className={`nd-badge nd-badge-status s-${node.status}`}>{node.status}</span>
            </div>
          </div>

          {m && (
            <div className="nd-snapshot">
              <div className="nd-snap-item"><span className="nd-snap-label">CPU load</span><span className="nd-snap-val">{m.cpu_load_1m.toFixed(2)}</span></div>
              <div className="nd-snap-item"><span className="nd-snap-label">Memory</span><span className="nd-snap-val">{m.memory_percent.toFixed(1)}%</span><span className="nd-snap-sub">{fmtBytes(m.memory_total_bytes - m.memory_available_bytes)} / {fmtBytes(m.memory_total_bytes)}</span></div>
              <div className="nd-snap-item"><span className="nd-snap-label">Disk</span><span className="nd-snap-val">{m.disk_percent.toFixed(1)}%</span><span className="nd-snap-sub">{fmtBytes(m.disk_used_bytes)} / {fmtBytes(m.disk_total_bytes)}</span></div>
              <div className="nd-snap-item"><span className="nd-snap-label">Temp</span><span className="nd-snap-val">{m.temperature_celsius !== null ? `${m.temperature_celsius.toFixed(1)}°C` : "—"}</span></div>
              <div className="nd-snap-item"><span className="nd-snap-label">Uptime</span><span className="nd-snap-val">{fmtUptime(m.uptime_seconds)}</span></div>
            </div>
          )}
        </div>

        <div className="nd-period-pills">
          {(["1h", "6h", "24h"] as Period[]).map((p) => (
            <button
              key={p}
              className={`nd-period-pill${period === p ? " nd-period-active" : ""}`}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Querying Prometheus…</span></div>
      ) : error ? (
        <div className="err-banner">{error}</div>
      ) : history ? (
        <div className="nd-charts-grid">
          <ChartCard label="CPU" points={history.cpu_pct} color="var(--blue)" fmt={pct} unit="%" softMax={100} />
          <ChartCard label="Memory" points={history.memory_pct} color="var(--green)" fmt={pct} unit="%" softMax={100} />
          <ChartCard label="Disk" points={history.disk_pct} color="var(--amber)" fmt={pct} unit="%" softMax={100} />
          <ChartCard label="Temperature" points={history.temperature_c} color="var(--red)" fmt={temp} unit="°C" softMax={85} />
          <ChartCard label="Network Rx" points={history.net_rx_bps} color="#7c3aed" fmt={fmtBps} unit="" />
          <ChartCard label="Network Tx" points={history.net_tx_bps} color="#0d9488" fmt={fmtBps} unit="" />
        </div>
      ) : null}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NodesPage() {
  const [nodes, setNodes] = useState<NodeHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NodeHealth | null>(null);

  useEffect(() => {
    getAllHealth()
      .then((data) => {
        setNodes(data.sort((a, b) => a.node_name.localeCompare(b.node_name, undefined, { numeric: true })));
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load nodes"))
      .finally(() => setLoading(false));
  }, []);

  const online = nodes.filter((n) => n.status === "ONLINE").length;

  if (selected) {
    return <NodeDetailView node={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div className="nd-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total nodes</div>
          <div className="summ-value sv-blue">{nodes.length}</div>
          <div className="summ-sub">10.100.102.0/24</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Online</div>
          <div className="summ-value sv-green">{online}</div>
          <div className="summ-sub">{nodes.length ? `${Math.round((online / nodes.length) * 100)}% availability` : "—"}</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Offline</div>
          <div className={`summ-value${(nodes.length - online) > 0 ? " sv-red" : " sv-dim"}`}>{nodes.length - online}</div>
          <div className="summ-sub">{nodes.length - online === 0 ? "All nodes healthy" : "Node(s) unreachable"}</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Control plane</div>
          <div className="summ-value sv-amber">pi-node1</div>
          <div className="summ-sub">10.100.102.10 · K3s API</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Cluster nodes</span>
        <span className="section-meta">click a node to view Prometheus time-series</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading nodes…</span></div>
      ) : (
        <div className="nd-grid">
          {nodes.map((n) => (
            <NodeListCard key={n.node_id} h={n} onSelect={() => setSelected(n)} />
          ))}
        </div>
      )}
    </div>
  );
}
