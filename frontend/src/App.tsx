import { useEffect, useState } from "react";
import "./App.css";
import { getAllHealth } from "./api/health";
import { useAuth } from "./context/AuthContext";
import AlertHistoryPage from "./pages/AlertHistoryPage";
import AuditPage from "./pages/AuditPage";
import AlertsPanel from "./components/AlertsPanel";
import { NodeDetailView } from "./pages/NodesPage";
import WorkloadsPage from "./pages/WorkloadsPage";
import type { NodeHealth } from "./types/node";

type Page = "dashboard" | "workloads" | "audit" | "alert-history";

const POLL_MS  = 30_000;
const CTRL_IP  = "10.100.102.10";

const NAV = [
  { label: "Prometheus", href: `http://${CTRL_IP}:9090`,        icon: "◎" },
  { label: "Grafana",    href: `http://${CTRL_IP}:3000`,         icon: "▣" },
  { label: "Jenkins",    href: `http://${CTRL_IP}:8080`,         icon: "⬡" },
  { label: "ArgoCD",     href: `https://${CTRL_IP}:30443`,       icon: "◈" },
  { label: "API Docs",   href: `http://${CTRL_IP}:8000/docs`,    icon: "≋" },
  { label: "Metrics",    href: `http://${CTRL_IP}:8000/metrics`, icon: "⌬" },
];

// ── Formatters ───────────────────────────────────────────────────────────────

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

function sev(pct: number): "ok" | "warn" | "crit" {
  return pct >= 90 ? "crit" : pct >= 75 ? "warn" : "ok";
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

// ── Ring gauge ────────────────────────────────────────────────────────────────

function Ring({ pct, label, detail, size = 90 }: {
  pct: number; label: string; detail: string; size?: number;
}) {
  const sw  = 7;
  const r   = (size - sw) / 2;
  const c   = 2 * Math.PI * r;
  const f   = c * Math.min(pct, 100) / 100;
  const lv  = sev(pct);
  const cx  = size / 2;
  const col = lv === "crit" ? "var(--red)" : lv === "warn" ? "var(--amber)" : "var(--blue)";

  return (
    <div className="ring-wrap">
      <svg width={size} height={size} className="ring-svg">
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--border)" strokeWidth={sw} />
        <circle
          cx={cx} cy={cx} r={r} fill="none"
          stroke={col} strokeWidth={sw}
          strokeDasharray={`${f} ${c - f}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
          style={{ transition: "stroke-dasharray .55s ease" }}
        />
      </svg>
      <div className="ring-center">
        <span className={`ring-pct${lv !== "ok" ? ` v-${lv}` : ""}`}>{pct.toFixed(0)}%</span>
      </div>
      <div className="ring-lbl">{label}</div>
      <div className="ring-detail">{detail}</div>
    </div>
  );
}

// ── Stat tile ─────────────────────────────────────────────────────────────────

function StatTile({ label, value, accent, bar: barPct }: {
  label: string; value: string; accent?: string; bar?: number;
}) {
  const lv = barPct !== undefined ? sev(barPct) : "ok";
  return (
    <div className="stat-tile">
      <div className="stat-lbl">{label}</div>
      <div className={`stat-val${accent ? ` a-${accent}` : ""}`}>{value}</div>
      {barPct !== undefined && (
        <div className="stat-bar">
          <div className={`stat-bar-fill${lv !== "ok" ? ` w-${lv}` : ""}`}
            style={{ width: `${Math.min(barPct, 100)}%` }} />
        </div>
      )}
    </div>
  );
}

// ── Node card ─────────────────────────────────────────────────────────────────

function NodeCard({ h, onDetails }: { h: NodeHealth; onDetails: () => void }) {
  const m     = h.metrics;
  const ts    = new Date(h.checked_at).toLocaleTimeString();
  const isCtrl = h.ip_address === CTRL_IP;

  return (
    <div className={`card s-${h.status}`}>
      <div className={`card-bar b-${h.status}`} />

      <div className="card-head">
        <div>
          <div className="node-name">{h.node_name}</div>
          <div className="node-ip">{h.ip_address}</div>
        </div>
        <div className="badges">
          {isCtrl && <span className="badge-ctrl">CTRL</span>}
          <span className={`badge-status bs-${h.status}`}>
            <span className="st-dot" />{h.status}
          </span>
        </div>
      </div>

      <div className="card-divider" />

      {m ? (
        <>
          <div className="rings-row">
            <Ring
              pct={m.memory_percent} label="RAM"
              detail={`${fmtBytes(m.memory_total_bytes - m.memory_available_bytes)} / ${fmtBytes(m.memory_total_bytes)}`}
            />
            <Ring
              pct={m.disk_percent} label="Disk"
              detail={`${fmtBytes(m.disk_used_bytes)} / ${fmtBytes(m.disk_total_bytes)}`}
            />
          </div>

          <div className="stats-row">
            <StatTile label="CPU Load" value={m.cpu_load_1m.toFixed(2)} />
            <StatTile label="Uptime"   value={fmtUptime(m.uptime_seconds)} accent="blue" />
            <StatTile
              label="Temp"
              value={m.temperature_celsius !== null ? `${m.temperature_celsius.toFixed(1)}°C` : "—"}
              bar={m.temperature_celsius !== null ? (m.temperature_celsius / 85) * 100 : undefined}
              accent={m.temperature_celsius !== null && m.temperature_celsius >= 65 ? "amber" : undefined}
            />
          </div>
        </>
      ) : (
        <div className="card-offline">
          <span className="offline-glyph">⊘</span>
          <span className="offline-msg">{h.error ?? "Node unreachable"}</span>
        </div>
      )}

      <div className="card-foot">
        <span>checked {ts}</span>
        <button className="card-detail-btn" onClick={onDetails}>Details →</button>
      </div>
    </div>
  );
}

// ── Cluster helpers ───────────────────────────────────────────────────────────

function pillState(nodes: NodeHealth[]): { label: string; cls: string } {
  const off = nodes.filter((n) => n.status === "OFFLINE").length;
  const deg = nodes.filter((n) => n.status === "DEGRADED").length;
  if (!nodes.length)          return { label: "No nodes",     cls: "deg" };
  if (off === nodes.length)   return { label: "All offline",  cls: "crit" };
  if (off > 0 || deg > 0)     return { label: "Degraded",     cls: "deg" };
  return                             { label: "Healthy",         cls: "ok" };
}

function avgTemp(nodes: NodeHealth[]): string {
  const ts = nodes.flatMap((n) =>
    n.metrics?.temperature_celsius != null ? [n.metrics.temperature_celsius] : []
  );
  if (!ts.length) return "—";
  return `${(ts.reduce((a, b) => a + b) / ts.length).toFixed(1)}°C`;
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { username, role, logout } = useAuth();
  const [page,         setPage]         = useState<Page>("dashboard");
  const [nodes,        setNodes]        = useState<NodeHealth[]>([]);
  const [error,        setError]        = useState<string | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [sbOpen,       setSbOpen]       = useState(true);
  const [selectedNode, setSelectedNode] = useState<NodeHealth | null>(null);

  const refresh = () =>
    getAllHealth()
      .then((d) => { setNodes(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { refresh(); const id = setInterval(refresh, POLL_MS); return () => clearInterval(id); }, []);

  const sorted  = [...nodes].sort((a, b) =>
    a.node_name.localeCompare(b.node_name, undefined, { numeric: true })
  );
  const online  = nodes.filter((n) => n.status === "ONLINE").length;
  const offline = nodes.filter((n) => n.status === "OFFLINE").length;
  const pill    = pillState(nodes);

  return (
    <div className={`layout${sbOpen ? "" : " sb-closed"}`}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sb-brand">
          <div className="sb-logo">π</div>
          <div>
            <div className="sb-title">Pi Cluster</div>
            <div className="sb-sub">Control Platform</div>
          </div>
        </div>

        <nav className="sb-nav">
          <div className="sb-section">Cluster</div>
          <a
            href="#"
            className={`sb-link${page === "dashboard" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); setPage("dashboard"); }}
          >
            <span className="sb-icon">⊞</span>
            Dashboard
          </a>
          <a
            href="#"
            className={`sb-link${page === "workloads" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); setPage("workloads"); }}
          >
            <span className="sb-icon">⬡</span>
            Workloads
          </a>
          <a
            href="#"
            className={`sb-link${page === "audit" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); setPage("audit"); }}
          >
            <span className="sb-icon">≔</span>
            Audit Log
          </a>
          <a
            href="#"
            className={`sb-link${page === "alert-history" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); setPage("alert-history"); }}
          >
            <span className="sb-icon">⊛</span>
            Alert History
          </a>

          <div className="sb-section">Services</div>
          {NAV.map((l) => (
            <a key={l.label} href={l.href} target="_blank" rel="noreferrer" className="sb-link">
              <span className="sb-icon">{l.icon}</span>
              {l.label}
              <span className="sb-ext">↗</span>
            </a>
          ))}
        </nav>

        <div className="sb-foot">
          <div className="sb-user">
            <span className="sb-user-icon">◉</span>
            <div>
              <div className="sb-user-name">{username}</div>
              <div className="sb-user-role">{role}</div>
            </div>
          </div>
          <button className="sb-logout" onClick={logout}>Sign out</button>
          <div className="sb-foot-label" style={{ marginTop: "0.8rem" }}>Version</div>
          <div className="sb-foot-val">v0.1.0 · Phase 30</div>
          <div className="sb-foot-label" style={{ marginTop: "0.4rem" }}>Cluster</div>
          <div className="sb-foot-val">4 nodes · arm64 · 10.100.102.0/24</div>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <div className="main-area">
        <header className="topbar">
          <div className="tb-left">
            <button className="hamburger" onClick={() => setSbOpen((o) => !o)}>
              <span /><span /><span />
            </button>
            <h1 className="page-title">
              {page === "workloads" ? "Workloads" : page === "audit" ? "Audit Log" : page === "alert-history" ? "Alert History" : "Dashboard"}
            </h1>
          </div>
          <div className="tb-right">
            {page === "dashboard" && !loading && (
              <span className={`pill pill-${pill.cls}`}>
                <span className="pill-dot" />
                {pill.label}
              </span>
            )}
            <Clock />
          </div>
        </header>

        <main>
          {page === "workloads" ? (
            <WorkloadsPage />
          ) : page === "audit" ? (
            <AuditPage />
          ) : page === "alert-history" ? (
            <AlertHistoryPage />
          ) : selectedNode ? (
            <NodeDetailView node={selectedNode} onBack={() => setSelectedNode(null)} />
          ) : (
            <>
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
                      <div className="summ-card sc-blue">
                        <div className="summ-label">Total nodes</div>
                        <div className="summ-value sv-blue">{nodes.length}</div>
                        <div className="summ-sub">10.100.102.0/24</div>
                      </div>
                      <div className="summ-card sc-green">
                        <div className="summ-label">Online</div>
                        <div className="summ-value sv-green">{online}</div>
                        <div className="summ-sub">{((online / nodes.length) * 100).toFixed(0)}% availability</div>
                      </div>
                      <div className="summ-card sc-red">
                        <div className="summ-label">Offline</div>
                        <div className={`summ-value${offline > 0 ? " sv-red" : " sv-dim"}`}>{offline}</div>
                        <div className="summ-sub">{offline === 0 ? "All nodes healthy" : `${offline} node(s) down`}</div>
                      </div>
                      <div className="summ-card sc-amber">
                        <div className="summ-label">Avg Temperature</div>
                        <div className="summ-value sv-amber">{avgTemp(nodes)}</div>
                        <div className="summ-sub">across {nodes.filter(n => n.metrics?.temperature_celsius != null).length} reporting nodes</div>
                      </div>
                    </div>
                  )}

                  <AlertsPanel />

                  <div className="section-header">
                    <span className="section-title">Node Health</span>
                    <span className="section-meta">auto-refresh every 30s</span>
                  </div>

                  <div className="node-grid">
                    {sorted.map((n) => (
                      <NodeCard key={n.node_id} h={n} onDetails={() => setSelectedNode(n)} />
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
