import { useEffect, useState } from "react";
import "./App.css";
import { getAllHealth } from "./api/health";
import type { NodeHealth, NodeStatus } from "./types/node";

const POLL_MS = 30_000;

function fmt(bytes: number): string {
  const gb = bytes / 1_073_741_824;
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1_048_576).toFixed(0)} MB`;
}

function fmtUptime(secs: number): string {
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function level(pct: number): "ok" | "warn" | "danger" {
  if (pct >= 90) return "danger";
  if (pct >= 75) return "warn";
  return "ok";
}

function Bar({ pct }: { pct: number }) {
  const cls = level(pct);
  return (
    <div className="bar-bg">
      <div className="bar-fill" style={{ width: `${Math.min(pct, 100)}%` }} data-level={cls} />
    </div>
  );
}

function Metric({ label, value, pct }: { label: string; value: string; pct?: number }) {
  const cls = pct !== undefined ? level(pct) : "ok";
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${cls === "ok" ? "" : cls}`}>{value}</div>
      {pct !== undefined && <Bar pct={pct} />}
    </div>
  );
}

function NodeCard({ h }: { h: NodeHealth }) {
  const m = h.metrics;
  const ts = new Date(h.checked_at).toLocaleTimeString();
  return (
    <div className={`node-card ${h.status}`}>
      <div className="node-header">
        <div>
          <div className="node-name">{h.node_name}</div>
          <div className="node-ip">{h.ip_address}</div>
        </div>
        <span className={`badge ${h.status}`}>{h.status}</span>
      </div>

      {m ? (
        <div className="metrics">
          <Metric label="CPU load" value={m.cpu_load_1m.toFixed(2)} />
          <Metric
            label="RAM"
            value={`${fmt(m.memory_total_bytes - m.memory_available_bytes)} / ${fmt(m.memory_total_bytes)}`}
            pct={m.memory_percent}
          />
          <Metric
            label="Disk"
            value={`${fmt(m.disk_used_bytes)} / ${fmt(m.disk_total_bytes)}`}
            pct={m.disk_percent}
          />
          <Metric label="Uptime" value={fmtUptime(m.uptime_seconds)} />
          {m.temperature_celsius !== null && (
            <Metric
              label="Temp"
              value={`${m.temperature_celsius.toFixed(1)} °C`}
              pct={m.temperature_celsius > 0 ? (m.temperature_celsius / 85) * 100 : 0}
            />
          )}
        </div>
      ) : (
        h.error && <div className="node-error">{h.error}</div>
      )}

      <div className="checked-at">checked {ts}</div>
    </div>
  );
}

function summary(nodes: NodeHealth[]) {
  return {
    online: nodes.filter((n) => n.status === "ONLINE").length,
    offline: nodes.filter((n) => n.status === "OFFLINE").length,
    total: nodes.length,
  };
}

export default function App() {
  const [nodes, setNodes] = useState<NodeHealth[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const refresh = () => {
    getAllHealth()
      .then((data) => {
        setNodes(data);
        setError(null);
        setLastRefresh(new Date());
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const s = summary(nodes);

  return (
    <>
      <header>
        <h1>Pi Cluster</h1>
        <span className="refresh-info">
          {lastRefresh ? `updated ${lastRefresh.toLocaleTimeString()}` : "loading…"}
        </span>
      </header>
      <main>
        {error && <div className="error-banner">API error: {error}</div>}

        {!loading && nodes.length > 0 && (
          <div className="status-bar">
            <div className="stat">
              <div className="stat-label">Total nodes</div>
              <div className="stat-value">{s.total}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Online</div>
              <div className="stat-value" style={{ color: "#4ade80" }}>{s.online}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Offline</div>
              <div className="stat-value" style={{ color: s.offline > 0 ? "#f87171" : "#94a3b8" }}>{s.offline}</div>
            </div>
          </div>
        )}

        {loading && <p className="loading">Connecting to cluster…</p>}

        <div className="grid">
          {nodes.map((n) => (
            <NodeCard key={n.node_id} h={n} />
          ))}
        </div>
      </main>
    </>
  );
}
