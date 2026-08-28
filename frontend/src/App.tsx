import { useEffect, useState } from "react";
import "./App.css";
import { getAllHealth } from "./api/health";
import type { NodeHealth, NodeStatus } from "./types/node";

const POLL_MS = 30_000;

// ── Formatters ──────────────────────────────────────────────────────────────

function fmtBytes(b: number): string {
  if (b >= 1_073_741_824) return `${(b / 1_073_741_824).toFixed(1)} GB`;
  return `${(b / 1_048_576).toFixed(0)} MB`;
}

function fmtUptime(secs: number): string {
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function bar(pct: number): "ok" | "warn" | "danger" {
  if (pct >= 90) return "danger";
  if (pct >= 75) return "warn";
  return "ok";
}

// ── Clock ───────────────────────────────────────────────────────────────────

function Clock() {
  const [time, setTime] = useState(() => new Date().toLocaleTimeString());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="header-clock">{time}</span>;
}

// ── Ring gauge ──────────────────────────────────────────────────────────────

function Ring({
  pct,
  label,
  value,
  size = 64,
}: {
  pct: number;
  label: string;
  value: string;
  size?: number;
}) {
  const strokeW = 5;
  const r = (size - strokeW) / 2;
  const circ = 2 * Math.PI * r;
  const dash = circ * Math.min(pct, 100) / 100;
  const lvl = bar(pct);
  const cx = size / 2;
  const color =
    lvl === "danger" ? "var(--red)" : lvl === "warn" ? "var(--amber)" : "var(--cyan)";

  return (
    <div className="ring-wrap">
      <svg width={size} height={size} className="ring-svg">
        <circle
          cx={cx} cy={cx} r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeW}
        />
        <circle
          cx={cx} cy={cx} r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeW}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
          style={{ transition: "stroke-dasharray 0.6s cubic-bezier(0.4,0,0.2,1)" }}
        />
      </svg>
      <div className="ring-inner">
        <span className={`ring-pct${lvl !== "ok" ? ` ${lvl}` : ""}`}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="ring-label">{label}</div>
      <div className="ring-value">{value}</div>
    </div>
  );
}

// ── Metric tile ─────────────────────────────────────────────────────────────

function Tile({
  label,
  value,
  pct,
  colorClass = "",
}: {
  label: string;
  value: string;
  pct?: number;
  colorClass?: string;
}) {
  const lvl = pct !== undefined ? bar(pct) : "ok";
  return (
    <div className="metric-tile">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${colorClass || (lvl !== "ok" ? lvl : "")}`}>{value}</div>
      {pct !== undefined && (
        <div className="metric-bar">
          <div
            className={`metric-bar-fill ${lvl !== "ok" ? lvl : ""}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ── Node card ───────────────────────────────────────────────────────────────

function NodeCard({ h }: { h: NodeHealth }) {
  const m = h.metrics;
  const ts = new Date(h.checked_at).toLocaleTimeString();

  return (
    <div className={`node-card ${h.status}`}>
      <div className={`card-accent ${h.status}`} />
      <div className="card-body">
        <div className="card-header">
          <div className="node-info">
            <span className="node-name">{h.node_name}</span>
            <span className="node-ip">{h.ip_address}</span>
          </div>
          <span className={`status-badge ${h.status}`}>
            <span className="status-dot" />
            {h.status}
          </span>
        </div>

        {m ? (
          <>
            <div className="metrics-rings">
              <Ring
                pct={m.memory_percent}
                label="RAM"
                value={`${fmtBytes(m.memory_total_bytes - m.memory_available_bytes)} / ${fmtBytes(m.memory_total_bytes)}`}
              />
              <Ring
                pct={m.disk_percent}
                label="Disk"
                value={`${fmtBytes(m.disk_used_bytes)} / ${fmtBytes(m.disk_total_bytes)}`}
              />
            </div>
            <div className="metrics-stats">
              <Tile label="CPU load" value={m.cpu_load_1m.toFixed(2)} />
              <Tile label="Uptime" value={fmtUptime(m.uptime_seconds)} colorClass="cyan" />
              {m.temperature_celsius !== null ? (
                <Tile
                  label="Temp"
                  value={`${m.temperature_celsius.toFixed(1)}°C`}
                  pct={(m.temperature_celsius / 85) * 100}
                />
              ) : (
                <Tile label="Temp" value="—" />
              )}
            </div>
          </>
        ) : (
          <div className="offline-body">
            <div className="offline-icon">⊘</div>
            <div className="offline-msg">{h.error ?? "Node unreachable"}</div>
          </div>
        )}
      </div>
      <div className="checked-at">checked {ts}</div>
    </div>
  );
}

// ── Cluster status ───────────────────────────────────────────────────────────

function clusterStatus(nodes: NodeHealth[]): { label: string; cls: string } {
  const offline = nodes.filter((n) => n.status === "OFFLINE").length;
  const degraded = nodes.filter((n) => n.status === "DEGRADED").length;
  if (offline === nodes.length && nodes.length > 0) return { label: "All offline", cls: "critical" };
  if (offline > 0 || degraded > 0) return { label: "Degraded", cls: "degraded" };
  if (nodes.length === 0) return { label: "No nodes", cls: "degraded" };
  return { label: "All systems operational", cls: "healthy" };
}

function avgTemp(nodes: NodeHealth[]): string {
  const temps = nodes.flatMap((n) =>
    n.metrics?.temperature_celsius != null ? [n.metrics.temperature_celsius] : []
  );
  if (temps.length === 0) return "—";
  return `${(temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1)}°C`;
}

// ── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [nodes, setNodes] = useState<NodeHealth[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = () =>
    getAllHealth()
      .then((data) => { setNodes(data); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const online  = nodes.filter((n) => n.status === "ONLINE").length;
  const offline = nodes.filter((n) => n.status === "OFFLINE").length;
  const cs = clusterStatus(nodes);

  return (
    <>
      <header>
        <div className="header-left">
          <div className="logo-mark">π</div>
          <div>
            <div className="header-title">Pi Cluster</div>
            <div className="header-subtitle">10.100.102.0/24</div>
          </div>
        </div>
        <div className="header-right">
          <div className="header-meta">
            {!loading && (
              <span className={`cluster-pill ${cs.cls}`}>
                <span className="cluster-pill-dot" />
                {cs.label}
              </span>
            )}
          </div>
          <Clock />
        </div>
      </header>

      <main>
        {error && <div className="error-banner">API error: {error}</div>}

        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <span>Connecting to cluster…</span>
          </div>
        ) : (
          <>
            {nodes.length > 0 && (
              <div className="summary">
                <div className="summary-stat">
                  <span className="summary-label">Total nodes</span>
                  <span className="summary-value cyan">{nodes.length}</span>
                </div>
                <div className="summary-stat">
                  <span className="summary-label">Online</span>
                  <span className="summary-value green">{online}</span>
                </div>
                <div className="summary-stat">
                  <span className="summary-label">Offline</span>
                  <span className={`summary-value ${offline > 0 ? "red" : ""}`}>{offline}</span>
                </div>
                <div className="summary-stat">
                  <span className="summary-label">Avg temp</span>
                  <span className="summary-value amber">{avgTemp(nodes)}</span>
                </div>
              </div>
            )}

            <div className="node-grid">
              {nodes.map((n) => (
                <NodeCard key={n.node_id} h={n} />
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
