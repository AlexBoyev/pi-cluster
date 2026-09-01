import { useEffect, useState } from "react";
import "./App.css";
import { getAllHealth } from "./api/health";
import { restartAllNodes, shutdownAllNodes, restartNode, shutdownNode } from "./api/nodes";
import { useAuth } from "./context/AuthContext";
import ConfirmDialog from "./components/ConfirmDialog";
import AlertHistoryPage from "./pages/AlertHistoryPage";
import AlertRulesPage from "./pages/AlertRulesPage";
import AuditPage from "./pages/AuditPage";
import CapacityPage from "./pages/CapacityPage";
import ConfigMapsPage from "./pages/ConfigMapsPage";
import CronJobsPage from "./pages/CronJobsPage";
import EventsPage from "./pages/EventsPage";
import JobsPage from "./pages/JobsPage";
import LiveLogsPage from "./pages/LiveLogsPage";
import NamespacesPage from "./pages/NamespacesPage";
import HelmPage from "./pages/HelmPage";
import NotificationsPage from "./pages/NotificationsPage";
import ObjectsPage from "./pages/ObjectsPage";
import QuotasPage from "./pages/QuotasPage";
import RBACPage from "./pages/RBACPage";
import SecretsPage from "./pages/SecretsPage";
import ServicesPage from "./pages/ServicesPage";
import StoragePage from "./pages/StoragePage";
import UsersPage from "./pages/UsersPage";
import AlertsPanel from "./components/AlertsPanel";
import NodeSSHModal from "./components/NodeSSHModal";
import { NodeDetailView } from "./pages/NodesPage";
import WorkloadsPage from "./pages/WorkloadsPage";
import type { NodeHealth } from "./types/node";

type Page = "dashboard" | "workloads" | "capacity" | "events" | "namespaces" | "audit" | "alert-history" | "users" | "configmaps" | "secrets" | "services" | "cronjobs" | "storage" | "notifications" | "objects" | "helm" | "rbac" | "jobs" | "quotas" | "alert-rules" | "live-logs";

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
  const [sshOpen,    setSshOpen]    = useState(false);
  const [nodeAction, setNodeAction] = useState<"restart" | "shutdown" | null>(null);
  const [nodeBusy,   setNodeBusy]   = useState(false);

  return (
    <>
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
            <button
              className="card-node-btn card-node-restart"
              onClick={() => setNodeAction("restart")}
            >Restart</button>
            <button
              className="card-node-btn card-node-shutdown"
              onClick={() => setNodeAction("shutdown")}
            >Shutdown</button>
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
            <span className="offline-glyph">&#x2298;</span>
            <span className="offline-msg">{h.error ?? "Node unreachable"}</span>
          </div>
        )}

        <div className="card-foot">
          <span>checked {ts}</span>
          <div className="card-foot-btns">
            <button className="card-ssh-btn" onClick={() => setSshOpen(true)}>SSH</button>
            <button className="card-detail-btn" onClick={onDetails}>Details &#x2192;</button>
          </div>
        </div>
      </div>

      {sshOpen && <NodeSSHModal node={h} onClose={() => setSshOpen(false)} />}

      {nodeAction && (
        <ConfirmDialog
          title={nodeAction === "restart" ? `Restart ${h.node_name}?` : `Shutdown ${h.node_name}?`}
          message={
            nodeAction === "restart"
              ? `This will reboot ${h.node_name} (${h.ip_address}). Any workloads on this node will be temporarily unavailable.`
              : `This will power off ${h.node_name} (${h.ip_address}). It will need to be manually powered on again.`
          }
          confirmLabel={nodeBusy ? "Please wait…" : nodeAction === "restart" ? "Restart" : "Shutdown"}
          onConfirm={async () => {
            setNodeBusy(true);
            try {
              if (nodeAction === "restart") await restartNode(h.node_id);
              else await shutdownNode(h.node_id);
            } finally {
              setNodeBusy(false);
              setNodeAction(null);
            }
          }}
          onCancel={() => setNodeAction(null)}
          dangerous
        />
      )}
    </>
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

// ── Viewer portal ─────────────────────────────────────────────────────────────

const COMING_SOON = [
  { icon: "📅", label: "Calendar",    desc: "Shared team calendar" },
  { icon: "🎮", label: "Games",       desc: "Pi-hosted games" },
  { icon: "📁", label: "File Share",  desc: "Internal file storage" },
  { icon: "💬", label: "Chat",        desc: "Team messaging" },
  { icon: "📊", label: "Dashboard",   desc: "Personal stats" },
  { icon: "⚙️",  label: "Settings",   desc: "Account preferences" },
];

function ViewerPortal({ username, logout }: { username: string | null; logout: () => void }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sb-brand">
          <div className="sb-logo">π</div>
          <div>
            <div className="sb-title">Pi Cluster</div>
            <div className="sb-sub">Portal</div>
          </div>
        </div>
        <nav className="sb-nav">
          <div className="sb-section">Services</div>
          {COMING_SOON.map((s) => (
            <span key={s.label} className="sb-link sb-link-disabled">
              <span className="sb-icon">{s.icon}</span>
              {s.label}
              <span className="sb-ext" style={{ fontSize: "0.6rem", opacity: 0.5 }}>soon</span>
            </span>
          ))}
        </nav>
        <div className="sb-foot">
          <div className="sb-user">
            <span className="sb-user-icon">◉</span>
            <div>
              <div className="sb-user-name">{username}</div>
              <div className="sb-user-role">viewer</div>
            </div>
          </div>
          <button className="sb-logout" onClick={logout}>Sign out</button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="tb-left">
            <h1 className="page-title">Portal</h1>
          </div>
          <div className="tb-right"><Clock /></div>
        </header>
        <main>
          <div className="portal-welcome">
            <div className="portal-greeting">Welcome, {username}</div>
            <div className="portal-sub">Your services will appear here as they become available.</div>
          </div>
          <div className="portal-grid">
            {COMING_SOON.map((s) => (
              <div key={s.label} className="portal-card portal-card-soon">
                <div className="portal-card-icon">{s.icon}</div>
                <div className="portal-card-label">{s.label}</div>
                <div className="portal-card-desc">{s.desc}</div>
                <div className="portal-card-badge">Coming soon</div>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { username, role, logout } = useAuth();
  const [page,         setPage]         = useState<Page>("dashboard");
  const [nodes,        setNodes]        = useState<NodeHealth[]>([]);
  const [error,        setError]        = useState<string | null>(null);
  const [loading,      setLoading]      = useState(true);
  const [sbOpen,        setSbOpen]        = useState(() => window.innerWidth > 768);
  const [selectedNode,  setSelectedNode]  = useState<NodeHealth | null>(null);
  const [clusterAction, setClusterAction] = useState<"restart" | "shutdown" | null>(null);
  const [clusterBusy,   setClusterBusy]   = useState(false);

  const navigate = (p: Page) => {
    setPage(p);
    if (window.innerWidth <= 768) setSbOpen(false);
  };

  const refresh = () =>
    getAllHealth()
      .then((d) => { setNodes(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => {
    if (role !== "admin") return;
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [role]);

  if (role !== "admin") {
    return <ViewerPortal username={username} logout={logout} />;
  }

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
            onClick={(e) => { e.preventDefault(); navigate("dashboard"); }}
          >
            <span className="sb-icon">⊞</span>
            Dashboard
          </a>
          <a
            href="#"
            className={`sb-link${page === "workloads" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("workloads"); }}
          >
            <span className="sb-icon">⬡</span>
            Workloads
          </a>
          <a
            href="#"
            className={`sb-link${page === "capacity" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("capacity"); }}
          >
            <span className="sb-icon">▦</span>
            Capacity
          </a>
          <a
            href="#"
            className={`sb-link${page === "events" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("events"); }}
          >
            <span className="sb-icon">⊜</span>
            Events
          </a>
          <a
            href="#"
            className={`sb-link${page === "namespaces" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("namespaces"); }}
          >
            <span className="sb-icon">⊟</span>
            Namespaces
          </a>
          <a
            href="#"
            className={`sb-link${page === "audit" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("audit"); }}
          >
            <span className="sb-icon">≔</span>
            Audit Log
          </a>
          <a
            href="#"
            className={`sb-link${page === "alert-history" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("alert-history"); }}
          >
            <span className="sb-icon">⊛</span>
            Alert History
          </a>
          <a
            href="#"
            className={`sb-link${page === "configmaps" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("configmaps"); }}
          >
            <span className="sb-icon">⊞</span>
            ConfigMaps
          </a>
          <a
            href="#"
            className={`sb-link${page === "secrets" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("secrets"); }}
          >
            <span className="sb-icon">⊕</span>
            Secrets
          </a>
          <a
            href="#"
            className={`sb-link${page === "services" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("services"); }}
          >
            <span className="sb-icon">⇌</span>
            Services
          </a>
          <a
            href="#"
            className={`sb-link${page === "cronjobs" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("cronjobs"); }}
          >
            <span className="sb-icon">⊙</span>
            CronJobs
          </a>
          <a
            href="#"
            className={`sb-link${page === "storage" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("storage"); }}
          >
            <span className="sb-icon">◫</span>
            Storage
          </a>
          <a
            href="#"
            className={`sb-link${page === "objects" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("objects"); }}
          >
            <span className="sb-icon">◈</span>
            Objects
          </a>
          <a
            href="#"
            className={`sb-link${page === "helm" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("helm"); }}
          >
            <span className="sb-icon">⛵</span>
            Helm
          </a>
          <a
            href="#"
            className={`sb-link${page === "jobs" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("jobs"); }}
          >
            <span className="sb-icon">⊙</span>
            Jobs
          </a>
          <a
            href="#"
            className={`sb-link${page === "quotas" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("quotas"); }}
          >
            <span className="sb-icon">⊠</span>
            Quotas
          </a>
          <a
            href="#"
            className={`sb-link${page === "alert-rules" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("alert-rules"); }}
          >
            <span className="sb-icon">⊛</span>
            Alert Rules
          </a>
          <a
            href="#"
            className={`sb-link${page === "live-logs" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("live-logs"); }}
          >
            <span className="sb-icon">▶</span>
            Live Logs
          </a>

          <div className="sb-section">Admin</div>
          <a
            href="#"
            className={`sb-link${page === "users" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("users"); }}
          >
            <span className="sb-icon">◉</span>
            Users
          </a>
          <a
            href="#"
            className={`sb-link${page === "notifications" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("notifications"); }}
          >
            <span className="sb-icon">⊛</span>
            Notifications
          </a>
          <a
            href="#"
            className={`sb-link${page === "rbac" ? " active" : ""}`}
            onClick={(e) => { e.preventDefault(); navigate("rbac"); }}
          >
            <span className="sb-icon">⊗</span>
            RBAC
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
          <div className="sb-foot-val">v0.1.0 · Phase 50</div>
          <div className="sb-foot-label" style={{ marginTop: "0.4rem" }}>Cluster</div>
          <div className="sb-foot-val">4 nodes · arm64 · 10.100.102.0/24</div>
        </div>
      </aside>

      {sbOpen && <div className="sb-overlay" onClick={() => setSbOpen(false)} />}

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <div className="main-area">
        <header className="topbar">
          <div className="tb-left">
            <button className="hamburger" onClick={() => setSbOpen((o) => !o)}>
              <span /><span /><span />
            </button>
            <h1 className="page-title">
              {page === "workloads" ? "Workloads" : page === "capacity" ? "Capacity" : page === "events" ? "Events" : page === "namespaces" ? "Namespaces" : page === "audit" ? "Audit Log" : page === "alert-history" ? "Alert History" : page === "users" ? "Users" : page === "configmaps" ? "ConfigMaps" : page === "secrets" ? "Secrets" : page === "services" ? "Services & Ingresses" : page === "cronjobs" ? "CronJobs" : page === "storage" ? "Storage" : page === "notifications" ? "Notifications" : page === "objects" ? "Objects" : page === "helm" ? "Helm Releases" : page === "rbac" ? "RBAC Explorer" : page === "jobs" ? "Batch Jobs" : page === "quotas" ? "Quotas & Limits" : page === "alert-rules" ? "Alert Rules" : page === "live-logs" ? "Live Logs" : "Dashboard"}
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
          ) : page === "capacity" ? (
            <CapacityPage />
          ) : page === "events" ? (
            <EventsPage />
          ) : page === "namespaces" ? (
            <NamespacesPage />
          ) : page === "audit" ? (
            <AuditPage />
          ) : page === "alert-history" ? (
            <AlertHistoryPage />
          ) : page === "users" ? (
            <UsersPage />
          ) : page === "configmaps" ? (
            <ConfigMapsPage />
          ) : page === "secrets" ? (
            <SecretsPage />
          ) : page === "services" ? (
            <ServicesPage />
          ) : page === "cronjobs" ? (
            <CronJobsPage />
          ) : page === "storage" ? (
            <StoragePage />
          ) : page === "notifications" ? (
            <NotificationsPage />
          ) : page === "objects" ? (
            <ObjectsPage />
          ) : page === "helm" ? (
            <HelmPage />
          ) : page === "rbac" ? (
            <RBACPage />
          ) : page === "jobs" ? (
            <JobsPage />
          ) : page === "quotas" ? (
            <QuotasPage />
          ) : page === "alert-rules" ? (
            <AlertRulesPage />
          ) : page === "live-logs" ? (
            <LiveLogsPage />
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

                  <div className="cluster-power-row">
                    <span className="cluster-power-label">Cluster Power</span>
                    <button
                      className="cluster-restart-btn"
                      onClick={() => setClusterAction("restart")}
                    >
                      ↺ Restart All Nodes
                    </button>
                    <button
                      className="cluster-shutdown-btn"
                      onClick={() => setClusterAction("shutdown")}
                    >
                      ⏻ Shutdown All Nodes
                    </button>
                  </div>

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

      {clusterAction && (
        <ConfirmDialog
          title={clusterAction === "restart" ? "Restart entire cluster?" : "Shutdown entire cluster?"}
          message={
            clusterAction === "restart"
              ? `This will reboot all ${nodes.length} nodes. The cluster will be temporarily unreachable.`
              : `This will power off all ${nodes.length} nodes. They will need to be manually powered back on.`
          }
          confirmLabel={clusterBusy ? "Please wait…" : clusterAction === "restart" ? "Restart All" : "Shutdown All"}
          dangerous
          onConfirm={async () => {
            setClusterBusy(true);
            try {
              if (clusterAction === "restart") await restartAllNodes();
              else await shutdownAllNodes();
            } catch { /* nodes go offline immediately */ }
            setClusterBusy(false);
            setClusterAction(null);
          }}
          onCancel={() => setClusterAction(null)}
        />
      )}
    </div>
  );
}
