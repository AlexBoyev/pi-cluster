import { useEffect, useState } from "react";
import "./App.css";
import { getAllHealth } from "./api/health";
import type { NodeHealth } from "./types/node";

const POLL_MS = 30_000;
const CTRL_IP  = "10.100.102.10";

// ── Formatters ───────────────────────────────────────────────────────────────

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

function severity(pct: number): "ok" | "warn" | "crit" {
  if (pct >= 90) return "crit";
  if (pct >= 75) return "warn";
  return "ok";
}

// ── Clock ────────────────────────────────────────────────────────────────────

function Clock() {
  const [t, setT] = useState(() => new Date().toLocaleTimeString());
  useEffect(() => {
    const id = setInterval(() => setT(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="clock">{t}</span>;
}

// ── Sidebar ──────────────────────────────────────────────────────────────────

const NAV_LINKS = [
  { label: "Prometheus",  href: `http://${CTRL_IP}:9090`,       ext: true },
  { label: "Grafana",     href: `http://${CTRL_IP}:3000`,        ext: true },
  { label: "API Docs",    href: `http://${CTRL_IP}:8000/docs`,   ext: true },
  { label: "Metrics",     href: `http://${CTRL_IP}:8000/metrics`,ext: true },
];

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open && <div className="backdrop" onClick={onClose} />}
      <aside className={`sidebar${open ? " open" : ""}`}>
        <div className="sb-brand">
          <div className="sb-logo">π</div>
          <div>
            <div className="sb-name">Pi Cluster</div>
            <div className="sb-sub">10.100.102.0/24</div>
          </div>
          <button className="sb-close" onClick={onClose}>✕</button>
        </div>

        <div className="sb-divider" />

        <nav className="sb-nav">
          <div className="sb-section-label">Cluster</div>
          <a href="#" className="sb-item active" onClick={onClose}>
            <span className="sb-icon">⊞</span>
            Dashboard
          </a>

          <div className="sb-section-label">Services</div>
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="sb-item"
            >
              <span className="sb-icon">◎</span>
              {l.label}
              <span className="sb-ext">↗</span>
            </a>
          ))}
        </nav>

        <div className="sb-footer">
          <span className="sb-version">v0.1.0 · Phase 3</span>
          <span className="sb-build">4 nodes · arm64</span>
        </div>
      </aside>
    </>
  );
}

// ── Ring gauge ────────────────────────────────────────────────────────────────

function Ring({ pct, label, detail, size = 76 }: {
  pct: number; label: string; detail: string; size?: number;
}) {
  const sw = 6;
  const r  = (size - sw) / 2;
  const c  = 2 * Math.PI * r;
  const fill = c * Math.min(pct, 100) / 100;
  const sev  = severity(pct);
  const cx   = size / 2;
  const stroke =
    sev === "crit" ? "var(--red)" : sev === "warn" ? "var(--amber)" : "var(--teal)";

  return (
    <div className="ring">
      <svg width={size} height={size}>
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--border)" strokeWidth={sw} />
        <circle
          cx={cx} cy={cx} r={r} fill="none"
          stroke={stroke} strokeWidth={sw}
          strokeDasharray={`${fill} ${c - fill}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
          style={{ transition: "stroke-dasharray .6s cubic-bezier(.4,0,.2,1)" }}
        />
      </svg>
      <div className="ring-center">
        <span className={`ring-pct sev-${sev}`}>{pct.toFixed(0)}%</span>
      </div>
      <div className="ring-label">{label}</div>
      <div className="ring-detail">{detail}</div>
    </div>
  );
}

// ── Stat tile ────────────────────────────────────────────────────────────────

function StatTile({ label, value, accent, bar: barPct }: {
  label: string; value: string; accent?: string; bar?: number;
}) {
  const sev = barPct !== undefined ? severity(barPct) : "ok";
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className={`stat-value${accent ? ` accent-${accent}` : ""}`}>{value}</div>
      {barPct !== undefined && (
        <div className="stat-bar">
          <div
            className={`stat-bar-fill sev-${sev}`}
            style={{ width: `${Math.min(barPct, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ── Node card ────────────────────────────────────────────────────────────────

function NodeCard({ h }: { h: NodeHealth }) {
  const m  = h.metrics;
  const ts = new Date(h.checked_at).toLocaleTimeString();
  const isCtrl = h.ip_address === CTRL_IP;

  return (
    <div className={`card status-${h.status}`}>
      <div className={`card-bar bar-${h.status}`} />

      <div className="card-head">
        <div className="card-title-row">
          <div className="card-node-info">
            <span className="card-name">{h.node_name}</span>
            <span className="card-ip">{h.ip_address}</span>
          </div>
          <div className="card-badges">
            {isCtrl && <span className="badge-ctrl">CTRL</span>}
            <span className={`badge-status st-${h.status}`}>
              <span className="st-dot" />{h.status}
            </span>
          </div>
        </div>
      </div>

      {m ? (
        <div className="card-body">
          <div className="rings-row">
            <Ring
              pct={m.memory_percent}
              label="RAM"
              detail={`${fmtBytes(m.memory_total_bytes - m.memory_available_bytes)} / ${fmtBytes(m.memory_total_bytes)}`}
            />
            <Ring
              pct={m.disk_percent}
              label="Disk"
              detail={`${fmtBytes(m.disk_used_bytes)} / ${fmtBytes(m.disk_total_bytes)}`}
            />
          </div>
          <div className="stats-row">
            <StatTile label="CPU load" value={m.cpu_load_1m.toFixed(2)} />
            <StatTile label="Uptime"   value={fmtUptime(m.uptime_seconds)} accent="teal" />
            <StatTile
              label="Temp"
              value={m.temperature_celsius !== null ? `${m.temperature_celsius.toFixed(1)}°C` : "—"}
              bar={m.temperature_celsius !== null ? (m.temperature_celsius / 85) * 100 : undefined}
            />
          </div>
        </div>
      ) : (
        <div className="card-offline">
          <span className="offline-glyph">⊘</span>
          <span className="offline-msg">{h.error ?? "Node unreachable"}</span>
        </div>
      )}

      <div className="card-foot">checked {ts}</div>
    </div>
  );
}

// ── Cluster helpers ──────────────────────────────────────────────────────────

function clusterPill(nodes: NodeHealth[]): { label: string; cls: string } {
  const off = nodes.filter((n) => n.status === "OFFLINE").length;
  const deg = nodes.filter((n) => n.status === "DEGRADED").length;
  if (nodes.length === 0)          return { label: "No nodes",    cls: "deg" };
  if (off === nodes.length)        return { label: "All offline",  cls: "crit" };
  if (off > 0 || deg > 0)          return { label: "Degraded",     cls: "deg" };
  return                                  { label: "All systems go", cls: "ok" };
}

function avgTemp(nodes: NodeHealth[]): string {
  const ts = nodes.flatMap((n) =>
    n.metrics?.temperature_celsius != null ? [n.metrics.temperature_celsius] : []
  );
  return ts.length
    ? `${(ts.reduce((a, b) => a + b) / ts.length).toFixed(1)}°C`
    : "—";
}

// ── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [nodes,   setNodes]   = useState<NodeHealth[]>([]);
  const [error,   setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sbOpen,  setSbOpen]  = useState(false);

  const refresh = () =>
    getAllHealth()
      .then((d) => { setNodes(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const sorted  = [...nodes].sort((a, b) =>
    a.node_name.localeCompare(b.node_name, undefined, { numeric: true })
  );
  const online  = nodes.filter((n) => n.status === "ONLINE").length;
  const offline = nodes.filter((n) => n.status === "OFFLINE").length;
  const pill    = clusterPill(nodes);

  return (
    <>
      <Sidebar open={sbOpen} onClose={() => setSbOpen(false)} />

      <header>
        <div className="h-left">
          <button className="hamburger" onClick={() => setSbOpen((o) => !o)}>
            <span /><span /><span />
          </button>
          <div className="h-logo">π</div>
          <div className="h-title">Pi Cluster</div>
        </div>
        <div className="h-right">
          {!loading && (
            <span className={`pill pill-${pill.cls}`}>
              <span className="pill-dot" />
              {pill.label}
            </span>
          )}
          <Clock />
        </div>
      </header>

      <main>
        {error && <div className="err-banner">API error: {error}</div>}

        {loading ? (
          <div className="loading">
            <div className="spinner" />
            <span>Connecting to cluster…</span>
          </div>
        ) : (
          <>
            {nodes.length > 0 && (
              <div className="summary-row">
                <div className="summ-card top-teal">
                  <div className="summ-label">Total nodes</div>
                  <div className="summ-value color-teal">{nodes.length}</div>
                </div>
                <div className="summ-card top-green">
                  <div className="summ-label">Online</div>
                  <div className="summ-value color-green">{online}</div>
                </div>
                <div className="summ-card top-red">
                  <div className="summ-label">Offline</div>
                  <div className={`summ-value${offline > 0 ? " color-red" : ""}`}>{offline}</div>
                </div>
                <div className="summ-card top-amber">
                  <div className="summ-label">Avg temp</div>
                  <div className="summ-value color-amber">{avgTemp(nodes)}</div>
                </div>
              </div>
            )}

            <div className="node-grid">
              {sorted.map((n) => (
                <NodeCard key={n.node_id} h={n} />
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
